"""Lezione 1 - Chat con LM Studio (streaming + memoria della chat).

Come client2, ma il programma conserva la cronologia della conversazione:
a ogni domanda invia al modello tutti i messaggi precedenti (domande e
risposte), così l'LLM "ricorda" di cosa si è parlato.
La memoria dura finché il client resta aperto: uscendo, si azzera.

Usa solo la libreria standard: nessuna dipendenza da installare.
"""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def carica_env(percorso: Path) -> None:
    """Legge un file .env (CHIAVE=valore) senza sovrascrivere variabili già impostate."""
    if not percorso.exists():
        return
    for riga in percorso.read_text(encoding="utf-8").splitlines():
        riga = riga.strip()
        if not riga or riga.startswith("#") or "=" not in riga:
            continue
        chiave, valore = riga.split("=", 1)
        os.environ.setdefault(chiave.strip(), valore.strip().strip('"').strip("'"))


carica_env(ROOT / ".env")

BASE_URL = os.environ.get("LM_BASE_URL", "http://localhost:1234").rstrip("/")
TIMEOUT = 300  # secondi di attesa massima tra un pezzo di risposta e il successivo


def richiesta(metodo: str, endpoint: str, dati: dict | None = None) -> dict:
    """Esegue una chiamata HTTP all'API di LM Studio e restituisce il JSON."""
    corpo = json.dumps(dati).encode("utf-8") if dati is not None else None
    req = urllib.request.Request(
        f"{BASE_URL}/v1/{endpoint}",
        data=corpo,
        method=metodo,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as risposta:
        return json.loads(risposta.read().decode("utf-8"))


def scegli_modello() -> str:
    """Usa LM_MODEL se impostato, altrimenti il primo modello caricato in LM Studio."""
    modello = os.environ.get("LM_MODEL")
    if modello:
        return modello
    modelli = richiesta("GET", "models").get("data", [])
    if not modelli:
        raise RuntimeError("Nessun modello caricato in LM Studio.")
    return modelli[0]["id"]


def chiedi_stream(modello: str, messaggi: list[dict]) -> str:
    """Invia i messaggi con stream attivo, stampa i pezzi appena arrivano
    e restituisce il testo completo.

    Con lo streaming il server risponde in formato SSE: tante righe
    "data: {...}" ognuna con un pezzetto di testo, e alla fine "data: [DONE]".
    """
    corpo = json.dumps({"model": modello, "messages": messaggi, "stream": True})
    req = urllib.request.Request(
        f"{BASE_URL}/v1/chat/completions",
        data=corpo.encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    pezzi: list[str] = []
    with urllib.request.urlopen(req, timeout=TIMEOUT) as risposta:
        for riga in risposta:
            riga = riga.decode("utf-8").strip()
            if not riga.startswith("data:"):
                continue
            dati = riga.removeprefix("data:").strip()
            if dati == "[DONE]":
                break
            scelte = json.loads(dati).get("choices") or []
            if not scelte:
                continue
            pezzo = scelte[0].get("delta", {}).get("content")
            if pezzo:
                print(pezzo, end="", flush=True)
                pezzi.append(pezzo)
    print()
    return "".join(pezzi).strip()


def main() -> None:
    print(f"Connessione a LM Studio su {BASE_URL} ...")
    try:
        modello = scegli_modello()
    except (urllib.error.URLError, OSError) as e:
        print(f"Impossibile contattare LM Studio: {e}")
        print("Controlla che il server sia avviato e che la porta sia corretta.")
        return
    except RuntimeError as e:
        print(e)
        return

    print(f"Modello: {modello}")
    print("Scrivi la tua domanda ('esci' per tornare al menu).")
    print("Il modello ricorda la conversazione finché il client resta aperto.\n")

    # Cronologia della chat: cresce a ogni scambio e viene inviata tutta ogni volta
    cronologia: list[dict] = []
    while True:
        try:
            domanda = input("Tu: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not domanda:
            continue
        if domanda.lower() in {"esci", "exit", "quit", "q"}:
            break

        cronologia.append({"role": "user", "content": domanda})
        print(f"\nil modello {modello} sta pensando...\n")
        print(f"{modello}: ", end="", flush=True)
        try:
            testo = chiedi_stream(modello, cronologia)
        except (urllib.error.URLError, OSError, ValueError) as e:
            print(f"\nErrore durante la richiesta: {e}\n")
            cronologia.pop()  # la domanda non ha avuto risposta: non la teniamo in memoria
            continue

        cronologia.append({"role": "assistant", "content": testo})
        print()


if __name__ == "__main__":
    main()
