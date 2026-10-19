"""Pezzi dell'interfaccia: nuvoletta, barra laterale e barra di scrittura."""

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
    """Pannello a sinistra: modello, interruttori, nuova chat, stato e tema."""

    def __init__(self, master):
        super().__init__(
            master,
            width=tema.LARGHEZZA_BARRA,
            corner_radius=tema.RAGGIO_PANNELLO,
            fg_color=COLORI["barra_laterale"],
        )
        self.pack_propagate(False)  # mantiene la larghezza fissa
        margine = tema.SPAZIO_L

        ctk.CTkLabel(
            self, text="LM Chat", font=tema.font(20, grassetto=True),
            text_color=COLORI["testo"], anchor="w",
        ).pack(fill="x", padx=margine, pady=(margine, tema.SPAZIO_L))

        # --- Modello ---
        ctk.CTkLabel(
            self, text="Modello", font=tema.font(12),
            text_color=COLORI["testo_leggero"], anchor="w", height=20,
        ).pack(fill="x", padx=margine)
        self.menu_modello = ctk.CTkOptionMenu(
            self,
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
            self._interruttore(testo, variabile).pack(
                fill="x", padx=margine, pady=(0, tema.SPAZIO_M)
            )

        self.pulsante_nuova_chat = ctk.CTkButton(
            self,
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
        self.interruttore_tema = self._interruttore("Tema scuro", None, self._cambia_tema)
        self.interruttore_tema.pack(side="bottom", fill="x", padx=margine, pady=(0, margine))
        if ctk.get_appearance_mode() == "Dark":
            self.interruttore_tema.select()

        riga_stato = ctk.CTkFrame(self, fg_color="transparent")
        riga_stato.pack(side="bottom", fill="x", padx=margine, pady=(0, tema.SPAZIO_M))
        self.pallino = ctk.CTkLabel(
            riga_stato, text="●", font=tema.font(14),
            text_color=COLORI["stato_errore"], width=16,
        )
        self.pallino.pack(side="left")
        self.testo_stato = ctk.CTkLabel(
            riga_stato, text="Non connesso", font=tema.font(13),
            text_color=COLORI["testo_leggero"],
        )
        self.testo_stato.pack(side="left", padx=(tema.SPAZIO_S, 0))

    def _interruttore(self, testo: str, variabile, comando=None) -> ctk.CTkSwitch:
        return ctk.CTkSwitch(
            self,
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

    def _cambia_tema(self) -> None:
        ctk.set_appearance_mode("dark" if self.interruttore_tema.get() else "light")


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
