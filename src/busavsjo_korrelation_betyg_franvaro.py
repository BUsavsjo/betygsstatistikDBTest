import pandas as pd
import numpy as np
import json
from pathlib import Path
from config_paths import DATA_MAPP, JSON_MAPP, LASAR

BETYGSFILER = {
    "6": DATA_MAPP / "betyg_ak6.xlsx",
    "9": DATA_MAPP / "betyg_ak9.xlsx",
}

FRANVARO_FIL = DATA_MAPP / "franvaro_total.xlsx"

FRANVAROTYPER = {
    "ogiltig_franvaro_pct": "Ogiltig frånvaro (%)",
    "total_franvaro_pct": "Total frånvaro (%)",
    "giltig_franvaro_pct": "Giltig frånvaro (%)"
}


def spara_json(df, filnamn, årskurs):
    (JSON_MAPP).mkdir(parents=True, exist_ok=True)
    df_clean = df.copy()

    df_clean["Korrelation"] = df_clean["Korrelation"].apply(
        lambda x: round(float(x), 2)
        if isinstance(x, (int, float, np.floating)) and not np.isnan(x)
        else None
    )

    df_clean = df_clean.astype(object).where(pd.notna(df_clean), None)
    df_clean["Läsår"] = LASAR
    df_clean["Årskurs"] = årskurs

    with (JSON_MAPP / filnamn).open("w", encoding="utf-8") as f:
        json.dump(
            df_clean.to_dict(orient="records"),
            f,
            indent=2,
            ensure_ascii=False,
            default=lambda x: float(x) if isinstance(x, (np.floating, np.integer)) and not pd.isna(x) else None,
            allow_nan=False,
        )


def analysera_korrelation(klass_varde, betyg_df):
    ämnen_ak6 = ["BI", "En", "Hkk", "idh", "Ma", "mu", "No", "So", "Sv", "Sva", "Tk"]
    ämnen_ak9 = ["BI", "En", "Hkk", "idh", "Ma", "mu", "Bi", "Fy", "Ke", "Ge", "Hi", "Re", "Sh", "SI", "Sv", "Sva", "Tn", "Tk"]
    ämnen = ämnen_ak6 if klass_varde == "6" else ämnen_ak9

    betygsskala = {
        "A": 20,
        "B": 17.5,
        "C": 15,
        "D": 12.5,
        "E": 10,
        "F": 0,
    }

    franvaro_df = pd.read_excel(FRANVARO_FIL)
    df = pd.merge(betyg_df, franvaro_df, on="PersonNr", how="inner")

    for ämne in ämnen:
        if ämne in df.columns:
            df[ämne] = df[ämne].replace(["2", "3"], np.nan)
            df[ämne] = pd.to_numeric(df[ämne].replace(betygsskala), errors="coerce").astype("float32")

    for franvarotyp, beskrivning in FRANVAROTYPER.items():
        resultat = []
        for ämne in ämnen:
            if ämne in df.columns:
                delmängd = df[[ämne, franvarotyp]].dropna()
                if not delmängd.empty and delmängd[franvarotyp].nunique() > 1 and delmängd[ämne].nunique() > 1:
                    korrelation = delmängd[ämne].corr(delmängd[franvarotyp])
                    if pd.isna(korrelation):
                        korrelation = None
                else:
                    korrelation = None

                styrka = styrkebedömning(korrelation)
                resultat.append({
                    "Ämne": ämne,
                    "Frånvarotyp": franvarotyp,
                    "Korrelation": korrelation,
                    "Styrka": styrka
                })

        df_resultat = pd.DataFrame(resultat)
        filnamn = f"{franvarotyp}_ak{klass_varde}.json".replace("å", "a").replace("ä", "a").replace("ö", "o")
        spara_json(df_resultat, filnamn, årskurs=klass_varde)
        print(f"📄 Sparade {filnamn} med {len(df_resultat)} rader.")

    merit_resultat = []
    for franvarotyp in FRANVAROTYPER.keys():
        delmängd = df[["Meritvärde", franvarotyp]].dropna()
        if (
            not delmängd.empty
            and delmängd[franvarotyp].nunique() > 1
            and delmängd["Meritvärde"].nunique() > 1
        ):
            korrelation = delmängd["Meritvärde"].corr(delmängd[franvarotyp])
            if pd.isna(korrelation):
                korrelation = None
        else:
            korrelation = None

        styrka = styrkebedömning(korrelation)
        merit_resultat.append(
            {
                "Ämne": "Meritvärde",
                "Frånvarotyp": franvarotyp,
                "Korrelation": korrelation,
                "Styrka": styrka,
            }
        )

    df_merit = pd.DataFrame(merit_resultat)
    filnamn_merit = f"meritvarde_ak{klass_varde}.json"
    spara_json(df_merit, filnamn_merit, årskurs=klass_varde)
    print(f"📄 Sparade {filnamn_merit} med {len(df_merit)} rader.")


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


