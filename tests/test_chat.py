"""Test della chat collegata a un finto LM Studio (fase 4: senza streaming)."""

import time
import unittest

import customtkinter as ctk

from gui import tema
from gui.componenti import AvvisoErrore, IndicatorePensiero
from gui.finestra import Finestra
from gui.lm_api import ClientLM
from tests.finto_lm import FintoLMStudio
from tests.test_finestra import chiudi


def aspetta(finestra: Finestra, condizione, secondi: float = 3) -> None:
    """Fa girare la finestra finché la condizione non è vera."""
    inizio = time.monotonic()
    while not condizione():
        finestra.update()
        if time.monotonic() - inizio > secondi:
            raise AssertionError("Condizione non raggiunta in tempo")
        time.sleep(0.005)


class TestChat(unittest.TestCase):
    modello_preferito = None

    def setUp(self):
        self.finto = FintoLMStudio()
        self.finto.modelli = ["modello-a", "text-embedding-nomic", "modello-b"]
        self.addCleanup(self.finto.chiudi)
        self.finestra = self.crea_finestra()

    def crea_finestra(self) -> Finestra:
        finestra = Finestra(ClientLM(self.finto.url, timeout=5), self.modello_preferito)
        finestra.withdraw()
        self.addCleanup(chiudi, finestra)
        return finestra

    def avvisi(self) -> list[AvvisoErrore]:
        return [w for w in self.finestra.chat.winfo_children() if isinstance(w, AvvisoErrore)]

    def connetti(self):
        aspetta(self.finestra, lambda: self.finestra.connesso)

    def scrivi(self, testo: str):
        self.finestra.scrittura.casella.insert("1.0", testo)


class TestConnessione(TestChat):
    def test_all_avvio_si_connette_e_mostra_i_modelli_chat(self):
        self.connetti()
        menu = self.finestra.barra.menu_modello
        self.assertEqual(menu.cget("values"), ["modello-a", "modello-b"])
        self.assertEqual(menu.get(), "modello-a")
        self.assertEqual(self.finestra.barra.testo_stato.cget("text"), "Connesso")
        self.assertEqual(self.finestra.barra.pallino.cget("text_color"), tema.COLORI["stato_ok"])
        self.assertEqual(
            self.finestra.barra.pallino_chiuso.cget("text_color"), tema.COLORI["stato_ok"]
        )

    def test_durante_la_connessione_lo_stato_lo_dice(self):
        self.assertEqual(self.finestra.barra.testo_stato.cget("text"), "Connessione...")

    def test_connessione_fallita_mostra_errore_con_riprova(self):
        self.finto.stato_http = 500
        finestra = self.finestra
        aspetta(finestra, lambda: self.avvisi())
        self.assertFalse(finestra.connesso)
        self.assertEqual(finestra.barra.testo_stato.cget("text"), "Non connesso")
        self.assertIn("500", self.avvisi()[0].messaggio)

        self.finto.stato_http = 200
        self.avvisi()[0].pulsante_riprova.invoke()
        self.connetti()
        self.assertEqual(self.avvisi(), [])

    def test_nessun_modello_caricato(self):
        self.finto.modelli = ["text-embedding-nomic"]
        aspetta(self.finestra, lambda: self.avvisi())
        self.assertIn("Nessun modello", self.avvisi()[0].messaggio)
        self.assertFalse(self.finestra.connesso)


class TestModelloPreferito(TestChat):
    modello_preferito = "modello-b"

    def test_seleziona_il_modello_del_env(self):
        self.connetti()
        self.assertEqual(self.finestra.barra.menu_modello.get(), "modello-b")


class TestModelloPreferitoNonInElenco(TestChat):
    modello_preferito = "modello-x"

    def test_lo_aggiunge_in_cima_all_elenco(self):
        """LM Studio può caricare al volo un modello non ancora in memoria."""
        self.connetti()
        menu = self.finestra.barra.menu_modello
        self.assertEqual(menu.cget("values"), ["modello-x", "modello-a", "modello-b"])
        self.assertEqual(menu.get(), "modello-x")


