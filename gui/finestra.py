"""Finestra principale: barra laterale a sinistra, chat e barra di scrittura a destra."""

import customtkinter as ctk

from gui import tema
from gui.componenti import BarraLaterale, BarraScrittura, Nuvoletta
from gui.tema import COLORI


class Finestra(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=COLORI["sfondo"])
        self.title("LM Chat")
        self.geometry("1040x700")
        self.minsize(760, 520)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.barra = BarraLaterale(self, alla_fine_animazione=self._barra_animata)
        self.barra.grid(row=0, column=0, sticky="ns", padx=(tema.SPAZIO_M, 0), pady=tema.SPAZIO_M)

        area = ctk.CTkFrame(self, fg_color="transparent")
        area.grid(row=0, column=1, sticky="nsew", padx=tema.SPAZIO_M, pady=tema.SPAZIO_M)
        area.grid_columnconfigure(0, weight=1)
        area.grid_rowconfigure(0, weight=1)

        self.chat = ctk.CTkScrollableFrame(
            area,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color=COLORI["bordo"],
            scrollbar_button_hover_color=COLORI["testo_leggero"],
        )
        self.chat.grid(row=0, column=0, sticky="nsew")
        self.chat.bind("<Configure>", self._chat_ridimensionata)

        self.scrittura = BarraScrittura(area)
        self.scrittura.grid(
            row=1, column=0, sticky="ew", padx=tema.SPAZIO_L, pady=(tema.SPAZIO_M, tema.SPAZIO_S)
        )

        self.nuvolette: list[Nuvoletta] = []
        self._larghezza_chat = 700

        # Ctrl+B apre/chiude la barra laterale, anche mentre si scrive
        for tasto in ("<Control-b>", "<Control-B>"):
            self.bind(tasto, self._scorciatoia_barra)
            self.scrittura.casella.bind(tasto, self._scorciatoia_barra)

    def aggiungi_messaggio(self, mittente: str, testo: str, nome: str | None = None) -> Nuvoletta:
        """Aggiunge una nuvoletta in fondo alla chat e la restituisce."""
        nuvoletta = Nuvoletta(
            self.chat, mittente, testo, nome=nome,
            larghezza_testo=self._larghezza_testo(),
        )
        nuvoletta.pack(
            anchor="e" if mittente == "utente" else "w",
            padx=tema.SPAZIO_L,
            pady=tema.SPAZIO_S,
        )
        self.nuvolette.append(nuvoletta)
        return nuvoletta

    def adatta_nuvolette(self, larghezza_chat: int) -> None:
        """Le nuvolette occupano al massimo il 70% della larghezza della chat."""
        self._larghezza_chat = larghezza_chat
        for nuvoletta in self.nuvolette:
            nuvoletta.imposta_larghezza(self._larghezza_testo())

    def _larghezza_testo(self) -> int:
        larghezza_nuvola = int(self._larghezza_chat * tema.LARGHEZZA_MAX_NUVOLA)
        return larghezza_nuvola - 2 * tema.SPAZIO_M  # tolti i margini interni

    def _scorciatoia_barra(self, _evento=None) -> str:
        self.barra.alterna()
        return "break"  # il tasto non arriva alla casella di testo

    def _chat_ridimensionata(self, evento) -> None:
        if self.barra.in_animazione:
            # Ricalcolare le nuvolette a ogni fotogramma rende l'animazione a scatti:
            # lo facciamo una volta sola, a fine animazione (_barra_animata).
            return
        self._adatta_a(evento.width)

    def _barra_animata(self) -> None:
        self.update_idletasks()  # completa il ridimensionamento della chat
        self._adatta_a(self.chat.winfo_width())

    def _adatta_a(self, larghezza_pixel: int) -> None:
        # Tk misura in pixel reali: con lo zoom di Windows (es. 125%) va riportato
        scala = ctk.ScalingTracker.get_widget_scaling(self)
        larghezza = int(larghezza_pixel / scala)
        if larghezza != self._larghezza_chat:
            self.adatta_nuvolette(larghezza)
