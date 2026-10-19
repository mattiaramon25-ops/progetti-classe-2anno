"""Pezzi dell'interfaccia: nuvoletta, barra laterale e barra di scrittura."""

import time

import customtkinter as ctk

from gui import tema
from gui.tema import COLORI

MITTENTI = ("utente", "modello")


class Nuvoletta(ctk.CTkFrame):
    """Un messaggio della chat.

    - utente  → colore d'accento, testo bianco (va allineata a destra)
    - modello → colore tenue, con il nome del modello sopra (va a sinistra)
    """

    def __init__(self, master, mittente: str, testo: str, nome: str | None = None,
                 larghezza_testo: int = 400):
        if mittente not in MITTENTI:
            raise ValueError(f"Mittente sconosciuto: {mittente!r} (usa {MITTENTI})")
        super().__init__(master, fg_color="transparent")
        self.mittente = mittente
        da_utente = mittente == "utente"
        lato = "e" if da_utente else "w"

        self.etichetta_nome = None
        if not da_utente:
            self.etichetta_nome = ctk.CTkLabel(
                self, text=nome or "modello", font=tema.font(12),
                text_color=COLORI["testo_leggero"], height=20,
            )
            self.etichetta_nome.pack(anchor="w", padx=tema.SPAZIO_S)

        self.fumetto = ctk.CTkFrame(
            self,
            corner_radius=tema.RAGGIO_NUVOLA,
            fg_color=COLORI["accento"] if da_utente else COLORI["nuvola_modello"],
        )
        self.fumetto.pack(anchor=lato)

        self.etichetta = ctk.CTkLabel(
            self.fumetto,
            text=testo,
            font=tema.font(14),
            text_color=COLORI["testo_su_accento"] if da_utente else COLORI["testo"],
            wraplength=larghezza_testo,
            justify="left",
            anchor="w",
        )
        self.etichetta.pack(padx=tema.SPAZIO_M, pady=tema.SPAZIO_S)

    @property
    def testo(self) -> str:
        return self.etichetta.cget("text")

    @property
    def larghezza_testo(self) -> int:
        return self.etichetta.cget("wraplength")

    def imposta_larghezza(self, larghezza_testo: int) -> None:
        """Larghezza massima del testo prima di andare a capo, in pixel."""
        self.etichetta.configure(wraplength=larghezza_testo)


