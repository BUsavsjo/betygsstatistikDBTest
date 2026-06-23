# === busavsjo_exportera_betyg_excel.py ===
import openpyxl
from config_paths import OUTPUT_DIR, LASAR
from pathlib import Path
import re

# Två varianter av kolumnrubriker
HEADERS_AK6 = [
    "System", "Datum", "Version", "PersonNr", "Skolenhetskod", "Klass", "Förnamn", "Efternamn",
    "BI", "En", "Hkk", "idh", "Ma", "m1(språk)", "M1(betyg)", "M2(språk)", "M2(betyg)",
    "ModM_anm", "Modmalbe", "mu", "No", "So", "Sv", "Sva", "Tk", "Ovr"
]

HEADERS_AK9 = [
    "System", "Datum", "Version", "PersonNr", "Skolenhetskod", "Klass", "Förnamn", "Efternamn",
    "BI", "En", "Hkk", "idh", "Ma", "m1(språk)", "M1(betyg)", "M2(språk)", "M2(betyg)",
    "ModM_anm", "Modmalbe", "mu", "Bi", "Fy", "Ke", "Ge", "Hi", "Re", "Sh", "SI",
    "Sv", "Sva", "Tn", "Tk", "Ovr"
]

KLASS_MAX_LENGTH = 25
HISTORISK_SAKNAD_KLASS = "9999999999"


def hamta_slutar(lasar: str = LASAR) -> int | None:
    """Returnerar slutaret i ett lasar, t.ex. 2026 for 2025-2026."""
    years = re.findall(r"\d{4}", str(lasar))
    if not years:
        return None
    return int(years[-1])


def validera_klass(klass: str, struktur: str | None = None, lasar: str = LASAR) -> list[str]:
    klass = str(klass or "").strip()
    struktur_norm = (struktur or "").upper()
    slut_ar = hamta_slutar(lasar)
    varningar = []

    if len(klass) > KLASS_MAX_LENGTH:
        varningar.append(
            f"Klass '{klass}' ar {len(klass)} tecken. Max tillaten langd ar {KLASS_MAX_LENGTH}."
        )

    if (
        klass == HISTORISK_SAKNAD_KLASS
        and struktur_norm == "AK6"
        and slut_ar is not None
        and slut_ar >= 2026
    ):
        varningar.append(
            "Klass 9999999999 ar ett historiskt AK6-varde for saknad uppgift och ar inte dokumenterat for 2026."
        )

    return varningar


def formatera_personnummer(pnr):
    pnr = pnr.replace("-", "").replace(" ", "")
    if len(pnr) == 10:
        return pnr[:6] + "-" + pnr[6:]
    elif len(pnr) == 12:
        return pnr[2:8] + "-" + pnr[8:]
    return pnr

def avgor_headers(lines):
    for line in lines:
        parts = line.strip().split(';')
        if len(parts) > 5:
            klass = parts[5].strip().upper()
            if klass.startswith("6"):
                print("📘 Klass indikerar AK6 – använder AK6-struktur.")
                return HEADERS_AK6
            elif klass.startswith("9"):
                print("📙 Klass indikerar AK9 – använder AK9-struktur.")
                return HEADERS_AK9
    print("⚠️ Klass kunde inte tolkas – standard till AK6.")
    return HEADERS_AK6

def exportera_betyg_excel(txt_fil: Path, excel_fil: Path, struktur: str = None):
    if not txt_fil.exists():
        print(f"⚠️ Filen '{txt_fil}' saknas – hoppar över export.")
        return

    try:
        with txt_fil.open('r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        with txt_fil.open('r', encoding='cp1252', errors='replace') as f:
            lines = f.readlines()

    struktur_norm = struktur.upper() if isinstance(struktur, str) else None

    if struktur_norm == "AK6":
        headers = HEADERS_AK6
    elif struktur_norm == "AK9":
        headers = HEADERS_AK9
    else:
        headers = avgor_headers(lines)
        struktur_norm = "AK6" if headers == HEADERS_AK6 else "AK9"

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)

    klass_varningar = set()
    for line in lines:
        line = line.strip()
        if not line:
            continue

        row = line.split(';')
        if len(row) > 3:
            row[3] = formatera_personnummer(row[3])
        if len(row) > 5:
            for varning in validera_klass(row[5], struktur_norm, LASAR):
                klass_varningar.add(varning)

        if len(row) > len(headers):
            row = row[:len(headers)]
        elif len(row) < len(headers):
            row += [''] * (len(headers) - len(row))

        ws.append(row)

    for varning in sorted(klass_varningar):
        print(f"Varning: {varning}")

    wb.save(excel_fil)
    print(f"✅ Filen '{excel_fil.name}' har skapats i '{excel_fil.parent}'.")

if __name__ == "__main__":
    BASE = Path(__file__).resolve().parent.parent
    lasar = LASAR
    base_out = BASE / "data" / "output" / lasar

    exportera_betyg_excel(
        txt_fil=base_out / "betyg_ak6.txt",
        excel_fil=base_out / "betyg_ak6.xlsx",
        struktur="AK6"
    )

    exportera_betyg_excel(
        txt_fil=base_out / "betyg_ak9.txt",
        excel_fil=base_out / "betyg_ak9.xlsx",
        struktur="AK9"
    )
