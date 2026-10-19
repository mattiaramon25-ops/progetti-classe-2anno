"""Test della finestra principale (creata nascosta, senza LM Studio)."""

import time
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

    def test_la_chat_scorre_quando_i_messaggi_non_ci_stanno(self):
        self.finestra.attributes("-alpha", 0)  # visibile ma trasparente: misure reali
        self.finestra.deiconify()
        for numero in range(30):
            self.finestra.aggiungi_messaggio("utente", f"messaggio {numero}")
        self.finestra.update()
        tela = self.finestra.chat._parent_canvas
        tela.yview_moveto(0)
        self.finestra.update()
        inizio, fine = tela.yview()
        self.assertEqual(inizio, 0.0)
        self.assertLess(fine, 1.0)  # c'è altro contenuto sotto: si può scorrere

    def test_interruttore_tema_cambia_tra_chiaro_e_scuro(self):
        interruttore = self.finestra.barra.interruttore_tema
        interruttore.select()
        interruttore.toggle()  # da acceso a spento
        self.assertEqual(ctk.get_appearance_mode(), "Light")
        interruttore.toggle()  # da spento ad acceso
        self.assertEqual(ctk.get_appearance_mode(), "Dark")


def aspetta_animazione(finestra: Finestra) -> list[int]:
    """Fa girare la finestra finché l'animazione della barra non finisce.

    Restituisce le larghezze attraversate, per controllare che sia graduale.
    """
    larghezze = []
    inizio = time.monotonic()
    while finestra.barra.in_animazione:
        finestra.update()
        larghezze.append(finestra.barra.cget("width"))
        if time.monotonic() - inizio > 2:
            raise AssertionError("L'animazione non è finita entro 2 secondi")
        time.sleep(0.005)
    return larghezze


