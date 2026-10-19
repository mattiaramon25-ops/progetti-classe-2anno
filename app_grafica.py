"""Interfaccia grafica per chattare con LM Studio.

Legge indirizzo e modello dal file .env, come i client della lezione 1.

Avvio:
    python app_grafica.py
"""

import customtkinter as ctk

from gui.finestra import Finestra
from gui.lm_api import ClientLM, configurazione


def main() -> None:
    ctk.set_appearance_mode("system")  # parte con il tema di Windows
    base_url, modello_preferito = configurazione()
    finestra = Finestra(ClientLM(base_url), modello_preferito)
    finestra.mainloop()


if __name__ == "__main__":
    main()
