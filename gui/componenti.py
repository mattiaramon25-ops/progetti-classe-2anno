"""Pezzi dell'interfaccia: nuvoletta, barra laterale e barra di scrittura."""

import math
import tkinter.font

import customtkinter as ctk

from gui import tema
from gui.animazione import Animazione
from gui.tema import COLORI

MITTENTI = ("utente", "modello")


class Nuvoletta(ctk.CTkFrame):
    """Un messaggio della chat.

    - utente  → colore d'accento, testo bianco (va allineata a destra)
    - modello → colore tenue, con il nome del modello sopra (va a sinistra)

    Con lo streaming la nuvoletta nasce "in scrittura": il testo cresce con
    aggiungi_testo() e mostra il cursore ▍ finché non si chiama fine_scrittura().
    """

    CURSORE = " ▍"

    def __init__(self, master, mittente: str, testo: str, nome: str | None = None,
                 larghezza_testo: int = 400, in_scrittura: bool = False):
        if mittente not in MITTENTI:
            raise ValueError(f"Mittente sconosciuto: {mittente!r} (usa {MITTENTI})")
        super().__init__(master, fg_color="transparent")
        self.mittente = mittente
        self._testo = testo
        self._in_scrittura = in_scrittura
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
            text=self._testo_visibile(),
            font=tema.font(14),
            text_color=COLORI["testo_su_accento"] if da_utente else COLORI["testo"],
            wraplength=larghezza_testo,
            justify="left",
            anchor="w",
        )
        self.etichetta.pack(padx=tema.SPAZIO_M, pady=tema.SPAZIO_S)

    @property
    def testo(self) -> str:
        """Il testo del messaggio, senza il cursore."""
        return self._testo

    def aggiungi_testo(self, pezzo: str) -> None:
        self._testo += pezzo
        self.etichetta.configure(text=self._testo_visibile())

    def fine_scrittura(self) -> None:
        """Toglie il cursore e gli spazi o le righe vuote rimasti in fondo."""
        self._in_scrittura = False
        self._testo = self._testo.rstrip()
        self.etichetta.configure(text=self._testo_visibile())

    def _testo_visibile(self) -> str:
        return self._testo + self.CURSORE if self._in_scrittura else self._testo

    @property
    def larghezza_testo(self) -> int:
        return self.etichetta.cget("wraplength")

    def imposta_larghezza(self, larghezza_testo: int) -> None:
        """Larghezza massima del testo prima di andare a capo, in pixel."""
        self.etichetta.configure(wraplength=larghezza_testo)


