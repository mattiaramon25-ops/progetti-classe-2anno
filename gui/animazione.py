"""Animazione di un numero (larghezza, altezza...) da un valore a un altro.

L'avanzamento dipende dal tempo trascorso, non dal numero di passi: così
l'animazione dura sempre uguale, anche se un fotogramma tarda. Parte veloce
e rallenta alla fine, per un movimento più naturale.
"""

import time
import tkinter

INTERVALLO_FOTOGRAMMI = 16  # millisecondi, circa 60 fotogrammi al secondo


class Animazione:
    def __init__(self, widget: tkinter.Misc, durata: float = 0.2):
        self._widget = widget
        self.durata = durata  # secondi
        self._timer = None

    @property
    def in_corso(self) -> bool:
        return self._timer is not None

    def avvia(self, partenza: int, arrivo: int, applica, alla_fine=None) -> None:
        """Chiama applica(valore) a ogni fotogramma; alla fine chiama alla_fine().

        Se c'era già un'animazione in corso, viene sostituita.
        """
        self.ferma()
        self._passo(partenza, arrivo, applica, alla_fine, time.perf_counter())

    def ferma(self) -> None:
        if self._timer is not None:
            self._widget.after_cancel(self._timer)
            self._timer = None

    def _passo(self, partenza, arrivo, applica, alla_fine, inizio) -> None:
        avanzamento = min(1.0, (time.perf_counter() - inizio) / self.durata)
        morbido = 1 - (1 - avanzamento) ** 3  # parte veloce e rallenta alla fine
        applica(round(partenza + (arrivo - partenza) * morbido))
        if avanzamento < 1:
            self._timer = self._widget.after(
                INTERVALLO_FOTOGRAMMI, self._passo, partenza, arrivo, applica, alla_fine, inizio
            )
        else:
            self._timer = None
            if alla_fine is not None:
                alla_fine()
