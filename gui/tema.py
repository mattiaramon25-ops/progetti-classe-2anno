"""Colori, misure e font dell'interfaccia grafica.

Ogni colore è una coppia (tema chiaro, tema scuro): CustomTkinter sceglie
da solo quale usare in base al tema attivo.
- Tema chiaro: verde menta tenue, accento verde deciso.
- Tema scuro: blu notte, accento viola.
I contrasti del testo sono controllati in tests/test_tema.py.
"""

import customtkinter as ctk

COLORI = {
    "sfondo": ("#F1F8F3", "#0E1129"),
    "pannello": ("#FFFFFF", "#161A3A"),
    "barra_laterale": ("#E2F2E7", "#161A3A"),
    "nuvola_modello": ("#E2F2E7", "#212754"),
    "bordo": ("#C6E2CF", "#2A3170"),
    "controllo": ("#FFFFFF", "#283068"),  # menu a tendina sulla barra laterale
    "interruttore_spento": ("#6A8E75", "#5C64AB"),
    "interruttore_acceso": ("#166534", "#8B5CF6"),
    "pallino_interruttore": ("#FFFFFF", "#ECEBFA"),
    "accento": ("#166534", "#6D28D9"),
    "accento_hover": ("#14532D", "#5B21B6"),
    "accento_testo": ("#166534", "#B9A2FB"),
    "testo": ("#14281C", "#ECEBFA"),
    "testo_leggero": ("#4A6354", "#A9AED6"),
    "testo_su_accento": ("#FFFFFF", "#FFFFFF"),
    "errore": ("#B91C1C", "#FCA5A5"),
    "stato_ok": ("#16A34A", "#4ADE80"),
    "stato_errore": ("#DC2626", "#F87171"),
}

# Spaziature: sempre multipli di 8 px
SPAZIO_S = 8
SPAZIO_M = 16
SPAZIO_L = 24
SPAZIO_XL = 32

# Angoli arrotondati
RAGGIO_NUVOLA = 24
RAGGIO_PANNELLO = 16
RAGGIO_CONTROLLO = 12

LARGHEZZA_BARRA = 240
LARGHEZZA_BARRA_CHIUSA = 64
LARGHEZZA_MAX_NUVOLA = 0.7  # frazione della larghezza della chat

FAMIGLIA_FONT = "Segoe UI"


def font(dimensione: int = 13, grassetto: bool = False) -> ctk.CTkFont:
    """Font dell'app. Va chiamata dopo aver creato la finestra."""
    return ctk.CTkFont(
        family=FAMIGLIA_FONT, size=dimensione, weight="bold" if grassetto else "normal"
    )
