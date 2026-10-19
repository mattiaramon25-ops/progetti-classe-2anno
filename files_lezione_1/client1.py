"""Lezione 1 - Chat con LM Studio (senza streaming).

Si collega al server locale di LM Studio (API compatibile OpenAI),
mostra "il modello <nome> sta pensando..." e poi stampa la risposta
completa in un unico colpo. Ogni domanda è indipendente (nessuna memoria).

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
TIMEOUT = 300  # secondi: i modelli locali possono essere lenti


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


def chiedi(modello: str, messaggi: list[dict]) -> str:
    """Invia i messaggi e restituisce la risposta completa (stream disattivato)."""
    dati = richiesta(
        "POST",
        "chat/completions",
        {"model": modello, "messages": messaggi, "stream": False},
    )
    return dati["choices"][0]["message"]["content"].strip()


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
    print("Scrivi la tua domanda ('esci' per tornare al menu).\n")

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

        # Nessuna memoria: ogni domanda viene inviata da sola
        messaggi = [{"role": "user", "content": domanda}]
        print(f"\nil modello {modello} sta pensando...\n")
        try:
            testo = chiedi(modello, messaggi)
        except (urllib.error.URLError, OSError, KeyError, IndexError) as e:
            print(f"Errore durante la richiesta: {e}\n")
            continue

        print(f"{modello}: {testo}\n")


if __name__ == "__main__":
    main()
