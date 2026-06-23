from pathlib import Path
import json
import pandas as pd
from config_paths import OUTPUT_DIR, JSON_MAPP

def busavsjo_les_excel_med_merit(fil: Path, arskurs: int) -> dict | None:
    """Läser en Excelfil och returnerar medelmeritvärde för en viss årskurs."""
    if not fil.exists():
        print(f"⚠️ Filen '{fil}' saknas – hoppar över.")
        return None

    df = pd.read_excel(fil)

    kolumnnamn = "MeritvardeGY" if arskurs == 9 else "Meritvärde"
    if kolumnnamn not in df.columns:
        print(f"⚠️ Kolumnen '{kolumnnamn}' saknas i '{fil.name}'.")
        print(f"Tillgängliga kolumner: {list(df.columns)}")
        return None

    medel = pd.to_numeric(df[kolumnnamn], errors="coerce").mean()
    return {"Årskurs": arskurs, "MedelMeritvärde": round(float(medel), 2)}

def busavsjo_berakna_medel_merit():
    """Beräknar medelmeritvärde för åk 6 och 9 och sparar resultatet som JSON."""
    filer = [
        ("betyg_ak6_med_merit.xlsx", 6),
        ("betyg_ak9_med_merit.xlsx", 9),
    ]

    resultat = []
    for filnamn, arskurs in filer:
        fil = OUTPUT_DIR / filnamn
        data = busavsjo_les_excel_med_merit(fil, arskurs)
        if data:
            resultat.append(data)

    if not resultat:
        print("⚠️ Ingen data att spara.")
        return

    JSON_MAPP.mkdir(parents=True, exist_ok=True)
    out_fil = JSON_MAPP / "medel_meritvarde.json"
    with out_fil.open("w", encoding="utf-8") as f:
        json.dump(resultat, f, ensure_ascii=False, indent=2)
    print(f"✅ Sparade medel meritvärde i '{out_fil}'.")

if __name__ == "__main__":
    busavsjo_berakna_medel_merit()
