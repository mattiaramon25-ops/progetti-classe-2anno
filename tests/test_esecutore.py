"""Test dell'esecutore: lavoro lento in un thread, risultato nel thread della grafica."""

import threading
import time
import tkinter
import unittest

from gui.esecutore import Esecutore


def aspetta(radice: tkinter.Misc, condizione, secondi: float = 3) -> None:
    """Fa girare la grafica finché la condizione non è vera."""
    inizio = time.monotonic()
    while not condizione():
        radice.update()
        if time.monotonic() - inizio > secondi:
            raise AssertionError("Condizione non raggiunta in tempo")
        time.sleep(0.005)


class TestEsecutore(unittest.TestCase):
    def setUp(self):
        self.radice = tkinter.Tk()
        self.radice.withdraw()
        self.addCleanup(self.radice.destroy)
        self.esecutore = Esecutore(self.radice)
        self.risultati = []

    def test_consegna_il_risultato_nel_thread_della_grafica(self):
        thread_lavoro = []

        def lavoro():
            thread_lavoro.append(threading.current_thread())
            return 42

        self.esecutore.esegui(
            lavoro,
            al_successo=lambda r: self.risultati.append((r, threading.current_thread())),
            all_errore=self.fail,
        )
        aspetta(self.radice, lambda: self.risultati)
        risultato, thread_consegna = self.risultati[0]
        self.assertEqual(risultato, 42)
        self.assertIsNot(thread_lavoro[0], threading.main_thread())
        self.assertIs(thread_consegna, threading.main_thread())

    def test_la_grafica_non_si_blocca_durante_il_lavoro(self):
        avviato = time.monotonic()
        self.esecutore.esegui(lambda: time.sleep(0.5), self.risultati.append, self.fail)
        self.assertLess(time.monotonic() - avviato, 0.1)
        self.assertTrue(self.esecutore.occupato)
        aspetta(self.radice, lambda: self.risultati)
        self.assertFalse(self.esecutore.occupato)

    def test_consegna_le_eccezioni_a_all_errore(self):
        def lavoro():
            raise ValueError("rotto")

        self.esecutore.esegui(lavoro, al_successo=self.fail, all_errore=self.risultati.append)
        aspetta(self.radice, lambda: self.risultati)
        self.assertIsInstance(self.risultati[0], ValueError)
        self.assertEqual(str(self.risultati[0]), "rotto")

    def test_piu_lavori_insieme(self):
        for numero in range(3):
            self.esecutore.esegui(lambda n=numero: n, self.risultati.append, self.fail)
        aspetta(self.radice, lambda: len(self.risultati) == 3)
        self.assertEqual(sorted(self.risultati), [0, 1, 2])


if __name__ == "__main__":
    unittest.main()