class MenuModello(ctk.CTkFrame):
    """Menu a tendina per scegliere il modello, che si apre e si chiude con
    un'animazione dentro la barra laterale (▾ chiuso, ▴ aperto).

    Con più di VOCI_MAX modelli l'elenco resta alto VOCI_MAX voci e scorre.
    """

    ALTEZZA_VOCE = 36
    VOCI_MAX = 4

    def __init__(self, master, valori: list[str] | None = None, al_cambio=None):
        super().__init__(master, fg_color="transparent")
        self.al_cambio = al_cambio  # chiamata con il nome del modello scelto
        self.aperto = False
        self._animazione = Animazione(self, durata=0.18)
        self._valori: list[str] = []
        self._scelto = ""
        self.pulsanti_voce: list[ctk.CTkButton] = []

        # Intestazione: nome del modello scelto a sinistra, freccia a destra.
        # Tutta l'intestazione è cliccabile e si colora al passaggio del mouse.
        self.intestazione = ctk.CTkFrame(
            self, height=40, corner_radius=tema.RAGGIO_CONTROLLO, fg_color=COLORI["controllo"],
        )
        self.intestazione.pack(fill="x")
        self.intestazione.pack_propagate(False)
        self.freccia = ctk.CTkLabel(
            self.intestazione, text="▾", font=tema.font(18),
            text_color=COLORI["accento_testo"], width=16,
        )
        self.freccia.pack(side="right", padx=(0, tema.SPAZIO_M))
        self.etichetta_scelta = ctk.CTkLabel(
            self.intestazione, text="", font=tema.font(13),
            text_color=COLORI["testo"], anchor="w",
        )
        self.etichetta_scelta.pack(side="left", fill="x", expand=True, padx=(tema.SPAZIO_M, 0))
        for parte in (self.intestazione, self.etichetta_scelta, self.freccia):
            parte.bind("<Button-1>", lambda _: self.alterna())
            parte.bind("<Enter>", lambda _: self._evidenzia(True))
            parte.bind("<Leave>", lambda _: self._evidenzia(False))
            parte.configure(cursor="hand2")

        # Elenco delle voci: parte chiuso (non visibile, alto 1 pixel)
        self.lista = ctk.CTkFrame(
            self, height=1, corner_radius=tema.RAGGIO_CONTROLLO, fg_color=COLORI["controllo"],
        )
        self.lista.pack_propagate(False)  # l'altezza la decide l'animazione
        self._contenitore_voci = self.lista
        self.imposta_valori(valori or ["Nessun modello"])

    # --- Valori ---

    @property
    def valori(self) -> list[str]:
        return list(self._valori)

    def get(self) -> str:
        return self._scelto

    def set(self, valore: str) -> None:
        self._scelto = valore
        self.etichetta_scelta.configure(text=valore)
        self._evidenzia_voce_scelta()

    def imposta_valori(self, valori: list[str]) -> None:
        """Sostituisce le voci; la scelta resta se il modello c'è ancora."""
        self._valori = list(valori)
        if self.aperto:
            self.chiudi(animazione=False)
        if self._contenitore_voci is not self.lista:
            self._contenitore_voci.destroy()
        for pulsante in self.pulsanti_voce:
            pulsante.destroy()
        self.pulsanti_voce = []

        # con tante voci serve un elenco che scorre
        if len(self._valori) > self.VOCI_MAX:
            self._contenitore_voci = ctk.CTkScrollableFrame(
                self.lista, fg_color="transparent", corner_radius=0,
                scrollbar_button_color=COLORI["bordo"],
                scrollbar_button_hover_color=COLORI["testo_leggero"],
            )
            self._contenitore_voci.pack(fill="both", expand=True, pady=tema.SPAZIO_S)
            margine_verticale = 0
        else:
            self._contenitore_voci = self.lista
            margine_verticale = tema.SPAZIO_S

        for indice, valore in enumerate(self._valori):
            pulsante = ctk.CTkButton(
                self._contenitore_voci,
                text=valore,
                height=self.ALTEZZA_VOCE,
                corner_radius=tema.SPAZIO_S,
                anchor="w",
                font=tema.font(13),
                fg_color="transparent",
                hover_color=COLORI["bordo"],
                text_color=COLORI["testo"],
                command=lambda v=valore: self._voce_scelta(v),
            )
            sopra = margine_verticale if indice == 0 else 0
            sotto = margine_verticale if indice == len(self._valori) - 1 else 0
            pulsante.pack(fill="x", padx=tema.SPAZIO_S, pady=(sopra, sotto))
            self.pulsanti_voce.append(pulsante)

        self.set(self._scelto if self._scelto in self._valori else self._valori[0])

    def _voce_scelta(self, valore: str) -> None:
        self.set(valore)
        self.chiudi()
        if self.al_cambio is not None:
            self.al_cambio(valore)

    def _evidenzia_voce_scelta(self) -> None:
        for pulsante in self.pulsanti_voce:
            scelto = pulsante.cget("text") == self._scelto
            pulsante.configure(fg_color=COLORI["nuvola_modello"] if scelto else "transparent")

    def _evidenzia(self, sopra: bool) -> None:
        # <Leave> arriva anche passando dall'intestazione a una sua etichetta:
        # controlliamo dove si trova davvero il mouse
        if not sopra:
            x, y = self.winfo_pointerxy()
            sotto_mouse = self.winfo_containing(x, y)
            parti = {str(w) for w in (self.intestazione, self.etichetta_scelta, self.freccia)}
            sopra = sotto_mouse is not None and any(
                str(sotto_mouse).startswith(parte) for parte in parti)
        self.intestazione.configure(fg_color=COLORI["bordo"] if sopra else COLORI["controllo"])

    # --- Apertura e chiusura ---

    @property
    def in_animazione(self) -> bool:
        return self._animazione.in_corso

    def altezza_lista_aperta(self) -> int:
        voci = min(len(self._valori), self.VOCI_MAX)
        return voci * self.ALTEZZA_VOCE + 2 * tema.SPAZIO_S

    def alterna(self) -> None:
        if self.aperto:
            self.chiudi()
        else:
            self.apri()

    def apri(self, animazione: bool = True) -> None:
        self.aperto = True
        self.freccia.configure(text="▴")
        self.lista.pack(fill="x", pady=(tema.SPAZIO_S, 0))
        self._cambia_altezza(self.altezza_lista_aperta(), animazione)

    def chiudi(self, animazione: bool = True) -> None:
        self.aperto = False
        self.freccia.configure(text="▾")
        self._cambia_altezza(1, animazione, alla_fine=self.lista.pack_forget)

    def _cambia_altezza(self, arrivo: int, animazione: bool, alla_fine=None) -> None:
        applica = lambda altezza: self.lista.configure(height=max(1, altezza))
        if animazione:
            self._animazione.avvia(self.lista.cget("height"), arrivo, applica, alla_fine)
        else:
            self._animazione.ferma()
            applica(arrivo)
            if alla_fine is not None:
                alla_fine()


