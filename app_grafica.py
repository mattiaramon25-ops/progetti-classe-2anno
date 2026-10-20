"""Interfaccia grafica per chattare con LM Studio.

Legge indirizzo e modello dal file .env, come i client della lezione 1.

Avvio:
    python app_grafica.py
"""

import customtkinter as ctk

from gui.finestra import Finestra
from gui.lm_api import ROOT, ClientLM, configurazione

# Preferenze dell'interfaccia (tema, barra, interruttori), escluse da git
PERCORSO_IMPOSTAZIONI = ROOT / "impostazioni_gui.json"


def main() -> None:
    ctk.set_appearance_mode("system")  # tema di Windows, se non ne è stato scelto un altro
    base_url, modello_preferito = configurazione()
    finestra = Finestra(ClientLM(base_url), modello_preferito, PERCORSO_IMPOSTAZIONI)
    finestra.mainloop()


if __name__ == "__main__":
    main()