def beräkna_och_spara_meritvärde(df, årskurs: str, ursprungsfil: Path):
    betygsskala = {"A": 20, "B": 17.5, "C": 15, "D": 12.5, "E": 10, "F": 0}
    språkvalskolumner = ["M1(betyg)", "M2(betyg)"]
    icke_betygskolumner = ["PersonNr", "Namn", "Klass"] + språkvalskolumner

    betygskolumner = [
        col for col in df.columns
        if col not in icke_betygskolumner and df[col].isin(betygsskala.keys()).any()
    ]

    ogiltiga_koder = {"2", "3", "9", "Z", "Y"}

    meritvärden = []
    for _, rad in df.iterrows():
        betygspoäng = []
        for ämne in betygskolumner:
            betyg = str(rad.get(ämne)).strip()
            if betyg in ogiltiga_koder:
                continue
            poäng = betygsskala.get(betyg, 0)
            betygspoäng.append(poäng)

        har_språkval = False
        for kolumn in språkvalskolumner:
            betyg = rad.get(kolumn)
            if isinstance(betyg, str) and betyg.strip() in betygsskala and betyg != "F":
                har_språkval = True
                break

        max_antal = 17 if har_språkval else 16
        poäng_summa = sum(sorted(betygspoäng, reverse=True)[:max_antal])
        meritvärden.append(poäng_summa)

    df["Meritvärde"] = meritvärden

    # 💡 Sätt None på elever med Meritvärde 0 i åk 6
    if årskurs == "6":
        df.loc[df["Meritvärde"] == 0, "Meritvärde"] = None

    if årskurs == "9":
        godkända_koder = {"A", "B", "C", "D", "E"}
        gy_meritvärden = []
        for idx, rad in df.iterrows():
            sv = str(rad.get("Sv", "")).strip()
            sva = str(rad.get("Sva", "")).strip()
            en = str(rad.get("En", "")).strip()
            ma = str(rad.get("Ma", "")).strip()

            sv_sva_godkänd = sv in godkända_koder or sva in godkända_koder
            en_godkänd = en in godkända_koder
            ma_godkänd = ma in godkända_koder

            antal_godkända = 0
            for ämne in betygskolumner:
                betyg = str(rad.get(ämne)).strip()
                if betyg in godkända_koder:
                    antal_godkända += 1

            if sv_sva_godkänd and en_godkänd and ma_godkänd and antal_godkända >= 8:
                gy_meritvärden.append(meritvärden[idx])
            else:
                gy_meritvärden.append(None)

        df["MeritvardeGY"] = gy_meritvärden

    ny_fil = ursprungsfil.parent / ursprungsfil.name.replace(".xlsx", "_med_merit.xlsx")
    df.to_excel(ny_fil, index=False)
    print(f"💾 Sparade {ny_fil.name} med kolumnerna 'Meritvärde'{', MeritvardeGY' if årskurs == '9' else ''}.")


if __name__ == "__main__":
    for årskurs, betygfil in BETYGSFILER.items():
        if not betygfil.exists():
            print(f"⚠️ Betygsfil för årskurs {årskurs} saknas: {betygfil.name}")
            continue
        print(f"🗓️ Läser betyg för årskurs {årskurs} från {betygfil.name}")
        betyg_df = pd.read_excel(betygfil)

        beräkna_och_spara_meritvärde(betyg_df, årskurs, betygfil)

        ny_betygfil = betygfil.parent / betygfil.name.replace(".xlsx", "_med_merit.xlsx")
        betyg_df_med_merit = pd.read_excel(ny_betygfil)

        analysera_korrelation(årskurs, betyg_df_med_merit)
