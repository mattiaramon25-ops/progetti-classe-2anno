"""Selettore delle versioni dell'applicativo.

Cerca tutte le cartelle "files_lezione_<N>" accanto a questo file e
mostra un menu con gli script .py che contengono. Aggiungendo nuove
lezioni (files_lezione_2, files_lezione_3, ...) compaiono da sole.
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PATTERN_CARTELLA = re.compile(r"^files_lezione_(\d+)$")


def trova_applicativi() -> list[tuple[int, Path]]:
    """Restituisce (numero lezione, percorso script) ordinati per lezione e nome."""
    applicativi = []
    for cartella in ROOT.iterdir():
        trovato = PATTERN_CARTELLA.match(cartella.name)
        if not cartella.is_dir() or not trovato:
            continue
        lezione = int(trovato.group(1))
        for script in cartella.glob("*.py"):
            if not script.name.startswith("_"):
                applicativi.append((lezione, script))
    return sorted(applicativi, key=lambda a: (a[0], a[1].name))


def mostra_menu(applicativi: list[tuple[int, Path]]) -> None:
    print("\n=== Selettore applicativi ===")
    lezione_corrente = None
    for indice, (lezione, script) in enumerate(applicativi, start=1):
        if lezione != lezione_corrente:
            print(f"\n  Lezione {lezione}")
            lezione_corrente = lezione
        print(f"    {indice}) {script.name}")
    print("\n    0) Esci")


def main() -> None:
    while True:
        applicativi = trova_applicativi()
        if not applicativi:
            print("Nessun applicativo trovato nelle cartelle files_lezione_*.")
            return

        mostra_menu(applicativi)
        try:
            scelta = input("\nScegli un numero: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if scelta in {"0", "q", "esci"}:
            return
        if not scelta.isdigit() or not 1 <= int(scelta) <= len(applicativi):
            print("Scelta non valida.")
            continue

        _, script = applicativi[int(scelta) - 1]
        print(f"\n--- Avvio {script.relative_to(ROOT)} ---\n")
        try:
            subprocess.run([sys.executable, str(script)], cwd=ROOT)
        except KeyboardInterrupt:
            pass
        print(f"\n--- Fine {script.name} ---")


if __name__ == "__main__":
    main()