class BarraLaterale(ctk.CTkFrame):
    """Pannello a sinistra, retraibile.

    - Aperta (240 px): modello, interruttori, nuova chat, stato e tema.
    - Chiusa (64 px): striscia con le sole icone essenziali.
    Il passaggio tra le due è animato; durante l'animazione il pannello
    resta vuoto, così cambia solo la larghezza e il movimento è fluido.
    A fine animazione viene chiamata `alla_fine_animazione`, se indicata.
    """

    DURATA_ANIMAZIONE = 0.2  # secondi
    INTERVALLO_FOTOGRAMMI = 16  # millisecondi, circa 60 fotogrammi al secondo

    def __init__(self, master, alla_fine_animazione=None):
        super().__init__(
            master,
            width=tema.LARGHEZZA_BARRA,
            corner_radius=tema.RAGGIO_PANNELLO,
            fg_color=COLORI["barra_laterale"],
        )
        self.pack_propagate(False)  # la larghezza la decidiamo noi, non il contenuto
        self.aperta = True
        self._timer_animazione = None
        self._alla_fine_animazione = alla_fine_animazione

        # I due contenuti lasciano libere le fasce in alto e in basso grandi
        # quanto il raggio, per non coprire gli angoli arrotondati del pannello.
        self.contenuto_aperto = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.contenuto_chiuso = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self._crea_contenuto_aperto(self.contenuto_aperto)
        self._crea_contenuto_chiuso(self.contenuto_chiuso)
        self._mostra(self.contenuto_aperto)

        if ctk.get_appearance_mode() == "Dark":
            self.interruttore_tema.select()
        self._aggiorna_icona_tema()

    # --- Costruzione ---

    def _crea_contenuto_aperto(self, contenitore) -> None:
        margine = tema.SPAZIO_L
        sopra = tema.SPAZIO_S  # più il raggio lasciato libero = 24 px dal bordo

        intestazione = ctk.CTkFrame(contenitore, fg_color="transparent")
        intestazione.pack(fill="x", padx=(margine, tema.SPAZIO_M), pady=(sopra, tema.SPAZIO_L))
        ctk.CTkLabel(
            intestazione, text="LM Chat", font=tema.font(20, grassetto=True),
            text_color=COLORI["testo"], anchor="w",
        ).pack(side="left")
        self.pulsante_chiudi = self._pulsante_icona(intestazione, "«", self.chiudi)
        self.pulsante_chiudi.pack(side="right")

        # --- Modello ---
        ctk.CTkLabel(
            contenitore, text="Modello", font=tema.font(12),
            text_color=COLORI["testo_leggero"], anchor="w", height=20,
        ).pack(fill="x", padx=margine)
        self.menu_modello = ctk.CTkOptionMenu(
            contenitore,
            values=["Nessun modello"],
            height=40,
            corner_radius=tema.RAGGIO_CONTROLLO,
            font=tema.font(13),
            dropdown_font=tema.font(13),
            fg_color=COLORI["controllo"],
            button_color=COLORI["controllo"],
            button_hover_color=COLORI["bordo"],
            text_color=COLORI["testo"],
            dropdown_fg_color=COLORI["controllo"],
            dropdown_hover_color=COLORI["nuvola_modello"],
            dropdown_text_color=COLORI["testo"],
            dynamic_resizing=False,
        )
        self.menu_modello.pack(fill="x", padx=margine, pady=(tema.SPAZIO_S, tema.SPAZIO_L))

        # --- Interruttori ---
        self.streaming = ctk.BooleanVar(value=True)
        self.memoria = ctk.BooleanVar(value=False)
        for testo, variabile in (("Streaming", self.streaming), ("Memoria", self.memoria)):
            self._interruttore(contenitore, testo, variabile).pack(
                fill="x", padx=margine, pady=(0, tema.SPAZIO_M)
            )

        self.pulsante_nuova_chat = ctk.CTkButton(
            contenitore,
            text="+  Nuova chat",
            height=40,
            corner_radius=tema.RAGGIO_CONTROLLO,
            font=tema.font(13, grassetto=True),
            fg_color=COLORI["accento"],
            hover_color=COLORI["accento_hover"],
            text_color=COLORI["testo_su_accento"],
        )
        self.pulsante_nuova_chat.pack(fill="x", padx=margine, pady=(tema.SPAZIO_S, 0))

        # --- In basso: tema e stato della connessione ---
        self.interruttore_tema = self._interruttore(
            contenitore, "Tema scuro", None, self._interruttore_tema_cambiato
        )
        self.interruttore_tema.pack(side="bottom", fill="x", padx=margine, pady=(0, sopra))

        riga_stato = ctk.CTkFrame(contenitore, fg_color="transparent")
        riga_stato.pack(side="bottom", fill="x", padx=margine, pady=(0, tema.SPAZIO_M))
        self.pallino = self._pallino(riga_stato)
        self.pallino.pack(side="left")
        self.testo_stato = ctk.CTkLabel(
            riga_stato, text="Non connesso", font=tema.font(13),
            text_color=COLORI["testo_leggero"],
        )
        self.testo_stato.pack(side="left", padx=(tema.SPAZIO_S, 0))

    def _crea_contenuto_chiuso(self, contenitore) -> None:
        sopra = tema.SPAZIO_S
        self.pulsante_apri = self._pulsante_icona(contenitore, "☰", self.apri)
        self.pulsante_apri.pack(pady=(sopra, tema.SPAZIO_M))

        self.pulsante_nuova_chat_icona = ctk.CTkButton(
            contenitore,
            text="+",
            width=40,
            height=40,
            corner_radius=tema.RAGGIO_CONTROLLO,
            font=tema.font(18, grassetto=True),
            fg_color=COLORI["accento"],
            hover_color=COLORI["accento_hover"],
            text_color=COLORI["testo_su_accento"],
        )
        self.pulsante_nuova_chat_icona.pack()

        self.pulsante_tema_icona = self._pulsante_icona(contenitore, "☾", self._pulsante_tema_premuto)
        self.pulsante_tema_icona.pack(side="bottom", pady=(0, sopra))
        self.pallino_chiuso = self._pallino(contenitore)
        self.pallino_chiuso.pack(side="bottom", pady=(0, tema.SPAZIO_M))

    def _pulsante_icona(self, master, icona: str, comando) -> ctk.CTkButton:
        """Pulsante quadrato e trasparente con una sola icona."""
        return ctk.CTkButton(
            master,
            text=icona,
            width=40,
            height=40,
            corner_radius=tema.RAGGIO_CONTROLLO,
            font=tema.font(18),
            fg_color="transparent",
            hover_color=COLORI["bordo"],
            text_color=COLORI["accento_testo"],
            command=comando,
        )

    def _pallino(self, master) -> ctk.CTkLabel:
        return ctk.CTkLabel(
            master, text="●", font=tema.font(14),
            text_color=COLORI["stato_errore"], width=16,
        )

    def _interruttore(self, master, testo: str, variabile, comando=None) -> ctk.CTkSwitch:
        return ctk.CTkSwitch(
            master,
            text=testo,
            variable=variabile,
            command=comando,
            font=tema.font(13),
            text_color=COLORI["testo"],
            progress_color=COLORI["interruttore_acceso"],
            fg_color=COLORI["interruttore_spento"],
            button_color=COLORI["pallino_interruttore"],
            button_hover_color=COLORI["pallino_interruttore"],
        )

    # --- Tema ---

    def _interruttore_tema_cambiato(self) -> None:
        ctk.set_appearance_mode("dark" if self.interruttore_tema.get() else "light")
        self._aggiorna_icona_tema()

    def _pulsante_tema_premuto(self) -> None:
        self.interruttore_tema.toggle()  # cambia il tema e tiene sincronizzati i due comandi

    def _aggiorna_icona_tema(self) -> None:
        # l'icona mostra il tema in cui si passa cliccando
        self.pulsante_tema_icona.configure(text="☀" if self.interruttore_tema.get() else "☾")

    # --- Apertura e chiusura ---

    @property
    def in_animazione(self) -> bool:
        return self._timer_animazione is not None

    def apri(self, animazione: bool = True) -> None:
        self._vai_a(True, animazione)

    def chiudi(self, animazione: bool = True) -> None:
        self._vai_a(False, animazione)

    def alterna(self, animazione: bool = True) -> None:
        self._vai_a(not self.aperta, animazione)

    def _vai_a(self, aperta: bool, animazione: bool) -> None:
        if self._timer_animazione is not None:  # cambio di idea a metà: si riparte da qui
            self.after_cancel(self._timer_animazione)
            self._timer_animazione = None
        self.aperta = aperta
        arrivo = tema.LARGHEZZA_BARRA if aperta else tema.LARGHEZZA_BARRA_CHIUSA
        contenuto = self.contenuto_aperto if aperta else self.contenuto_chiuso
        if not animazione:
            self.configure(width=arrivo)
            self._mostra(contenuto)
            return
        self._mostra(None)
        self._anima(self.cget("width"), arrivo, time.perf_counter(),
                    alla_fine=lambda: self._fine_animazione(contenuto))

    def _fine_animazione(self, contenuto) -> None:
        self._mostra(contenuto)
        if self._alla_fine_animazione is not None:
            self._alla_fine_animazione()

    def _anima(self, partenza: int, arrivo: int, inizio: float, alla_fine) -> None:
        # L'avanzamento dipende dal tempo trascorso, non dal numero di passi:
        # così l'animazione dura sempre uguale, anche se un fotogramma tarda.
        avanzamento = min(1.0, (time.perf_counter() - inizio) / self.DURATA_ANIMAZIONE)
        morbido = 1 - (1 - avanzamento) ** 3  # parte veloce e rallenta alla fine
        self.configure(width=round(partenza + (arrivo - partenza) * morbido))
        if avanzamento < 1:
            self._timer_animazione = self.after(
                self.INTERVALLO_FOTOGRAMMI, self._anima, partenza, arrivo, inizio, alla_fine
            )
        else:
            self._timer_animazione = None
            alla_fine()

    def _mostra(self, contenuto) -> None:
        """Mostra uno dei due contenuti (o nessuno, con None)."""
        for altro in (self.contenuto_aperto, self.contenuto_chiuso):
            if altro is not contenuto:
                altro.pack_forget()
        if contenuto is not None:
            contenuto.pack(fill="both", expand=True, pady=tema.RAGGIO_PANNELLO)


