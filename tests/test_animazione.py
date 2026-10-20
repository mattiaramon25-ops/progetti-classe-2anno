"""Test dell'animazione basata sul tempo (barra laterale, menu del modello)."""

import time
import tkinter
import unittest

from gui.animazione import Animazione


class TestAnimazione(unittest.TestCase):
    def setUp(self):
        self.radice = tkinter.Tk()
        self.radice.withdraw()
        self.addCleanup(self.radice.destroy)
        self.animazione = Animazione(self.radice, durata=0.15)
        self.valori = []
        self.finita = []

    def aspetta_fine(self):
        inizio = time.monotonic()
        while self.animazione.in_corso:
            self.radice.update()
            if time.monotonic() - inizio > 2:
                raise AssertionError("animazione non finita")
            time.sleep(0.005)

    def test_va_dalla_partenza_all_arrivo_passando_per_valori_intermedi(self):
        self.animazione.avvia(0, 100, self.valori.append, lambda: self.finita.append(True))
        self.assertTrue(self.animazione.in_corso)
        self.aspetta_fine()
        self.assertEqual(self.valori[-1], 100)
        self.assertGreaterEqual(len([v for v in self.valori if 0 < v < 100]), 3)
        self.assertEqual(self.valori, sorted(self.valori))
        self.assertEqual(self.finita, [True])

    def test_dura_circa_quanto_richiesto(self):
        inizio = time.monotonic()
        self.animazione.avvia(0, 100, self.valori.append)
        self.aspetta_fine()
        self.assertLess(time.monotonic() - inizio, 0.4)

    def test_una_nuova_animazione_sostituisce_quella_in_corso(self):
        self.animazione.avvia(0, 100, self.valori.append, lambda: self.finita.append("prima"))
        self.radice.update()
        self.animazione.avvia(50, 0, self.valori.append, lambda: self.finita.append("seconda"))
        self.aspetta_fine()
        self.assertEqual(self.valori[-1], 0)
        self.assertEqual(self.finita, ["seconda"])

    def test_ferma(self):
        self.animazione.avvia(0, 100, self.valori.append, lambda: self.finita.append(True))
        self.animazione.ferma()
        self.assertFalse(self.animazione.in_corso)
        self.radice.after(100)
        self.radice.update()
        self.assertEqual(self.finita, [])


if __name__ == "__main__":
    unittest.main()
