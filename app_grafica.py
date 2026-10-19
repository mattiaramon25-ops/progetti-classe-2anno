"""Interfaccia grafica per chattare con LM Studio.

Avvio:
    python app_grafica.py
"""

import customtkinter as ctk

from gui.finestra import Finestra

# Fase 2: conversazione di prova per vedere la grafica.
# Dalla fase 4 la chat sarà collegata davvero a LM Studio.
ESEMPI = [
    ("modello", "Ciao! Come posso aiutarti?"),
    ("utente", "Spiegami in breve cos'è lo streaming SSE."),
    ("modello",
     "Con lo streaming SSE il server non aspetta di avere la risposta completa: "
     "invia tante righe \"data: {...}\", ognuna con un pezzetto di testo, e alla "
     "fine manda \"data: [DONE]\". Così il testo compare mentre il modello lo scrive."),
    ("utente", "Perfetto, grazie!"),
]


def main() -> None:
    ctk.set_appearance_mode("system")  # parte con il tema di Windows
    finestra = Finestra()
    for mittente, testo in ESEMPI:
        finestra.aggiungi_messaggio(mittente, testo, nome="spark-x2.5-4b")
    finestra.mainloop()


if __name__ == "__main__":
    main()
