"""Test della finestra principale (creata nascosta, senza LM Studio)."""

import unittest

import customtkinter as ctk

from gui import tema
from gui.componenti import Nuvoletta
from gui.finestra import Finestra


def chiudi(finestra: ctk.CTk) -> None:
    """Annulla i timer interni di CustomTkinter e chiude la finestra senza messaggi d'errore."""
    for timer in finestra.tk.call("after", "info"):
        finestra.tk.call("after", "cancel", timer)
    finestra.destroy()


class TestFinestra(unittest.TestCase):
    def setUp(self):
        self.finestra = Finestra()
        self.finestra.withdraw()
        self.addCleanup(chiudi, self.finestra)
        self.addCleanup(ctk.set_appearance_mode, ctk.get_appearance_mode())

    def test_titolo(self):
        self.assertEqual(self.finestra.title(), "LM Chat")

    def test_interruttori_predefiniti_streaming_acceso_memoria_spenta(self):
        self.assertTrue(self.finestra.barra.streaming.get())
        self.assertFalse(self.finestra.barra.memoria.get())

    def test_stato_iniziale_non_connesso(self):
        self.assertEqual(self.finestra.barra.testo_stato.cget("text"), "Non connesso")
        self.assertEqual(
            self.finestra.barra.pallino.cget("text_color"), tema.COLORI["stato_errore"]
        )

    def test_messaggio_utente_a_destra_con_colore_accento(self):
        nuvoletta = self.finestra.aggiungi_messaggio("utente", "Ciao")
        self.assertIsInstance(nuvoletta, Nuvoletta)
        self.assertEqual(nuvoletta.testo, "Ciao")
        self.assertEqual(nuvoletta.pack_info()["anchor"], "e")
        self.assertEqual(nuvoletta.fumetto.cget("fg_color"), tema.COLORI["accento"])
        self.assertIsNone(nuvoletta.etichetta_nome)

    def test_messaggio_modello_a_sinistra_con_nome_del_modello(self):
        nuvoletta = self.finestra.aggiungi_messaggio("modello", "Salve!", nome="qwen")
        self.assertEqual(nuvoletta.pack_info()["anchor"], "w")
        self.assertEqual(nuvoletta.fumetto.cget("fg_color"), tema.COLORI["nuvola_modello"])
        self.assertEqual(nuvoletta.etichetta_nome.cget("text"), "qwen")

    def test_mittente_sconosciuto_da_errore(self):
        with self.assertRaises(ValueError):
            self.finestra.aggiungi_messaggio("altro", "?")

    def test_nuvolette_larghe_al_massimo_il_70_per_cento_della_chat(self):
        nuvoletta = self.finestra.aggiungi_messaggio("utente", "testo lungo " * 50)
        self.finestra.adatta_nuvolette(1000)
        self.assertEqual(nuvoletta.larghezza_testo, 700 - 2 * tema.SPAZIO_M)

    def test_le_nuove_nuvolette_usano_la_larghezza_attuale(self):
        self.finestra.adatta_nuvolette(600)
        nuvoletta = self.finestra.aggiungi_messaggio("modello", "ciao", nome="qwen")
        self.assertEqual(nuvoletta.larghezza_testo, 420 - 2 * tema.SPAZIO_M)

    def test_interruttore_tema_cambia_tra_chiaro_e_scuro(self):
        interruttore = self.finestra.barra.interruttore_tema
        interruttore.select()
        interruttore.toggle()  # da acceso a spento
        self.assertEqual(ctk.get_appearance_mode(), "Light")
        interruttore.toggle()  # da spento ad acceso
        self.assertEqual(ctk.get_appearance_mode(), "Dark")


if __name__ == "__main__":
    unittest.main()
