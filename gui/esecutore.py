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
        self._in_corso += 1
        threading.Thread(target=self._lavora, args=(lavoro, al_successo, all_errore),
                         daemon=True).start()
        if self._timer is None:
            self._timer = self._widget.after(INTERVALLO_CONTROLLO, self._controlla_coda)

    def _lavora(self, lavoro, al_successo, all_errore) -> None:
        # Gira nel thread di lavoro: qui niente grafica, solo la coda
        try:
            risultato = lavoro()
        except Exception as errore:  # qualunque problema va mostrato all'utente
            self._coda.put((all_errore, errore))
        else:
            self._coda.put((al_successo, risultato))

    def _controlla_coda(self) -> None:
        # Gira nel thread della grafica
        self._timer = None
        try:
            while True:
                try:
                    funzione, valore = self._coda.get_nowait()
                except queue.Empty:
                    break
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
