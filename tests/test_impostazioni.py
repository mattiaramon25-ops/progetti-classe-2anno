"""Test del salvataggio delle preferenze dell'interfaccia."""

import json
import tempfile
import unittest
from pathlib import Path

from gui import impostazioni


class TestImpostazioni(unittest.TestCase):
    def setUp(self):
        cartella = tempfile.TemporaryDirectory()
        self.addCleanup(cartella.cleanup)
        self.percorso = Path(cartella.name) / "impostazioni_gui.json"

    def test_senza_file_usa_i_valori_predefiniti(self):
        self.assertEqual(impostazioni.carica(self.percorso), impostazioni.PREDEFINITE)
        self.assertEqual(impostazioni.PREDEFINITE, {
            "tema": None,  # None = come Windows
            "barra_aperta": True,
            "streaming": True,
            "memoria": False,
        })

    def test_salva_e_ricarica(self):
        valori = {"tema": "dark", "barra_aperta": False, "streaming": False, "memoria": True}
        impostazioni.salva(self.percorso, valori)
        self.assertEqual(impostazioni.carica(self.percorso), valori)

    def test_file_rovinato_usa_i_valori_predefiniti(self):
        self.percorso.write_text("{ non è json", encoding="utf-8")
        self.assertEqual(impostazioni.carica(self.percorso), impostazioni.PREDEFINITE)

    def test_valori_mancanti_o_sbagliati_vengono_sostituiti(self):
        self.percorso.write_text(json.dumps({
            "tema": "viola",        # tema inesistente
            "streaming": "sì",      # dovrebbe essere vero/falso
            "memoria": True,
            "altro": 123,           # chiave sconosciuta
        }), encoding="utf-8")
        self.assertEqual(impostazioni.carica(self.percorso), {
            "tema": None, "barra_aperta": True, "streaming": True, "memoria": True,
        })

    def test_il_file_e_leggibile(self):
        impostazioni.salva(self.percorso, dict(impostazioni.PREDEFINITE))
        testo = self.percorso.read_text(encoding="utf-8")
        self.assertIn('\n  "barra_aperta": true', testo)  # indentato, facile da leggere

    def test_errore_di_scrittura_non_blocca_l_app(self):
        percorso = Path(self.percorso.parent, "cartella_inesistente", "x.json")
        impostazioni.salva(percorso, dict(impostazioni.PREDEFINITE))  # nessuna eccezione


if __name__ == "__main__":
    unittest.main()