class BarraScrittura(ctk.CTkFrame):
    """Casella arrotondata "a pillola" con il pulsante di invio."""

    ALTEZZA = 56
    SUGGERIMENTO = "Scrivi un messaggio..."

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)

        # La "pillola" è un contenitore arrotondato con dentro una casella di testo
        # senza angoli: CTkTextbox con angoli grandi aggiungerebbe troppo margine.
        pillola = ctk.CTkFrame(
            self,
            corner_radius=self.ALTEZZA // 2,
            border_width=1,
            fg_color=COLORI["pannello"],
            border_color=COLORI["bordo"],
        )
        pillola.grid(row=0, column=0, sticky="ew")
        self.casella = ctk.CTkTextbox(
            pillola,
            height=self.ALTEZZA - 2 * tema.SPAZIO_M,
            corner_radius=0,
            border_width=0,
            border_spacing=0,
            font=tema.font(14),
            fg_color=COLORI["pannello"],
            text_color=COLORI["testo"],
            wrap="word",
            activate_scrollbars=False,
        )
        self.casella.pack(fill="x", padx=tema.SPAZIO_L, pady=tema.SPAZIO_M)

        # Testo di aiuto mostrato quando la casella è vuota
        self.suggerimento = ctk.CTkLabel(
            self.casella, text=self.SUGGERIMENTO, font=tema.font(14),
            text_color=COLORI["testo_leggero"], fg_color=COLORI["pannello"], height=20,
        )
        self._aggiorna_suggerimento()
        self.suggerimento.bind("<Button-1>", lambda _: self.casella.focus_set())
        self.casella.bind("<FocusIn>", lambda _: self.suggerimento.place_forget())
        self.casella.bind("<FocusOut>", lambda _: self._aggiorna_suggerimento())

        self.pulsante_invia = ctk.CTkButton(
            self,
            text="➤",
            width=self.ALTEZZA,
            height=self.ALTEZZA,
            corner_radius=self.ALTEZZA // 2,
            font=tema.font(18),
            fg_color=COLORI["accento"],
            hover_color=COLORI["accento_hover"],
            text_color=COLORI["testo_su_accento"],
        )
        self.pulsante_invia.grid(row=0, column=1, padx=(tema.SPAZIO_S, 0))

    def _aggiorna_suggerimento(self) -> None:
        if not self.casella.get("1.0", "end").strip():
            self.suggerimento.place(x=0, rely=0.5, anchor="w")
