import pandas as pd
import numpy as np
import json
from config_paths import OUTPUT_DIR, JSON_MAPP, LASAR

BETYGSFILER = {
    "6": OUTPUT_DIR / "betyg_ak6_med_merit.xlsx",
    "9": OUTPUT_DIR / "betyg_ak9_med_merit.xlsx",
}

FRANVARO_FIL = OUTPUT_DIR / "franvaro_total.xlsx"

FRANVAROTYPER = {
    "ogiltig_franvaro_pct": "Ogiltig frånvaro (%)",
    "total_franvaro_pct": "Total frånvaro (%)",
    "giltig_franvaro_pct": "Giltig frånvaro (%)"
}

ämnen_ak6 = ["BI", "En", "Hkk", "idh", "Ma", "mu", "No", "So", "Sv", "Sva", "Tk"]
ämnen_ak9 = ["BI", "En", "Hkk", "idh", "Ma", "mu", "Bi", "Fy", "Ke", "Ge", "Hi", "Re", "Sh", "SI", "Sv", "Sva", "Tn", "Tk"]

OGILTIGA_BETYGSVARDEN = ["2", "3", "9", "Y", "Z", 2, 3, 9, "", None]


def spara_json(data, filnamn):
    JSON_MAPP.mkdir(parents=True, exist_ok=True)
    with (JSON_MAPP / filnamn).open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def styrkebedömning(k):
    if k is None:
        return "saknas"
    k_abs = abs(k)
    if k_abs < 0.1:
        return "ingen"
    elif k_abs < 0.3:
        return "svag"
    elif k_abs < 0.5:
        return "måttlig"
    elif k_abs < 0.7:
        return "stark"
    else:
        return "mycket stark"


def analysera_per_koen():
    resultat_merit = []

    for arskurs, fil in BETYGSFILER.items():
        df = pd.read_excel(fil)
        franvaro_df = pd.read_excel(FRANVARO_FIL)
        df = pd.merge(df, franvaro_df, on="PersonNr", how="inner")

        df = df[df["gender"].isin(["pojke", "flicka"])]
        ämnen = ämnen_ak6 if arskurs == "6" else ämnen_ak9

        for koen in df["gender"].dropna().unique():
            subset = df[df["gender"] == koen].copy()

            # Meritvärde
            medel = pd.to_numeric(subset["Meritvärde"], errors="coerce").mean()
            resultat_merit.append({
                "Ämne": "Meritvärde",
                "Gender": koen,
                "Värde": round(float(medel), 2),
                "Årskurs": arskurs,
                "Läsår": LASAR
            })

            # Korrelationsanalyser per kön → sparas separat
            betygsskala = {"A": 20, "B": 17.5, "C": 15, "D": 12.5, "E": 10, "F": 0}
            for franvarotyp in FRANVAROTYPER:
                resultat = []
                for kol in ämnen:
                    if kol not in subset.columns:
                        continue

                    s = subset[[kol, franvarotyp]].dropna().copy()
                    s = s[~s[kol].isin(OGILTIGA_BETYGSVARDEN)]
                    if s.empty:
                        k = None
                    else:
                        if s[kol].dtype == object:
                            s[kol] = s[kol].replace(betygsskala)
                        s[kol] = pd.to_numeric(s[kol], errors="coerce")
                        s = s.dropna(subset=[kol, franvarotyp])
                        if not s.empty and s[franvarotyp].nunique() > 1 and s[kol].nunique() > 1:
                            k = s[kol].corr(s[franvarotyp])
                        else:
                            k = None

                    resultat.append({
                        "Ämne": kol,
                        "Frånvarotyp": franvarotyp,
                        "Gender": koen,
                        "Korrelation": round(float(k), 2) if k is not None else None,
                        "Styrka": styrkebedömning(k),
                        "Årskurs": arskurs,
                        "Läsår": LASAR
                    })

                filnamn = f"{franvarotyp}_ak{arskurs}_{koen}.json"
                spara_json(resultat, filnamn)

    spara_json(resultat_merit, "medel_meritvarde_gender.json")


if __name__ == "__main__":
    analysera_per_koen()
    print("✅ Sparade könsuppdelade merit- och frånvarodata.")