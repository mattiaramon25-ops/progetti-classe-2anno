"""Test del menu a tendina animato per scegliere il modello."""

import time
import unittest

from gui.componenti import MenuModello
from gui.finestra import Finestra
from tests.test_finestra import chiudi


class TestMenuModello(unittest.TestCase):
    def setUp(self):
        self.finestra = Finestra()
        self.finestra.withdraw()
        self.addCleanup(chiudi, self.finestra)
        self.menu = self.finestra.barra.menu_modello
        self.assertIsInstance(self.menu, MenuModello)
        self.scelte = []
        self.menu.al_cambio = self.scelte.append

    def aspetta_animazione(self) -> list[int]:
        altezze = []
        inizio = time.monotonic()
        while self.menu.in_animazione:
            self.finestra.update()
            altezze.append(self.menu.lista.cget("height"))
            if time.monotonic() - inizio > 2:
                raise AssertionError("animazione non finita")
            time.sleep(0.005)
        return altezze

    def test_valori_iniziali(self):
        self.assertEqual(self.menu.valori, ["Nessun modello"])
        self.assertEqual(self.menu.get(), "Nessun modello")

    def test_imposta_valori_e_scelta(self):
        self.menu.imposta_valori(["a", "b", "c"])
        self.assertEqual(self.menu.valori, ["a", "b", "c"])
        self.assertEqual(self.menu.get(), "a")  # il valore precedente non c'è più
        self.menu.set("b")
        self.assertEqual(self.menu.get(), "b")
        self.assertEqual(self.menu.etichetta_scelta.cget("text"), "b")

    def test_imposta_valori_tiene_la_scelta_se_c_e_ancora(self):
        self.menu.imposta_valori(["a", "b"])
        self.menu.set("b")
        self.menu.imposta_valori(["b", "c"])
        self.assertEqual(self.menu.get(), "b")

    def test_all_inizio_e_chiuso(self):
        self.assertFalse(self.menu.aperto)
        self.assertEqual(self.menu.lista.winfo_manager(), "")
        self.assertEqual(self.menu.freccia.cget("text"), "▾")

    def test_si_apre_con_un_animazione(self):
        self.menu.imposta_valori(["a", "b", "c"])
        self.menu.alterna()  # come un clic sull'intestazione
        self.assertTrue(self.menu.aperto)
        self.assertEqual(self.menu.freccia.cget("text"), "▴")
        altezze = self.aspetta_animazione()
        finale = self.menu.altezza_lista_aperta()
        self.assertGreaterEqual(len([a for a in altezze if 1 < a < finale]), 3)
        self.assertEqual(self.menu.lista.cget("height"), finale)
        self.assertEqual(self.menu.lista.winfo_manager(), "pack")
        self.assertEqual(len(self.menu.pulsanti_voce), 3)

    def test_scegliere_una_voce_la_seleziona_e_chiude(self):
        self.menu.imposta_valori(["a", "b", "c"])
        self.menu.apri()
        self.aspetta_animazione()
        self.menu.pulsanti_voce[2].invoke()
        self.assertEqual(self.menu.get(), "c")
        self.assertEqual(self.scelte, ["c"])
        self.assertFalse(self.menu.aperto)
        self.aspetta_animazione()
        self.assertEqual(self.menu.lista.winfo_manager(), "")
        self.assertEqual(self.menu.freccia.cget("text"), "▾")

    def test_cliccare_di_nuovo_l_intestazione_chiude(self):
        self.menu.apri()
        self.aspetta_animazione()
        self.menu.alterna()  # come un clic sull'intestazione
        self.aspetta_animazione()
        self.assertEqual(self.menu.lista.winfo_manager(), "")

    def test_con_molti_modelli_l_elenco_non_supera_quattro_voci(self):
        self.menu.imposta_valori(["a", "b", "c"])
        tre = self.menu.altezza_lista_aperta()
        self.menu.imposta_valori([f"modello-{n}" for n in range(4)])
        quattro = self.menu.altezza_lista_aperta()
        self.menu.imposta_valori([f"modello-{n}" for n in range(9)])
        self.assertGreater(quattro, tre)
        self.assertEqual(self.menu.altezza_lista_aperta(), quattro)
        self.assertEqual(len(self.menu.pulsanti_voce), 9)  # le altre si raggiungono scorrendo

    def test_con_la_finestra_al_minimo_e_il_menu_aperto_tutto_resta_visibile(self):
        self.finestra.attributes("-alpha", 0)  # visibile ma trasparente: misure reali
        self.finestra.deiconify()
        larghezza, altezza = Finestra.LARGHEZZA_MINIMA, Finestra.ALTEZZA_MINIMA
        self.finestra.geometry(f"{larghezza}x{altezza}")
        self.menu.imposta_valori([f"modello-{n}" for n in range(9)])
        self.menu.apri(animazione=False)
        self.finestra.update()
        barra = self.finestra.barra
        fondo_barra = barra.winfo_rooty() + barra.winfo_height()
        for elemento in (barra.pulsante_nuova_chat, barra.testo_stato, barra.interruttore_tema):
            with self.subTest(elemento=elemento):
                self.assertTrue(elemento.winfo_ismapped())
                self.assertLessEqual(elemento.winfo_rooty() + elemento.winfo_height(), fondo_barra)


if __name__ == "__main__":
    unittest.main()
