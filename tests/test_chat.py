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
    """Streaming spento: la risposta arriva tutta insieme (come client1)."""

    def setUp(self):
        super().setUp()
        self.connetti()
        self.finestra.barra.streaming.set(False)

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
        self.assertEqual(self.finestra.scrittura.pulsante_invia.cget("text"), "■")

        aspetta(self.finestra, lambda: not self.finestra.in_attesa)
        risposta = self.finestra.nuvolette[-1]
        self.assertEqual((risposta.mittente, risposta.testo), ("modello", "Ciao!"))
        self.assertEqual(risposta.etichetta_nome.cget("text"), "modello-a")
        self.assertIsNone(self.finestra.indicatore)
        self.assertEqual(self.finestra.scrittura.pulsante_invia.cget("text"), "➤")

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


class TestStreaming(TestChat):
    """Streaming acceso: il testo compare pezzo per pezzo (come client2)."""

    def setUp(self):
        super().setUp()
        self.connetti()
        self.assertTrue(self.finestra.barra.streaming.get())  # acceso di default
        self.finto.risposta = "RISPOSTA SENZA STREAMING"  # se compare, lo streaming non è usato

    def invia(self, testo="Ciao"):
        self.scrivi(testo)
        self.finestra.invia()

    def risposta(self):
        nuvolette = [n for n in self.finestra.nuvolette if n.mittente == "modello"]
        return nuvolette[-1] if nuvolette else None

    def test_il_testo_compare_pezzo_per_pezzo(self):
        self.finto.pezzi = ["Ci", "ao", " a", " tutti"]
        self.finto.ritardo_pezzi = 0.15
        self.invia()
        testi_visti = set()

        def guarda():
            if self.risposta() is not None:
                testi_visti.add(self.risposta().testo)
            return not self.finestra.in_attesa

        aspetta(self.finestra, guarda)
        self.assertEqual(self.risposta().testo, "Ciao a tutti")
        self.assertGreaterEqual(len(testi_visti), 3)  # visti anche testi parziali
        self.assertTrue(self.finto.richieste[0]["stream"])

    def test_al_primo_pezzo_la_nuvoletta_prende_il_posto_dell_indicatore(self):
        self.finto.pezzi = ["Ci", "ao"]
        self.finto.ritardo_pezzi = 0.3
        self.invia()
        self.assertIsNotNone(self.finestra.indicatore)
        aspetta(self.finestra, lambda: self.risposta() is not None)
        self.assertIsNone(self.finestra.indicatore)
        self.assertEqual(self.risposta().etichetta_nome.cget("text"), "modello-a")
        aspetta(self.finestra, lambda: not self.finestra.in_attesa)

    def test_cursore_mentre_scrive_e_non_alla_fine(self):
        self.finto.pezzi = ["Ci", "ao"]
        self.finto.ritardo_pezzi = 0.3
        self.invia()
        aspetta(self.finestra, lambda: self.risposta() is not None)
        self.assertTrue(self.risposta().etichetta.cget("text").endswith("▍"))
        aspetta(self.finestra, lambda: not self.finestra.in_attesa)
        self.assertEqual(self.risposta().etichetta.cget("text"), "Ciao")

    def test_spazi_e_righe_vuote_ai_lati_vengono_tolti(self):
        self.finto.pezzi = ["\n\n", "  Ciao", "!  \n"]
        self.invia()
        aspetta(self.finestra, lambda: not self.finestra.in_attesa)
        self.assertEqual(self.risposta().testo, "Ciao!")

    def test_errore_a_meta_lascia_il_testo_ricevuto_e_mostra_l_avviso(self):
        self.finto.corpo_sse = lambda: (
            b'data: {"choices": [{"delta": {"content": "Ci"}}]}\n\n'
            b"data: {rotto\n\n"
        )
        self.invia()
        aspetta(self.finestra, lambda: self.avvisi())
        self.assertEqual(self.risposta().etichetta.cget("text"), "Ci")  # senza cursore
        self.assertFalse(self.finestra.in_attesa)
        self.assertIn("Risposta non valida", self.avvisi()[0].messaggio)


