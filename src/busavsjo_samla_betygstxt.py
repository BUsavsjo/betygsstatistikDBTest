# === busavsjo_samla_betygstxt.py ===
from config_paths import RAW_BETYG_DIR, OUTPUT_DIR, LASAR
from pathlib import Path

def busavsjo_samla_txtfiler(indata_mapp=None, utdata_fil=None):
    """
    Läser in alla .txt-filer från angiven mapp och sparar ihop dem till angiven utfil.
    Om inget anges används standardvägar: RAW_BETYG_DIR och betyg.txt
    """
    if indata_mapp is None:
        indata_mapp = RAW_BETYG_DIR
    if utdata_fil is None:
        utdata_fil = OUTPUT_DIR / "betyg.txt"

    med_antal = 0
    with utdata_fil.open("w", encoding="utf-8") as utfil:
        for filväg in sorted(indata_mapp.iterdir()):
            if filväg.suffix == ".txt" and filväg.name != utdata_fil.name:
                try:
                    innehåll = filväg.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    innehåll = filväg.read_text(encoding="latin-1")

                utfil.write(innehåll.strip() + "\n\n")
                med_antal += 1

    print(f"✔️ Samlade {med_antal} filer till '{utdata_fil}'")

if __name__ == "__main__":
    BASE = Path(__file__).resolve().parent.parent
    lasar = LASAR
    base_raw = BASE / "data" / "raw" / "betyg" / lasar
    base_out = BASE / "data" / "output" / lasar

    busavsjo_samla_txtfiler(
        indata_mapp=base_raw / "ak6",
        utdata_fil=base_out / "betyg_ak6.txt"
    )

    busavsjo_samla_txtfiler(
        indata_mapp=base_raw / "ak9",
        utdata_fil=base_out / "betyg_ak9.txt"
    )