class BarraLaterale(ctk.CTkFrame):
    """Pannello a sinistra, retraibile.

    - Aperta (240 px): modello, interruttori, nuova chat, stato e tema.
    - Chiusa (64 px): striscia con le sole icone essenziali.
    Il passaggio tra le due è animato; durante l'animazione il pannello
    resta vuoto, così cambia solo la larghezza e il movimento è fluido.
    A fine animazione viene chiamata `alla_fine_animazione`, se indicata.
    """

    def __init__(self, master, alla_fine_animazione=None):
        super().__init__(
            master,
            width=tema.LARGHEZZA_BARRA,
            corner_radius=tema.RAGGIO_PANNELLO,
            fg_color=COLORI["barra_laterale"],
        )
        self.pack_propagate(False)  # la larghezza la decidiamo noi, non il contenuto
        self.aperta = True
        self._animazione = Animazione(self, durata=0.2)
        self._alla_fine_animazione = alla_fine_animazione
        self.tema_scelto: str | None = None  # resta None finché l'utente non cambia tema
        self._timer_lampeggio = None

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
        self.menu_modello = MenuModello(contenitore)
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

    # --- Stato della connessione ---

    STATI = {
        "connessione": ("Connessione...", "stato_errore"),
        "connesso": ("Connesso", "stato_ok"),
        "errore": ("Non connesso", "stato_errore"),
    }

    INTERVALLO_LAMPEGGIO = 500  # millisecondi

    def imposta_stato(self, stato: str) -> None:
        """Aggiorna testo e pallini: "connessione", "connesso" oppure "errore".

        Durante la connessione il pallino rosso lampeggia.
        """
        testo, colore = self.STATI[stato]
        self.testo_stato.configure(text=testo)
        if self._timer_lampeggio is not None:
            self.after_cancel(self._timer_lampeggio)
            self._timer_lampeggio = None
        self._colora_pallini(COLORI[colore])
        if stato == "connessione":
            self._timer_lampeggio = self.after(self.INTERVALLO_LAMPEGGIO, self._lampeggia, False)

    def _lampeggia(self, acceso: bool) -> None:
        # spento = stesso colore della barra, cioè invisibile
        self._colora_pallini(COLORI["stato_errore"] if acceso else COLORI["barra_laterale"])
        self._timer_lampeggio = self.after(self.INTERVALLO_LAMPEGGIO, self._lampeggia, not acceso)

    def _colora_pallini(self, colore) -> None:
        for pallino in (self.pallino, self.pallino_chiuso):
            pallino.configure(text_color=colore)

    # --- Tema ---

    def _interruttore_tema_cambiato(self) -> None:
        self.tema_scelto = "dark" if self.interruttore_tema.get() else "light"
        ctk.set_appearance_mode(self.tema_scelto)
        self._aggiorna_icona_tema()

    def _pulsante_tema_premuto(self) -> None:
        self.interruttore_tema.toggle()  # cambia il tema e tiene sincronizzati i due comandi

    def _aggiorna_icona_tema(self) -> None:
        # l'icona mostra il tema in cui si passa cliccando
        self.pulsante_tema_icona.configure(text="☀" if self.interruttore_tema.get() else "☾")

    # --- Apertura e chiusura ---

    @property
    def in_animazione(self) -> bool:
        return self._animazione.in_corso

    def apri(self, animazione: bool = True) -> None:
        self._vai_a(True, animazione)

    def chiudi(self, animazione: bool = True) -> None:
        self._vai_a(False, animazione)

    def alterna(self, animazione: bool = True) -> None:
        self._vai_a(not self.aperta, animazione)

    def _vai_a(self, aperta: bool, animazione: bool) -> None:
        self._animazione.ferma()  # cambio di idea a metà: si riparte da dove si è
        self.aperta = aperta
        arrivo = tema.LARGHEZZA_BARRA if aperta else tema.LARGHEZZA_BARRA_CHIUSA
        contenuto = self.contenuto_aperto if aperta else self.contenuto_chiuso
        if not animazione:
            self.configure(width=arrivo)
            self._mostra(contenuto)
            return
        self._mostra(None)
        self._animazione.avvia(self.cget("width"), arrivo,
                               applica=lambda larghezza: self.configure(width=larghezza),
                               alla_fine=lambda: self._fine_animazione(contenuto))

    def _fine_animazione(self, contenuto) -> None:
        self._mostra(contenuto)
        if self._alla_fine_animazione is not None:
            self._alla_fine_animazione()

    def _mostra(self, contenuto) -> None:
        """Mostra uno dei due contenuti (o nessuno, con None)."""
        for altro in (self.contenuto_aperto, self.contenuto_chiuso):
            if altro is not contenuto:
                altro.pack_forget()
        if contenuto is not None:
            contenuto.pack(fill="both", expand=True, pady=tema.RAGGIO_PANNELLO)


