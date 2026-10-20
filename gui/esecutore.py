"""Esegue lavori lenti (le richieste a LM Studio) senza bloccare la finestra.

Tkinter non va mai toccato da un thread diverso da quello della grafica.
Per questo il lavoro gira in un thread a parte e mette il risultato in una
coda; la grafica controlla la coda ogni pochi millisecondi con after() e
chiama le funzioni di risposta dal proprio thread.
"""

import queue
import threading
import tkinter

INTERVALLO_CONTROLLO = 30  # millisecondi tra un controllo della coda e il successivo


class Esecutore:
    def __init__(self, widget: tkinter.Misc):
        self._widget = widget
        self._coda: queue.Queue = queue.Queue()
        self._in_corso = 0
        self._timer = None

    @property
    def occupato(self) -> bool:
        return self._in_corso > 0

    def esegui(self, lavoro, al_successo, all_errore) -> None:
        """Esegue lavoro() in un thread; poi, nel thread della grafica, chiama
        al_successo(risultato) oppure all_errore(eccezione)."""
        self._avvia(self._lavora, (lavoro, al_successo, all_errore))

    def esegui_a_pezzi(self, lavoro, al_pezzo, alla_fine, all_errore,
                       ferma: threading.Event) -> None:
        """Come esegui(), ma lavoro() restituisce tanti pezzi (per lo streaming).

        Ogni pezzo arriva a al_pezzo(pezzo) appena è pronto; alla fine viene
        chiamata alla_fine(None), oppure all_errore(eccezione) se qualcosa va storto.
        Se `ferma` viene attivato, il lavoro si interrompe al pezzo successivo.
        """
        self._avvia(self._lavora_a_pezzi, (lavoro, al_pezzo, alla_fine, all_errore, ferma))

    def _avvia(self, funzione, argomenti) -> None:
        self._in_corso += 1
        threading.Thread(target=funzione, args=argomenti, daemon=True).start()
        if self._timer is None:
            self._timer = self._widget.after(INTERVALLO_CONTROLLO, self._controlla_coda)

    # I metodi _lavora... girano nel thread di lavoro: qui niente grafica, solo la coda.
    # Ogni elemento della coda è (funzione, valore, ultimo); "ultimo" indica che il
    # lavoro è finito.

    def _lavora(self, lavoro, al_successo, all_errore) -> None:
        try:
            risultato = lavoro()
        except Exception as errore:  # qualunque problema va mostrato all'utente
            self._coda.put((all_errore, errore, True))
        else:
            self._coda.put((al_successo, risultato, True))

    def _lavora_a_pezzi(self, lavoro, al_pezzo, alla_fine, all_errore, ferma) -> None:
        try:
            pezzi = lavoro()
            try:
                for pezzo in pezzi:
                    if ferma.is_set():
                        break
                    self._coda.put((al_pezzo, pezzo, False))
            finally:
                if hasattr(pezzi, "close"):
                    pezzi.close()  # chiude anche la connessione con LM Studio
        except Exception as errore:
            self._coda.put((all_errore, errore, True))
        else:
            self._coda.put((alla_fine, None, True))

    def _controlla_coda(self) -> None:
        # Gira nel thread della grafica
        self._timer = None
        try:
            while True:
                try:
                    funzione, valore, ultimo = self._coda.get_nowait()
                except queue.Empty:
                    break
                if ultimo:
                    self._in_corso -= 1
                funzione(valore)
        finally:
            # anche se una funzione di risposta va in errore, si continua a controllare
            if self._in_corso > 0:
                self._timer = self._widget.after(INTERVALLO_CONTROLLO, self._controlla_coda)

    def ferma(self) -> None:
        """Smette di controllare la coda (da chiamare quando si chiude la finestra)."""
        if self._timer is not None:
            self._widget.after_cancel(self._timer)
            self._timer = None