class TestBarraRetraibile(unittest.TestCase):
    def setUp(self):
        self.finestra = Finestra()
        self.finestra.withdraw()
        self.addCleanup(chiudi, self.finestra)
        self.addCleanup(ctk.set_appearance_mode, ctk.get_appearance_mode())
        self.barra = self.finestra.barra

    def controlla_aperta(self):
        self.assertTrue(self.barra.aperta)
        self.assertEqual(self.barra.cget("width"), tema.LARGHEZZA_BARRA)
        self.assertEqual(self.barra.contenuto_aperto.winfo_manager(), "pack")
        self.assertEqual(self.barra.contenuto_chiuso.winfo_manager(), "")

    def controlla_chiusa(self):
        self.assertFalse(self.barra.aperta)
        self.assertEqual(self.barra.cget("width"), tema.LARGHEZZA_BARRA_CHIUSA)
        self.assertEqual(self.barra.contenuto_aperto.winfo_manager(), "")
        self.assertEqual(self.barra.contenuto_chiuso.winfo_manager(), "pack")

    def test_all_avvio_e_aperta(self):
        self.controlla_aperta()

    def test_chiudi_e_riapri_senza_animazione(self):
        self.barra.chiudi(animazione=False)
        self.controlla_chiusa()
        self.barra.apri(animazione=False)
        self.controlla_aperta()

    def test_alterna(self):
        self.barra.alterna(animazione=False)
        self.controlla_chiusa()
        self.barra.alterna(animazione=False)
        self.controlla_aperta()

    def test_la_chiusura_animata_passa_per_larghezze_intermedie(self):
        self.barra.chiudi()
        larghezze = aspetta_animazione(self.finestra)
        intermedie = [l for l in larghezze
                      if tema.LARGHEZZA_BARRA_CHIUSA < l < tema.LARGHEZZA_BARRA]
        self.assertGreaterEqual(len(intermedie), 3)
        self.assertEqual(larghezze, sorted(larghezze, reverse=True))  # solo restringimento
        self.controlla_chiusa()

    def test_durante_l_animazione_il_contenuto_e_nascosto(self):
        self.barra.chiudi()
        self.assertTrue(self.barra.in_animazione)
        self.assertEqual(self.barra.contenuto_aperto.winfo_manager(), "")
        self.assertEqual(self.barra.contenuto_chiuso.winfo_manager(), "")
        aspetta_animazione(self.finestra)

    def test_cambiare_idea_a_meta_animazione(self):
        self.barra.chiudi()
        self.finestra.after(60, self.barra.apri)
        aspetta_animazione(self.finestra)  # finisce la chiusura o la riapertura
        aspetta_animazione(self.finestra)
        self.controlla_aperta()

    def test_pulsante_chiudi_e_pulsante_apri(self):
        self.barra.pulsante_chiudi.invoke()
        aspetta_animazione(self.finestra)
        self.controlla_chiusa()
        self.barra.pulsante_apri.invoke()
        aspetta_animazione(self.finestra)
        self.controlla_aperta()

    def test_ctrl_b_alterna_la_barra_anche_scrivendo(self):
        # Tk consegna i tasti solo a finestre visibili: la mostriamo ma trasparente
        self.finestra.attributes("-alpha", 0)
        self.finestra.deiconify()
        casella = self.finestra.scrittura.casella
        casella.insert("1.0", "ciao")
        casella.mark_set("insert", "end")
        casella._textbox.focus_force()
        self.finestra.update()
        casella._textbox.event_generate("<Control-b>", when="now")
        aspetta_animazione(self.finestra)
        self.controlla_chiusa()
        # il tasto non deve spostare il cursore né scrivere nulla nella casella
        self.assertEqual(casella.get("1.0", "end-1c"), "ciao")
        self.assertEqual(casella.index("insert"), "1.4")

    def test_pulsante_tema_della_striscia_resta_sincronizzato(self):
        ctk.set_appearance_mode("light")
        self.barra.interruttore_tema.deselect()
        self.barra.chiudi(animazione=False)
        self.barra.pulsante_tema_icona.invoke()
        self.assertEqual(ctk.get_appearance_mode(), "Dark")
        self.assertEqual(self.barra.interruttore_tema.get(), 1)
        self.barra.interruttore_tema.toggle()
        self.assertEqual(ctk.get_appearance_mode(), "Light")
        self.assertEqual(self.barra.pulsante_tema_icona.cget("text"), "☾")

    def test_le_nuvolette_si_adattano_solo_a_fine_animazione(self):
        """Ricalcolarle a ogni fotogramma renderebbe l'animazione a scatti."""
        self.finestra.attributes("-alpha", 0)  # visibile ma trasparente: misure reali
        self.finestra.deiconify()
        nuvoletta = self.finestra.aggiungi_messaggio("utente", "ciao")
        self.finestra.update()  # la finestra riceve gli eventi solo dopo il primo update
        prima = nuvoletta.larghezza_testo
        self.barra.chiudi()
        self.finestra.chat.event_generate("<Configure>", width=500, when="now")
        self.assertEqual(nuvoletta.larghezza_testo, prima)
        aspetta_animazione(self.finestra)
        self.controlla_nuvoletta_segue_la_chat(nuvoletta)
        self.barra.apri()
        aspetta_animazione(self.finestra)
        self.controlla_nuvoletta_segue_la_chat(nuvoletta)

    def controlla_nuvoletta_segue_la_chat(self, nuvoletta):
        """A fine animazione la nuvoletta segue la larghezza reale della chat."""
        self.finestra.update()
        scala = ctk.ScalingTracker.get_widget_scaling(self.finestra)
        larghezza_chat = int(self.finestra.chat.winfo_width() / scala)
        attesa = int(larghezza_chat * tema.LARGHEZZA_MAX_NUVOLA) - 2 * tema.SPAZIO_M
        self.assertEqual(nuvoletta.larghezza_testo, attesa)

    def test_la_striscia_ha_nuova_chat_e_stato(self):
        self.assertEqual(self.barra.pulsante_nuova_chat_icona.cget("text"), "+")
        self.assertEqual(
            self.barra.pallino_chiuso.cget("text_color"), tema.COLORI["stato_errore"]
        )


if __name__ == "__main__":
    unittest.main()