class BarraScrittura(ctk.CTkFrame):
    """Casella arrotondata "a pillola" con il pulsante di invio.

    La casella cresce con il testo (anche quando va a capo da solo) fino a
    RIGHE_MAX righe; oltre, il testo scorre dentro la casella.
    """

    ALTEZZA = 56
    ALTEZZA_CASELLA = ALTEZZA - 2 * tema.SPAZIO_M  # una riga
    RIGHE_MAX = 5
    SUGGERIMENTO = "Scrivi un messaggio..."

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)

        # La "pillola" è un contenitore arrotondato con dentro una casella di testo
        # senza angoli: CTkTextbox con angoli grandi aggiungerebbe troppo margine.
        self.pillola = pillola = ctk.CTkFrame(
            self,
            corner_radius=self.ALTEZZA // 2,
            border_width=1,
            fg_color=COLORI["pannello"],
            border_color=COLORI["bordo"],
        )
        pillola.grid(row=0, column=0, sticky="ew")
        self.casella = ctk.CTkTextbox(
            pillola,
            height=self.ALTEZZA_CASELLA,
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
        self.suggerimento.bind("<Button-1>", lambda _: self.casella.focus_set())
        self.casella.bind("<FocusIn>", lambda _: self._aggiorna_suggerimento())
        self.casella.bind("<FocusOut>", lambda _: self._aggiorna_suggerimento())

        # <<Modified>> arriva a ogni modifica del testo, anche fatta dal programma
        self.righe_visibili = 1
        self.casella.bind("<<Modified>>", self._testo_cambiato)
        self.casella.bind("<Configure>", lambda _: self._adatta_altezza())
        self._aggiorna_suggerimento()

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
        # sticky="s": quando la casella cresce, il pulsante resta in basso
        self.pulsante_invia.grid(row=0, column=1, sticky="s", padx=(tema.SPAZIO_S, 0))

    def modalita_stop(self, attiva: bool) -> None:
        """Mentre il modello risponde il pulsante diventa ■ (Stop)."""
        self.pulsante_invia.configure(text="■" if attiva else "➤")

    def _testo_cambiato(self, _evento=None) -> None:
        self.casella.edit_modified(False)  # così il prossimo cambiamento genera un nuovo evento
        self._adatta_altezza()
        self._aggiorna_suggerimento()

    def _adatta_altezza(self) -> None:
        testo_tk = self.casella._textbox  # il widget Text di Tk dentro CTkTextbox
        # "displaylines" conta anche le righe che vanno a capo da sole
        conteggio = testo_tk.count("1.0", "end-1c", "displaylines")
        if isinstance(conteggio, tuple):
            conteggio = conteggio[0]
        righe = min(self.RIGHE_MAX, (conteggio or 0) + 1)
        if righe == self.righe_visibili:
            return
        self.righe_visibili = righe
        # Altezza reale di una riga: se la prima riga è visibile la misuriamo,
        # altrimenti la stimiamo dal font (Tk aggiunge un paio di pixel).
        misura = testo_tk.dlineinfo("1.0")
        riga = misura[3] if misura else tkinter.font.Font(
            font=testo_tk.cget("font")).metrics("linespace") + 2
        bordi = 2 * (int(testo_tk.cget("pady")) + int(testo_tk.cget("borderwidth")))
        # Tk misura in pixel reali, CustomTkinter vuole pixel "logici" (zoom di Windows)
        scala = ctk.ScalingTracker.get_widget_scaling(self)
        altezza = math.ceil((righe * riga + bordi) / scala)  # per eccesso: niente righe tagliate
        self.casella.configure(height=max(self.ALTEZZA_CASELLA, altezza))
        self.casella.see("insert")

    def _aggiorna_suggerimento(self) -> None:
        """Il testo di aiuto si vede solo con la casella vuota e senza il cursore dentro."""
        vuota = not self.casella.get("1.0", "end-1c")
        if vuota and self.focus_get() is not self.casella._textbox:
            self.suggerimento.place(x=0, rely=0.5, anchor="w")
        else:
            self.suggerimento.place_forget()


class IndicatorePensiero(ctk.CTkFrame):
    """Nuvoletta "il modello sta pensando..." con i puntini animati."""

    INTERVALLO = 400  # millisecondi tra un fotogramma dei puntini e il successivo

    def __init__(self, master, nome_modello: str):
        super().__init__(master, fg_color="transparent")
        self._base = f"{nome_modello} sta pensando"
        self._puntini = 1
        fumetto = ctk.CTkFrame(
            self, corner_radius=tema.RAGGIO_NUVOLA, fg_color=COLORI["nuvola_modello"]
        )
        fumetto.pack(anchor="w")
        self._etichetta = ctk.CTkLabel(
            fumetto, text=self._testo_corrente(), font=tema.font(14, corsivo=True),
            text_color=COLORI["testo_leggero"], anchor="w",
        )
        self._etichetta.pack(padx=tema.SPAZIO_M, pady=tema.SPAZIO_S)
        self._timer = self.after(self.INTERVALLO, self._anima)

    @property
    def testo(self) -> str:
        return self._etichetta.cget("text")

    def _testo_corrente(self) -> str:
        # i puntini mancanti sono spazi, così la nuvoletta non cambia larghezza
        return self._base + "." * self._puntini + " " * (3 - self._puntini)

    def _anima(self) -> None:
        self._puntini = self._puntini % 3 + 1
        self._etichetta.configure(text=self._testo_corrente())
        self._timer = self.after(self.INTERVALLO, self._anima)

    def destroy(self):
        self.after_cancel(self._timer)
        super().destroy()


class AvvisoErrore(ctk.CTkFrame):
    """Avviso rosso arrotondato dentro la chat, con il pulsante Riprova.

    Premendo Riprova l'avviso sparisce e viene chiamata `al_riprova`.
    """

    def __init__(self, master, messaggio: str, al_riprova, larghezza_testo: int = 400):
        super().__init__(
            master,
            corner_radius=tema.RAGGIO_PANNELLO,
            border_width=2,
            fg_color=COLORI["pannello"],
            border_color=COLORI["errore"],
        )
        self._al_riprova = al_riprova
        self._etichetta = ctk.CTkLabel(
            self, text=messaggio, font=tema.font(14), text_color=COLORI["errore"],
            wraplength=larghezza_testo, justify="left", anchor="w",
        )
        self._etichetta.pack(anchor="w", padx=tema.SPAZIO_M, pady=(tema.SPAZIO_M, tema.SPAZIO_S))
        self.pulsante_riprova = ctk.CTkButton(
            self,
            text="↻  Riprova",
            width=112,
            height=32,
            corner_radius=tema.RAGGIO_CONTROLLO,
            font=tema.font(13, grassetto=True),
            fg_color="transparent",
            hover_color=COLORI["bordo"],
            border_width=1,
            border_color=COLORI["errore"],
            text_color=COLORI["errore"],
            command=self._riprova,
        )
        self.pulsante_riprova.pack(anchor="w", padx=tema.SPAZIO_M, pady=(0, tema.SPAZIO_M))

    @property
    def messaggio(self) -> str:
        return self._etichetta.cget("text")

    def imposta_larghezza(self, larghezza_testo: int) -> None:
        self._etichetta.configure(wraplength=larghezza_testo)

    def _riprova(self) -> None:
        al_riprova = self._al_riprova
        self.destroy()
        al_riprova()


class SchermataVuota(ctk.CTkFrame):
    """Benvenuto mostrato quando la chat è vuota, con domande d'esempio cliccabili."""

    ESEMPI = (
        "Spiegami cos'è un modello linguistico in tre frasi",
        "Dammi tre idee per un progetto di scuola in Python",
        "Scrivi una breve poesia sull'autunno",
    )

    def __init__(self, master, al_click_esempio):
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(
            self, text="Ciao! Come posso aiutarti?", font=tema.font(24, grassetto=True),
            text_color=COLORI["testo"],
        ).pack(pady=(tema.SPAZIO_XL * 3, tema.SPAZIO_S))
        ctk.CTkLabel(
            self, text="Scrivi una domanda qui sotto oppure prova uno di questi esempi:",
            font=tema.font(14), text_color=COLORI["testo_leggero"],
        ).pack(pady=(0, tema.SPAZIO_L))

        self.pulsanti_esempio = []
        for esempio in self.ESEMPI:
            pulsante = ctk.CTkButton(
                self,
                text=esempio,
                height=44,
                corner_radius=tema.RAGGIO_NUVOLA,
                border_width=1,
                font=tema.font(14),
                fg_color=COLORI["pannello"],
                hover_color=COLORI["nuvola_modello"],
                border_color=COLORI["bordo"],
                text_color=COLORI["testo"],
                command=lambda testo=esempio: al_click_esempio(testo),
            )
            pulsante.pack(pady=(0, tema.SPAZIO_S), ipadx=tema.SPAZIO_M)
            self.pulsanti_esempio.append(pulsante)
