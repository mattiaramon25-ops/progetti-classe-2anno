"""Logica per parlare con LM Studio, separata dalla grafica.

Riprende il codice dei client della lezione 1 (lettura del .env, scelta del
modello, risposta normale e in streaming) ma senza print() né input(), così
l'interfaccia grafica può usarlo e i test possono verificarlo da soli.

Usa solo la libreria standard.
"""

import json
import os
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
URL_PREDEFINITO = "http://localhost:1234"
TIMEOUT = 300  # secondi: i modelli locali possono essere lenti


class ErroreLM(Exception):
    """Errore con un messaggio già comprensibile, da mostrare nella GUI."""


def leggi_env(percorso: Path) -> dict[str, str]:
    """Legge un file .env (CHIAVE=valore) e restituisce le coppie trovate."""
    if not percorso.exists():
        return {}
    valori = {}
    for riga in percorso.read_text(encoding="utf-8").splitlines():
        riga = riga.strip()
        if not riga or riga.startswith("#") or "=" not in riga:
            continue
        chiave, valore = riga.split("=", 1)
        valori[chiave.strip()] = valore.strip().strip('"').strip("'")
    return valori


def configurazione(percorso_env: Path = ROOT / ".env") -> tuple[str, str | None]:
    """Restituisce (indirizzo del server, modello preferito o None).

    Come nei client della lezione 1, le variabili di ambiente già impostate
    hanno la precedenza sul file .env.
    """
    valori = {**leggi_env(percorso_env), **os.environ}
    base_url = valori.get("LM_BASE_URL") or URL_PREDEFINITO
    modello = valori.get("LM_MODEL") or None
    return base_url.rstrip("/"), modello


class ClientLM:
    """Client per il server locale di LM Studio (API compatibile OpenAI)."""

    def __init__(self, base_url: str, timeout: float = TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _apri(self, metodo: str, endpoint: str, dati: dict | None = None):
        """Apre la connessione e restituisce la risposta HTTP ancora da leggere.

        Gli errori di rete vengono trasformati in ErroreLM con un messaggio chiaro.
        """
        corpo = json.dumps(dati).encode("utf-8") if dati is not None else None
        req = urllib.request.Request(
            f"{self.base_url}/v1/{endpoint}",
            data=corpo,
            method=metodo,
            headers={"Content-Type": "application/json"},
        )
        try:
            return urllib.request.urlopen(req, timeout=self.timeout)
        except urllib.error.HTTPError as e:
            e.close()  # anche la risposta di errore è una connessione da chiudere
            raise ErroreLM(f"LM Studio ha risposto con un errore {e.code}: {e.reason}") from e
        except (urllib.error.URLError, OSError) as e:
            raise ErroreLM(
                f"Impossibile contattare LM Studio su {self.base_url}: "
                "controlla che il server sia avviato e che la porta sia corretta."
            ) from e

    def _richiesta_json(self, metodo: str, endpoint: str, dati: dict | None = None) -> dict:
        with self._apri(metodo, endpoint, dati) as risposta:
            try:
                return json.loads(risposta.read().decode("utf-8"))
            except ValueError as e:
                raise ErroreLM("Risposta non valida da LM Studio.") from e

    def modelli(self) -> list[str]:
        """Nomi dei modelli caricati in LM Studio."""
        dati = self._richiesta_json("GET", "models")
        return [modello["id"] for modello in dati.get("data", [])]

    def scegli_modello(self, preferito: str | None) -> str:
        """Usa il modello preferito se c'è, altrimenti il primo caricato in LM Studio."""
        if preferito:
            return preferito
        modelli = self.modelli()
        if not modelli:
            raise ErroreLM("Nessun modello caricato in LM Studio.")
        return modelli[0]

    def chiedi(self, modello: str, messaggi: list[dict]) -> str:
        """Invia i messaggi e restituisce la risposta completa (stream disattivato)."""
        dati = self._richiesta_json(
            "POST",
            "chat/completions",
            {"model": modello, "messages": messaggi, "stream": False},
        )
        try:
            return dati["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError, AttributeError) as e:
            raise ErroreLM("Risposta non valida da LM Studio.") from e

    def chiedi_stream(self, modello: str, messaggi: list[dict]) -> Iterator[str]:
        """Invia i messaggi con stream attivo e restituisce i pezzi di testo
        uno alla volta, appena arrivano.

        Con lo streaming il server risponde in formato SSE: tante righe
        "data: {...}" ognuna con un pezzetto di testo, e alla fine "data: [DONE]".
        Per fermare la risposta a metà basta smettere di leggere: chiudendo
        il generatore si chiude anche la connessione.
        """
        corpo = {"model": modello, "messages": messaggi, "stream": True}
        with self._apri("POST", "chat/completions", corpo) as risposta:
            for riga in risposta:
                riga = riga.decode("utf-8").strip()
                if not riga.startswith("data:"):
                    continue
                dati = riga.removeprefix("data:").strip()
                if dati == "[DONE]":
                    return
                try:
                    scelte = json.loads(dati).get("choices") or []
                except ValueError as e:
                    raise ErroreLM("Risposta non valida da LM Studio.") from e
                if not scelte:
                    continue
                pezzo = scelte[0].get("delta", {}).get("content")
                if pezzo:
                    yield pezzo