class TestStop(TestChat):
    def setUp(self):
        super().setUp()
        self.connetti()
        self.pulsante = self.finestra.scrittura.pulsante_invia

    def risposte(self):
        return [n for n in self.finestra.nuvolette if n.mittente == "modello"]

    def test_stop_durante_lo_streaming_tiene_il_testo_ricevuto(self):
        self.finto.pezzi = [f"parola{n} " for n in range(30)]
        self.finto.ritardo_pezzi = 0.05
        self.scrivi("Ciao")
        self.finestra.invia()
        aspetta(self.finestra, lambda: self.risposte())
        self.pulsante.invoke()  # ■ Stop

        self.assertFalse(self.finestra.in_attesa)
        self.assertEqual(self.pulsante.cget("text"), "➤")
        testo = self.risposte()[0].testo
        self.assertFalse(self.risposte()[0].etichetta.cget("text").endswith("▍"))
        self.assertTrue(self.finestra.nota_interrotta.winfo_exists())
        # i pezzi che arrivano dopo lo Stop vengono ignorati
        attesa_fino = time.monotonic() + 0.5
        aspetta(self.finestra, lambda: time.monotonic() > attesa_fino)
        self.assertEqual(self.risposte()[0].testo, testo)

    def test_stop_prima_della_risposta_senza_streaming(self):
        self.finestra.barra.streaming.set(False)
        self.finto.ritardo = 0.5
        self.scrivi("Ciao")
        self.finestra.invia()
        self.pulsante.invoke()
        self.assertFalse(self.finestra.in_attesa)
        self.assertIsNone(self.finestra.indicatore)
        attesa_fino = time.monotonic() + 0.8
        aspetta(self.finestra, lambda: time.monotonic() > attesa_fino)
        self.assertEqual(self.risposte(), [])  # la risposta arrivata dopo è ignorata

    def test_dopo_lo_stop_si_puo_chiedere_di_nuovo(self):
        self.finto.pezzi = [f"vecchia{n} " for n in range(20)]
        self.finto.ritardo_pezzi = 0.05
        self.scrivi("Prima")
        self.finestra.invia()
        aspetta(self.finestra, lambda: self.risposte())
        self.pulsante.invoke()

        self.finto.pezzi = ["nuova"]
        self.finto.ritardo_pezzi = 0
        self.scrivi("Seconda")
        self.finestra.invia()
        aspetta(self.finestra, lambda: not self.finestra.in_attesa)
        attesa_fino = time.monotonic() + 0.3
        aspetta(self.finestra, lambda: time.monotonic() > attesa_fino)
        self.assertEqual(self.risposte()[-1].testo, "nuova")  # niente pezzi della vecchia


def utente(testo: str) -> dict:
    return {"role": "user", "content": testo}


def assistente(testo: str) -> dict:
    return {"role": "assistant", "content": testo}


class TestMemoria(TestChat):
    """Interruttore Memoria: il modello ricorda la conversazione (come client3)."""

    def setUp(self):
        super().setUp()
        self.connetti()
        self.finestra.barra.streaming.set(False)

    def chiedi(self, testo: str, risposta: str = "Ciao!"):
        self.finto.risposta = risposta
        self.scrivi(testo)
        self.finestra.invia()
        aspetta(self.finestra, lambda: not self.finestra.in_attesa)

    def messaggi_inviati(self, indice: int = -1) -> list[dict]:
        return self.finto.richieste[indice]["messages"]

    def test_spenta_ogni_domanda_e_indipendente(self):
        self.assertFalse(self.finestra.barra.memoria.get())  # spenta di default
        self.chiedi("Mi chiamo Ada", "Piacere!")
        self.chiedi("Come mi chiamo?")
        self.assertEqual(self.messaggi_inviati(), [utente("Come mi chiamo?")])

    def test_accesa_invia_tutta_la_conversazione(self):
        self.finestra.barra.memoria.set(True)
        self.chiedi("Mi chiamo Ada", "Piacere!")
        self.chiedi("Come mi chiamo?", "Ada")
        self.chiedi("E tu?")
        self.assertEqual(self.messaggi_inviati(), [
            utente("Mi chiamo Ada"), assistente("Piacere!"),
            utente("Come mi chiamo?"), assistente("Ada"),
            utente("E tu?"),
        ])

    def test_accesa_a_meta_ricorda_quello_che_si_vede_nella_chat(self):
        self.chiedi("Mi chiamo Ada", "Piacere!")
        self.finestra.barra.memoria.set(True)
        self.chiedi("Come mi chiamo?")
        self.assertEqual(self.messaggi_inviati(), [
            utente("Mi chiamo Ada"), assistente("Piacere!"), utente("Come mi chiamo?"),
        ])

    def test_le_domande_fallite_non_entrano_in_memoria(self):
        self.finestra.barra.memoria.set(True)
        self.finto.stato_http = 500
        self.chiedi("Domanda fallita")
        self.finto.stato_http = 200
        self.chiedi("Seconda")
        self.assertEqual(self.messaggi_inviati(), [utente("Seconda")])

    def test_le_risposte_interrotte_non_entrano_in_memoria(self):
        self.finestra.barra.memoria.set(True)
        self.finto.ritardo = 0.3
        self.scrivi("Interrotta")
        self.finestra.invia()
        self.finestra.ferma()
        self.finto.ritardo = 0
        self.chiedi("Seconda")
        self.assertEqual(self.messaggi_inviati(), [utente("Seconda")])

    def test_riprova_dopo_un_errore_entra_in_memoria(self):
        self.finestra.barra.memoria.set(True)
        self.finto.stato_http = 500
        self.chiedi("Mi chiamo Ada")
        self.finto.stato_http = 200
        self.finto.risposta = "Piacere!"
        self.avvisi()[0].pulsante_riprova.invoke()
        aspetta(self.finestra, lambda: not self.finestra.in_attesa)
        self.chiedi("Come mi chiamo?")
        self.assertEqual(self.messaggi_inviati(), [
            utente("Mi chiamo Ada"), assistente("Piacere!"), utente("Come mi chiamo?"),
        ])

    def test_con_lo_streaming_ricorda_la_risposta_completa(self):
        self.finestra.barra.streaming.set(True)
        self.finestra.barra.memoria.set(True)
        self.finto.pezzi = ["\n", "Pia", "cere", "!", " \n"]
        self.scrivi("Mi chiamo Ada")
        self.finestra.invia()
        aspetta(self.finestra, lambda: not self.finestra.in_attesa)
        self.chiedi("Come mi chiamo?")
        self.assertEqual(self.messaggi_inviati(), [
            utente("Mi chiamo Ada"), assistente("Piacere!"), utente("Come mi chiamo?"),
        ])