class TestInvio(TestChat):
    def setUp(self):
        super().setUp()
        self.connetti()

    def test_domanda_e_risposta(self):
        self.finto.ritardo = 0.3
        self.scrivi("  Ciao  ")
        self.finestra.invia()

        # subito: la domanda compare, la casella si svuota, il modello "pensa"
        domanda = self.finestra.nuvolette[-1]
        self.assertEqual((domanda.mittente, domanda.testo), ("utente", "Ciao"))
        self.assertEqual(self.finestra.scrittura.casella.get("1.0", "end-1c"), "")
        self.assertTrue(self.finestra.in_attesa)
        self.assertIsInstance(self.finestra.indicatore, IndicatorePensiero)
        self.assertIn("modello-a sta pensando", self.finestra.indicatore.testo)
        self.assertEqual(self.finestra.scrittura.pulsante_invia.cget("state"), "disabled")

        aspetta(self.finestra, lambda: not self.finestra.in_attesa)
        risposta = self.finestra.nuvolette[-1]
        self.assertEqual((risposta.mittente, risposta.testo), ("modello", "Ciao!"))
        self.assertEqual(risposta.etichetta_nome.cget("text"), "modello-a")
        self.assertIsNone(self.finestra.indicatore)
        self.assertEqual(self.finestra.scrittura.pulsante_invia.cget("state"), "normal")

    def test_invia_solo_la_domanda_senza_streaming(self):
        self.scrivi("Ciao")
        self.finestra.invia()
        aspetta(self.finestra, lambda: not self.finestra.in_attesa)
        self.assertEqual(
            self.finto.richieste,
            [{"model": "modello-a", "messages": [{"role": "user", "content": "Ciao"}],
              "stream": False}],
        )

    def test_usa_il_modello_scelto_nel_menu(self):
        self.finestra.barra.menu_modello.set("modello-b")
        self.scrivi("Ciao")
        self.finestra.invia()
        aspetta(self.finestra, lambda: not self.finestra.in_attesa)
        self.assertEqual(self.finto.richieste[0]["model"], "modello-b")
        self.assertEqual(self.finestra.nuvolette[-1].etichetta_nome.cget("text"), "modello-b")

    def test_testo_vuoto_non_viene_inviato(self):
        self.scrivi("   \n  ")
        self.finestra.invia()
        self.assertEqual(self.finestra.nuvolette, [])
        self.assertFalse(self.finestra.in_attesa)

    def test_niente_secondo_invio_mentre_il_modello_risponde(self):
        self.finto.ritardo = 0.3
        self.scrivi("Prima")
        self.finestra.invia()
        self.scrivi("Seconda")
        self.finestra.invia()
        aspetta(self.finestra, lambda: not self.finestra.in_attesa)
        self.assertEqual(len(self.finto.richieste), 1)
        # la seconda domanda resta nella casella, pronta da inviare dopo
        self.assertEqual(self.finestra.scrittura.casella.get("1.0", "end-1c"), "Seconda")

    def test_errore_durante_la_risposta_e_riprova(self):
        self.finto.stato_http = 500
        self.scrivi("Ciao")
        self.finestra.invia()
        aspetta(self.finestra, lambda: self.avvisi())
        self.assertFalse(self.finestra.in_attesa)
        self.assertIsNone(self.finestra.indicatore)

        self.finto.stato_http = 200
        self.avvisi()[0].pulsante_riprova.invoke()
        aspetta(self.finestra, lambda: not self.finestra.in_attesa and not self.avvisi())
        testi = [(n.mittente, n.testo) for n in self.finestra.nuvolette]
        self.assertEqual(testi, [("utente", "Ciao"), ("modello", "Ciao!")])  # niente doppioni

    def test_la_chat_scorre_fino_all_ultimo_messaggio(self):
        self.finestra.attributes("-alpha", 0)  # visibile ma trasparente: misure reali
        self.finestra.deiconify()
        for numero in range(15):
            self.finestra.aggiungi_messaggio("utente", f"messaggio {numero}")
        self.scrivi("Ciao")
        self.finestra.invia()
        aspetta(self.finestra, lambda: not self.finestra.in_attesa)
        self.finestra.update()
        self.assertAlmostEqual(self.finestra.chat._parent_canvas.yview()[1], 1.0)


class TestInvioSenzaConnessione(TestChat):
    def test_avvisa_e_tiene_il_testo(self):
        self.finto.chiudi()
        aspetta(self.finestra, lambda: self.avvisi())
        for avviso in self.avvisi():
            avviso.destroy()
        self.scrivi("Ciao")
        self.finestra.invia()
        self.assertEqual(self.finestra.nuvolette, [])
        self.assertEqual(self.finestra.scrittura.casella.get("1.0", "end-1c"), "Ciao")
        self.assertIn("non sei connesso", self.avvisi()[0].messaggio.lower())


class TestTastiera(TestChat):
    def setUp(self):
        super().setUp()
        self.connetti()
        # Tk consegna i tasti solo a finestre visibili: la mostriamo ma trasparente
        self.finestra.attributes("-alpha", 0)
        self.finestra.deiconify()
        self.casella = self.finestra.scrittura.casella
        self.casella._textbox.focus_force()
        self.finestra.update()

    def premi(self, tasto: str):
        self.casella._textbox.event_generate(tasto, when="now")

    def test_invio_manda_il_messaggio(self):
        self.scrivi("Ciao")
        self.premi("<Return>")
        self.assertEqual(self.finestra.nuvolette[-1].testo, "Ciao")
        self.assertEqual(self.casella.get("1.0", "end-1c"), "")
        aspetta(self.finestra, lambda: not self.finestra.in_attesa)

    def test_shift_invio_va_a_capo(self):
        self.scrivi("riga 1")
        self.casella.mark_set("insert", "end")
        self.premi("<Shift-Return>")
        self.assertEqual(self.finestra.nuvolette, [])
        self.assertEqual(self.casella.get("1.0", "end-1c"), "riga 1\n")


class TestIndicatorePensiero(unittest.TestCase):
    def test_i_puntini_si_animano(self):
        finestra = Finestra()
        finestra.withdraw()
        self.addCleanup(chiudi, finestra)
        indicatore = IndicatorePensiero(finestra.chat, "qwen")
        testi = {indicatore.testo}
        aspetta(finestra, lambda: testi.add(indicatore.testo) or len(testi) >= 3)
        self.assertTrue(all(t.startswith("qwen sta pensando") for t in testi))


if __name__ == "__main__":
    unittest.main()
