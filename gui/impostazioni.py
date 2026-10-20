"""Preferenze dell'interfaccia salvate in un piccolo file JSON.

Il file (impostazioni_gui.json) è escluso da git: ognuno ha le sue.
Se manca o è rovinato si usano i valori predefiniti, senza errori.
"""

import json
from pathlib import Path

PREDEFINITE = {
    "tema": None,  # None = come Windows, altrimenti "light" o "dark"
    "barra_aperta": True,
    "streaming": True,
    "memoria": False,
}
TEMI = (None, "light", "dark")


def carica(percorso: Path) -> dict:
    """Legge le preferenze; i valori mancanti o non validi diventano quelli predefiniti."""
    valori = dict(PREDEFINITE)
    try:
        letti = json.loads(percorso.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return valori
    if not isinstance(letti, dict):
        return valori
    if letti.get("tema") in TEMI:
        valori["tema"] = letti["tema"]
    for chiave in ("barra_aperta", "streaming", "memoria"):
        if isinstance(letti.get(chiave), bool):
            valori[chiave] = letti[chiave]
    return valori


def salva(percorso: Path, valori: dict) -> None:
    """Scrive le preferenze. Se non ci riesce pazienza: l'app funziona lo stesso."""
    try:
        percorso.write_text(json.dumps(valori, indent=2), encoding="utf-8")
    except OSError:
        pass