class TestNuovaChat(TestChat):
    def setUp(self):
        super().setUp()
        self.connetti()
        self.finestra.barra.streaming.set(False)
        self.finestra.barra.memoria.set(True)

    def chiedi(self, testo: str):
        self.scrivi(testo)
        self.finestra.invia()
        aspetta(self.finestra, lambda: not self.finestra.in_attesa)

    def test_svuota_la_chat_e_la_memoria(self):
        self.chiedi("Mi chiamo Ada")
        self.finestra.mostra_errore("errore di prova", al_riprova=lambda: None)
        self.finestra.barra.pulsante_nuova_chat.invoke()
        self.finestra.update()
        self.assertEqual(self.finestra.nuvolette, [])
        self.assertEqual(self.finestra.chat.winfo_children(), [])
        self.chiedi("Come mi chiamo?")
        self.assertEqual(self.finto.richieste[-1]["messages"], [utente("Come mi chiamo?")])

    def test_il_pulsante_della_striscia_fa_lo_stesso(self):
        self.chiedi("Ciao")
        self.finestra.barra.chiudi(animazione=False)
        self.finestra.barra.pulsante_nuova_chat_icona.invoke()
        self.assertEqual(self.finestra.nuvolette, [])

    def test_durante_una_risposta_la_ferma_senza_lasciare_tracce(self):
        self.finto.ritardo = 0.4
        self.scrivi("Ciao")
        self.finestra.invia()
        self.finestra.barra.pulsante_nuova_chat.invoke()
        self.assertFalse(self.finestra.in_attesa)
        attesa_fino = time.monotonic() + 0.7
        aspetta(self.finestra, lambda: time.monotonic() > attesa_fino)
        self.finestra.update()
        self.assertEqual(self.finestra.chat.winfo_children(), [])  # né risposta né nota

    def test_il_testo_che_si_sta_scrivendo_resta(self):
        self.chiedi("Ciao")
        self.scrivi("bozza")
        self.finestra.nuova_chat()
        self.assertEqual(self.finestra.scrittura.casella.get("1.0", "end-1c"), "bozza")


class TestInvioSenzaConnessione(TestChat):
    def test_avvisa_e_tiene_il_testo(self):
        self.finto.chiudi()
        # Windows impiega circa 2 secondi a rifiutare una porta chiusa: margine ampio
        aspetta(self.finestra, lambda: self.avvisi(), secondi=6)
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

    def test_esc_ferma_la_risposta(self):
        self.finto.ritardo = 0.5
        self.scrivi("Ciao")
        self.premi("<Return>")
        self.assertTrue(self.finestra.in_attesa)
        self.premi("<Escape>")
        self.assertFalse(self.finestra.in_attesa)

    def test_ctrl_n_nuova_chat(self):
        self.finestra.aggiungi_messaggio("utente", "vecchio")
        self.premi("<Control-n>")
        self.assertEqual(self.finestra.nuvolette, [])
        self.assertEqual(self.casella.get("1.0", "end-1c"), "")  # niente caratteri inseriti

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
