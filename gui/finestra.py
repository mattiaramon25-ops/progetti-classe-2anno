"""Finestra principale: barra laterale a sinistra, chat e barra di scrittura a destra.

Le richieste a LM Studio girano in un thread a parte (vedi esecutore.py),
così la finestra resta sempre reattiva anche mentre il modello risponde.
"""

import threading

import customtkinter as ctk

from gui import tema
from gui.componenti import (AvvisoErrore, BarraLaterale, BarraScrittura,
                            IndicatorePensiero, Nuvoletta)
from gui.esecutore import Esecutore
from gui.lm_api import ClientLM, ErroreLM, solo_modelli_chat
from gui.tema import COLORI


class Finestra(ctk.CTk):
    def __init__(self, client: ClientLM | None = None, modello_preferito: str | None = None):
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
        # add="+": si aggiunge al collegamento interno di CustomTkinter che aggiorna
        # l'area scorrevole, invece di sostituirlo (altrimenti la chat non scorre)
        self.chat.bind("<Configure>", self._chat_ridimensionata, add="+")

        self.scrittura = BarraScrittura(area)
        self.scrittura.grid(
            row=1, column=0, sticky="ew", padx=tema.SPAZIO_L, pady=(tema.SPAZIO_M, tema.SPAZIO_S)
        )
        self.scrittura.pulsante_invia.configure(command=self._pulsante_premuto)
        self.scrittura.casella.bind("<Return>", self._tasto_invio)
        self.bind("<Escape>", lambda _: self.ferma())

        self.nuvolette: list[Nuvoletta] = []
        self._larghezza_chat = 700

        # Scorciatoie, attive anche mentre si scrive nella casella:
        # Ctrl+B apre/chiude la barra laterale, Ctrl+N inizia una nuova chat
        scorciatoie = {"b": self.barra.alterna, "n": self.nuova_chat}
        for lettera, azione in scorciatoie.items():
            gestore = lambda _evento, azione=azione: self._scorciatoia(azione)
            for tasto in (f"<Control-{lettera}>", f"<Control-{lettera.upper()}>"):
                self.bind(tasto, gestore)
                self.scrittura.casella.bind(tasto, gestore)
        for pulsante in (self.barra.pulsante_nuova_chat, self.barra.pulsante_nuova_chat_icona):
            pulsante.configure(command=self.nuova_chat)

        # --- Collegamento a LM Studio ---
        self._client = client
        self._modello_preferito = modello_preferito
        self.esecutore = Esecutore(self)
        self.connesso = False
        self.in_attesa = False
        self.indicatore: IndicatorePensiero | None = None
        self.nota_interrotta: ctk.CTkLabel | None = None
        # Ogni domanda ha un "biglietto": se l'utente preme Stop il biglietto
        # cambia, e le risposte che arrivano dopo per quello vecchio si ignorano.
        self._richiesta: object | None = None
        self._ferma_stream = threading.Event()
        self._nuvoletta_in_scrittura: Nuvoletta | None = None
        self._scorrimento_programmato = False
        # Memoria (come client3): gli scambi completi domanda/risposta della chat.
        # Viene inviata al modello solo se l'interruttore Memoria è acceso.
        self.cronologia: list[dict] = []
        if client is not None:
            self.connetti()

    # --- Connessione ---

    def connetti(self) -> None:
        """Chiede a LM Studio i modelli caricati (in background)."""
        self.barra.imposta_stato("connessione")
        self.esecutore.esegui(self._client.modelli, self._modelli_ricevuti,
                              self._connessione_fallita)

    def _modelli_ricevuti(self, nomi: list[str]) -> None:
        modelli = solo_modelli_chat(nomi)
        preferito = self._modello_preferito
        if preferito and preferito not in modelli:
            modelli.insert(0, preferito)  # LM Studio può caricarlo al primo messaggio
        if not modelli:
            self._connessione_fallita(
                ErroreLM("Nessun modello caricato in LM Studio: caricane uno e premi Riprova.")
            )
            return
        self.barra.menu_modello.configure(values=modelli)
        self.barra.menu_modello.set(preferito or modelli[0])
        self.connesso = True
        self.barra.imposta_stato("connesso")

    def _connessione_fallita(self, errore: Exception) -> None:
        self.connesso = False
        self.barra.imposta_stato("errore")
        self.mostra_errore(testo_errore(errore), al_riprova=self.connetti)

    # --- Domanda e risposta ---

    def invia(self) -> None:
        """Invia il testo scritto nella casella (se c'è e se si può)."""
        if self.in_attesa:
            return  # il testo resta nella casella, pronto per dopo
        testo = self.scrittura.casella.get("1.0", "end-1c").strip()
        if not testo:
            return
        if not self.connesso:
            self.mostra_errore("Non sei connesso a LM Studio.", al_riprova=self.connetti)
            return
        self.scrittura.casella.delete("1.0", "end")
        self.aggiungi_messaggio("utente", testo)
        self._chiedi(testo)

    def _chiedi(self, testo: str) -> None:
        if self.in_attesa:
            return
        modello = self.barra.menu_modello.get()
        domanda = {"role": "user", "content": testo}
        if self.barra.memoria.get():
            messaggi = self.cronologia + [domanda]  # il modello "ricorda" la chat
        else:
            messaggi = [domanda]  # ogni domanda è indipendente
        richiesta = self._inizia_attesa(modello)
        solo_se_attuale = lambda funzione: self._solo_se_attuale(richiesta, funzione)
        all_errore = solo_se_attuale(lambda errore: self._risposta_fallita(testo, errore))

        if self.barra.streaming.get():
            # Streaming (come client2): il testo arriva a pezzi
            self.esecutore.esegui_a_pezzi(
                lambda: self._client.chiedi_stream(modello, messaggi),
                al_pezzo=solo_se_attuale(lambda pezzo: self._pezzo_ricevuto(modello, pezzo)),
                alla_fine=solo_se_attuale(lambda _: self._stream_finito(testo, modello)),
                all_errore=all_errore,
                ferma=self._ferma_stream,
            )
        else:
            # Senza streaming (come client1): la risposta arriva tutta insieme
            self.esecutore.esegui(
                lambda: self._client.chiedi(modello, messaggi),
                al_successo=solo_se_attuale(
                    lambda risposta: self._risposta_ricevuta(testo, modello, risposta)),
                all_errore=all_errore,
            )

    def _solo_se_attuale(self, richiesta: object, funzione):
        """Avvolge una funzione di risposta: la esegue solo se nel frattempo
        l'utente non ha premuto Stop (cioè se la richiesta è ancora quella attuale)."""
        def avvolta(valore):
            if richiesta is self._richiesta:
                funzione(valore)
        return avvolta

    def _inizia_attesa(self, modello: str) -> object:
        self.in_attesa = True
        self._richiesta = object()
        self._ferma_stream = threading.Event()
        self.scrittura.modalita_stop(True)
        self.indicatore = IndicatorePensiero(self.chat, modello)
        self.indicatore.pack(anchor="w", padx=tema.SPAZIO_L, pady=tema.SPAZIO_S)
        self._scorri_in_fondo()
        return self._richiesta

    def _fine_attesa(self) -> None:
        self.in_attesa = False
        self._richiesta = None
        self.scrittura.modalita_stop(False)
        self._togli_indicatore()
        if self._nuvoletta_in_scrittura is not None:
            self._nuvoletta_in_scrittura.fine_scrittura()
            self._nuvoletta_in_scrittura = None

    def _togli_indicatore(self) -> None:
        if self.indicatore is not None:
            self.indicatore.destroy()
            self.indicatore = None

    def _risposta_ricevuta(self, testo: str, modello: str, risposta: str) -> None:
        self._fine_attesa()
        self.aggiungi_messaggio("modello", risposta, nome=modello)
        self._ricorda(testo, risposta)

    def _pezzo_ricevuto(self, modello: str, pezzo: str) -> None:
        nuvoletta = self._nuvoletta_in_scrittura
        if nuvoletta is None:
            pezzo = pezzo.lstrip()  # spazi e righe vuote iniziali non servono
            if not pezzo:
                return
            # al primo pezzo vero la nuvoletta prende il posto di "sta pensando..."
            self._togli_indicatore()
            self._nuvoletta_in_scrittura = self.aggiungi_messaggio(
                "modello", pezzo, nome=modello, in_scrittura=True)
        else:
            nuvoletta.aggiungi_testo(pezzo)
            self._scorri_in_fondo()

    def _stream_finito(self, testo: str, modello: str) -> None:
        nuvoletta = self._nuvoletta_in_scrittura
        self._fine_attesa()  # toglie il cursore e gli spazi finali
        if nuvoletta is None:
            self.aggiungi_messaggio("modello", "(nessuna risposta)", nome=modello)
        else:
            self._ricorda(testo, nuvoletta.testo)

    def _ricorda(self, domanda: str, risposta: str) -> None:
        """Solo gli scambi completi entrano in memoria: le domande fallite o
        interrotte restano fuori, come in client3."""
        self.cronologia.append({"role": "user", "content": domanda})
        self.cronologia.append({"role": "assistant", "content": risposta})

    def _risposta_fallita(self, testo: str, errore: Exception) -> None:
        self._fine_attesa()
        self.mostra_errore(testo_errore(errore), al_riprova=lambda: self._chiedi(testo))

    def ferma(self, mostra_nota: bool = True) -> None:
        """Pulsante Stop o tasto Esc: smette di aspettare la risposta.

        Il testo già arrivato resta; quello che arriva dopo viene ignorato.
        """
        if not self.in_attesa:
            return
        self._ferma_stream.set()  # lo streaming si chiude al pezzo successivo
        self._fine_attesa()
        if not mostra_nota:
            return
        self.nota_interrotta = ctk.CTkLabel(
            self.chat, text="Risposta interrotta", font=tema.font(12, corsivo=True),
            text_color=COLORI["testo_leggero"], height=20,
        )
        self.nota_interrotta.pack(anchor="w", padx=tema.SPAZIO_L + tema.SPAZIO_S)
        self._scorri_in_fondo()

    def nuova_chat(self) -> None:
        """Svuota la chat e la memoria. Il testo nella casella resta."""
        self.ferma(mostra_nota=False)
        for elemento in self.chat.winfo_children():
            elemento.destroy()
        self.nuvolette.clear()
        self.cronologia.clear()
        self.nota_interrotta = None
        self.scrittura.casella.focus_set()

    def _pulsante_premuto(self) -> None:
        if self.in_attesa:
            self.ferma()
        else:
            self.invia()

    def _tasto_invio(self, evento) -> str | None:
        if evento.state & 0x0001:  # con Shift premuto: va a capo come al solito
            return None
        self.invia()
        return "break"  # niente "a capo" nella casella

    # --- Contenuto della chat ---

    def aggiungi_messaggio(self, mittente: str, testo: str, nome: str | None = None,
                           in_scrittura: bool = False) -> Nuvoletta:
        """Aggiunge una nuvoletta in fondo alla chat e la restituisce."""
        nuvoletta = Nuvoletta(
            self.chat, mittente, testo, nome=nome,
            larghezza_testo=self._larghezza_testo(), in_scrittura=in_scrittura,
        )
        nuvoletta.pack(
            anchor="e" if mittente == "utente" else "w",
            padx=tema.SPAZIO_L,
            pady=tema.SPAZIO_S,
        )
        self.nuvolette.append(nuvoletta)
        self._scorri_in_fondo()
        return nuvoletta

    def mostra_errore(self, messaggio: str, al_riprova) -> AvvisoErrore:
        """Mostra un avviso rosso in fondo alla chat, con il pulsante Riprova."""
        avviso = AvvisoErrore(self.chat, messaggio, al_riprova, self._larghezza_testo())
        avviso.pack(anchor="w", padx=tema.SPAZIO_L, pady=tema.SPAZIO_S)
        self._scorri_in_fondo()
        return avviso

    def _scorri_in_fondo(self) -> None:
        if self._scorrimento_programmato:
            return  # con lo streaming arrivano tanti pezzi: basta scorrere una volta
        self._scorrimento_programmato = True

        def scorri():
            self._scorrimento_programmato = False
            self.update_idletasks()  # prima la chat deve sapere quanto è alta
            # CTkScrollableFrame non offre un metodo pubblico per scorrere
            self.chat._parent_canvas.yview_moveto(1.0)
        self.after_idle(scorri)

    def adatta_nuvolette(self, larghezza_chat: int) -> None:
        """Nuvolette e avvisi occupano al massimo il 70% della larghezza della chat."""
        self._larghezza_chat = larghezza_chat
        for elemento in self.chat.winfo_children():
            if hasattr(elemento, "imposta_larghezza"):
                elemento.imposta_larghezza(self._larghezza_testo())

    def _larghezza_testo(self) -> int:
        larghezza_nuvola = int(self._larghezza_chat * tema.LARGHEZZA_MAX_NUVOLA)
        return larghezza_nuvola - 2 * tema.SPAZIO_M  # tolti i margini interni

    # --- Barra laterale e ridimensionamento ---

    def _scorciatoia(self, azione) -> str:
        azione()
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

    def destroy(self):
        self.esecutore.ferma()
        super().destroy()


def testo_errore(errore: Exception) -> str:
    """Messaggio da mostrare all'utente: gli ErroreLM sono già scritti per lui."""
    if isinstance(errore, ErroreLM):
        return str(errore)
    return f"Errore inatteso: {errore}"
