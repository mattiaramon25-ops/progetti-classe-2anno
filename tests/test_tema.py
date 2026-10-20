"""Test dei colori dell'interfaccia: formato e contrasti leggibili."""

import re
import unittest

import customtkinter as ctk

from gui import tema

MINIMO_LEGGIBILE = 4.5  # rapporto di contrasto minimo WCAG per il testo
MINIMO_GRAFICA = 3.0  # minimo WCAG per elementi grafici (interruttori, icone)


def luminanza(colore: str) -> float:
    """Luminanza relativa di un colore "#RRGGBB" secondo la formula WCAG."""
    canali = [int(colore[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canali]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrasto(colore1: str, colore2: str) -> float:
    chiaro, scuro = sorted([luminanza(colore1), luminanza(colore2)], reverse=True)
    return (chiaro + 0.05) / (scuro + 0.05)


class TestColori(unittest.TestCase):
    def test_ogni_colore_ha_versione_chiara_e_scura_in_formato_esadecimale(self):
        for nome, coppia in tema.COLORI.items():
            with self.subTest(colore=nome):
                self.assertEqual(len(coppia), 2)
                for valore in coppia:
                    self.assertRegex(valore, re.compile(r"^#[0-9A-Fa-f]{6}$"))

    def test_testi_leggibili_su_ogni_sfondo_in_entrambi_i_temi(self):
        coppie = [
            ("testo", "sfondo"),
            ("testo", "pannello"),
            ("testo", "barra_laterale"),
            ("testo", "nuvola_modello"),
            ("testo_leggero", "sfondo"),
            ("testo_leggero", "pannello"),
            ("testo_leggero", "barra_laterale"),
            ("testo_leggero", "nuvola_modello"),
            ("testo_su_accento", "accento"),
            ("testo_su_accento", "accento_hover"),
            ("accento_testo", "sfondo"),
            ("accento_testo", "barra_laterale"),
            ("errore", "sfondo"),
            ("errore", "pannello"),
            ("testo", "controllo"),
        ]
        self.controlla_contrasti(coppie, MINIMO_LEGGIBILE)

    def test_interruttori_visibili_sulla_barra_laterale_in_entrambi_i_temi(self):
        coppie = [
            ("interruttore_spento", "barra_laterale"),
            ("interruttore_acceso", "barra_laterale"),
            ("pallino_interruttore", "interruttore_spento"),
            ("pallino_interruttore", "interruttore_acceso"),
        ]
        self.controlla_contrasti(coppie, MINIMO_GRAFICA)

    def controlla_contrasti(self, coppie: list[tuple[str, str]], minimo: float) -> None:
        for primo_piano, sfondo in coppie:
            for indice, nome_tema in enumerate(["chiaro", "scuro"]):
                with self.subTest(primo_piano=primo_piano, sfondo=sfondo, tema=nome_tema):
                    rapporto = contrasto(
                        tema.COLORI[primo_piano][indice], tema.COLORI[sfondo][indice]
                    )
                    self.assertGreaterEqual(rapporto, minimo)


class TestMisure(unittest.TestCase):
    def test_spaziature_multiple_di_8(self):
        for nome in ["SPAZIO_S", "SPAZIO_M", "SPAZIO_L", "SPAZIO_XL"]:
            with self.subTest(misura=nome):
                self.assertEqual(getattr(tema, nome) % 8, 0)

    def test_raggi_degli_angoli_come_da_piano(self):
        self.assertEqual(tema.RAGGIO_NUVOLA, 24)
        self.assertEqual(tema.RAGGIO_PANNELLO, 16)
        self.assertEqual(tema.RAGGIO_CONTROLLO, 12)


class TestFont(unittest.TestCase):
    def test_lo_stesso_font_viene_creato_una_volta_sola_e_poi_riusato(self):
        finestra = ctk.CTk()
        finestra.withdraw()
        self.addCleanup(finestra.destroy)
        self.assertIs(tema.font(14), tema.font(14))
        self.assertIs(tema.font(13, grassetto=True), tema.font(13, grassetto=True))
        self.assertIsNot(tema.font(14), tema.font(14, grassetto=True))


if __name__ == "__main__":
    unittest.main()
