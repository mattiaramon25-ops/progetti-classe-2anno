"""Test della logica LM Studio usata dall'interfaccia grafica.

Avvio (dalla cartella principale del progetto):
    python -m unittest
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from gui import lm_api
from tests.finto_lm import FintoLMStudio


class TestSoloModelliChat(unittest.TestCase):
    def test_toglie_i_modelli_di_embedding(self):
        nomi = ["qwen/qwen3.5-9b", "text-embedding-nomic-embed-text-v1.5", "gemma", "bge-EMBED"]
        self.assertEqual(lm_api.solo_modelli_chat(nomi), ["qwen/qwen3.5-9b", "gemma"])

    def test_lista_vuota(self):
        self.assertEqual(lm_api.solo_modelli_chat([]), [])


class TestConServer(unittest.TestCase):
    def setUp(self):
        self.finto = FintoLMStudio()
        self.addCleanup(self.finto.chiudi)
        self.lm = lm_api.ClientLM(self.finto.url, timeout=5)


class TestModelli(TestConServer):
    def test_elenca_i_modelli_caricati(self):
        self.assertEqual(self.lm.modelli(), ["modello-a", "modello-b"])

    def test_scegli_modello_usa_quello_preferito(self):
        self.assertEqual(self.lm.scegli_modello("llama"), "llama")

    def test_scegli_modello_senza_preferito_usa_il_primo_caricato(self):
        self.assertEqual(self.lm.scegli_modello(None), "modello-a")

    def test_scegli_modello_senza_modelli_caricati_da_errore(self):
        self.finto.modelli = []
        with self.assertRaisesRegex(lm_api.ErroreLM, "Nessun modello"):
            self.lm.scegli_modello(None)


class TestChiedi(TestConServer):
    messaggi = [{"role": "user", "content": "Ciao"}]

    def test_restituisce_la_risposta_senza_spazi_ai_lati(self):
        self.assertEqual(self.lm.chiedi("modello-a", self.messaggi), "Ciao!")

    def test_invia_modello_messaggi_e_stream_disattivato(self):
        self.lm.chiedi("modello-a", self.messaggi)
        self.assertEqual(
            self.finto.richieste,
            [{"model": "modello-a", "messages": self.messaggi, "stream": False}],
        )


class TestChiediStream(TestConServer):
    messaggi = [{"role": "user", "content": "Ciao"}]

    def test_restituisce_i_pezzi_in_ordine_fino_a_done(self):
        self.assertEqual(
            list(self.lm.chiedi_stream("modello-a", self.messaggi)), ["Ci", "ao", "!"]
        )

    def test_invia_modello_messaggi_e_stream_attivo(self):
        list(self.lm.chiedi_stream("modello-a", self.messaggi))
        self.assertEqual(
            self.finto.richieste,
            [{"model": "modello-a", "messages": self.messaggi, "stream": True}],
        )

    def test_si_puo_fermare_a_meta(self):
        """Il pulsante Stop della GUI interrompe il ciclo: non deve dare errori."""
        stream = self.lm.chiedi_stream("modello-a", self.messaggi)
        self.assertEqual(next(stream), "Ci")
        stream.close()

    def test_riga_non_json_da_errore_comprensibile(self):
        self.finto.corpo_sse = lambda: b"data: {non e' json\n\n"
        with self.assertRaisesRegex(lm_api.ErroreLM, "Risposta non valida"):
            list(self.lm.chiedi_stream("modello-a", self.messaggi))


class TestErrori(TestConServer):
    def test_server_spento_da_errore_comprensibile(self):
        self.finto.chiudi()
        with self.assertRaisesRegex(lm_api.ErroreLM, "Impossibile contattare LM Studio"):
            self.lm.modelli()

    def test_errore_http_riporta_il_codice(self):
        self.finto.stato_http = 500
        with self.assertRaisesRegex(lm_api.ErroreLM, "500"):
            self.lm.chiedi("modello-a", [])

    def test_errore_http_anche_in_streaming(self):
        self.finto.stato_http = 500
        with self.assertRaisesRegex(lm_api.ErroreLM, "500"):
            list(self.lm.chiedi_stream("modello-a", []))

    def test_risposta_senza_testo_da_errore_comprensibile(self):
        self.finto.risposta = None
        with self.assertRaisesRegex(lm_api.ErroreLM, "Risposta non valida"):
            self.lm.chiedi("modello-a", [])


class TestLeggiEnv(unittest.TestCase):
    def scrivi_env(self, testo: str) -> Path:
        cartella = tempfile.TemporaryDirectory()
        self.addCleanup(cartella.cleanup)
        percorso = Path(cartella.name) / ".env"
        percorso.write_text(testo, encoding="utf-8")
        return percorso

    def test_legge_coppie_chiave_valore(self):
        percorso = self.scrivi_env("LM_BASE_URL=http://pc:1234\nLM_MODEL=qwen\n")
        self.assertEqual(
            lm_api.leggi_env(percorso),
            {"LM_BASE_URL": "http://pc:1234", "LM_MODEL": "qwen"},
        )

    def test_ignora_commenti_righe_vuote_e_righe_senza_uguale(self):
        percorso = self.scrivi_env("# commento\n\nriga_strana\nLM_MODEL=qwen\n")
        self.assertEqual(lm_api.leggi_env(percorso), {"LM_MODEL": "qwen"})

    def test_toglie_spazi_e_virgolette(self):
        percorso = self.scrivi_env(" LM_MODEL = \"qwen\" \nLM_BASE_URL='http://pc'\n")
        self.assertEqual(
            lm_api.leggi_env(percorso),
            {"LM_MODEL": "qwen", "LM_BASE_URL": "http://pc"},
        )

    def test_file_mancante_restituisce_dizionario_vuoto(self):
        self.assertEqual(lm_api.leggi_env(Path("non_esiste/.env")), {})


@mock.patch.dict(os.environ, {}, clear=True)
class TestConfigurazione(unittest.TestCase):
    def scrivi_env(self, testo: str) -> Path:
        cartella = tempfile.TemporaryDirectory()
        self.addCleanup(cartella.cleanup)
        percorso = Path(cartella.name) / ".env"
        percorso.write_text(testo, encoding="utf-8")
        return percorso

    def test_senza_env_usa_i_valori_predefiniti(self):
        self.assertEqual(
            lm_api.configurazione(Path("non_esiste/.env")),
            ("http://localhost:1234", None),
        )

    def test_usa_i_valori_del_file_env(self):
        percorso = self.scrivi_env("LM_BASE_URL=http://pc:5000\nLM_MODEL=qwen\n")
        self.assertEqual(lm_api.configurazione(percorso), ("http://pc:5000", "qwen"))

    def test_le_variabili_di_ambiente_vincono_sul_file(self):
        percorso = self.scrivi_env("LM_BASE_URL=http://pc:5000\nLM_MODEL=qwen\n")
        with mock.patch.dict(os.environ, {"LM_MODEL": "llama"}):
            self.assertEqual(lm_api.configurazione(percorso), ("http://pc:5000", "llama"))

    def test_toglie_la_barra_finale_dall_indirizzo(self):
        percorso = self.scrivi_env("LM_BASE_URL=http://pc:5000/\n")
        self.assertEqual(lm_api.configurazione(percorso), ("http://pc:5000", None))

    def test_modello_vuoto_vale_come_non_impostato(self):
        percorso = self.scrivi_env("LM_MODEL=\n")
        self.assertEqual(lm_api.configurazione(percorso), ("http://localhost:1234", None))


if __name__ == "__main__":
    unittest.main()
