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


class TestEsecutoreAPezzi(unittest.TestCase):
    """Per lo streaming: il lavoro produce tanti pezzi, consegnati uno alla volta."""

    def setUp(self):
        self.radice = tkinter.Tk()
        self.radice.withdraw()
        self.addCleanup(self.radice.destroy)
        self.esecutore = Esecutore(self.radice)
        self.eventi = []
        self.ferma = threading.Event()

    def esegui(self, lavoro):
        self.esecutore.esegui_a_pezzi(
            lavoro,
            al_pezzo=lambda p: self.eventi.append(("pezzo", p, threading.current_thread())),
            alla_fine=lambda _: self.eventi.append(("fine", None, threading.current_thread())),
            all_errore=lambda e: self.eventi.append(("errore", e, threading.current_thread())),
            ferma=self.ferma,
        )

    def tipi(self):
        return [(tipo, valore) for tipo, valore, _ in self.eventi]

    def test_consegna_i_pezzi_in_ordine_e_poi_la_fine(self):
        def lavoro():
            for pezzo in ["a", "b", "c"]:
                time.sleep(0.02)
                yield pezzo

        self.esegui(lavoro)
        aspetta(self.radice, lambda: self.eventi and self.eventi[-1][0] == "fine")
        self.assertEqual(self.tipi(), [("pezzo", "a"), ("pezzo", "b"), ("pezzo", "c"), ("fine", None)])
        self.assertTrue(all(t is threading.main_thread() for _, _, t in self.eventi))
        self.assertFalse(self.esecutore.occupato)

    def test_ferma_interrompe_e_chiude_il_generatore(self):
        chiuso = threading.Event()

        def lavoro():
            try:
                for numero in range(100):
                    time.sleep(0.02)
                    yield numero
            finally:
                chiuso.set()  # succede quando il generatore viene chiuso

        self.esegui(lavoro)
        aspetta(self.radice, lambda: self.eventi)
        self.ferma.set()
        aspetta(self.radice, lambda: not self.esecutore.occupato)
        self.assertTrue(chiuso.is_set())
        self.assertLess(len(self.eventi), 20)
        self.assertEqual(self.eventi[-1][0], "fine")

    def test_errore_a_meta(self):
        def lavoro():
            yield "a"
            raise ValueError("rotto")

        self.esegui(lavoro)
        aspetta(self.radice, lambda: not self.esecutore.occupato)
        self.assertEqual(self.tipi()[0], ("pezzo", "a"))
        self.assertEqual(self.eventi[-1][0], "errore")
        self.assertEqual(str(self.eventi[-1][1]), "rotto")


if __name__ == "__main__":
    unittest.main()
