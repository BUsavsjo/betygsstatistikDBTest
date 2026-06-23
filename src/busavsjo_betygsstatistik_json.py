import json
from pathlib import Path

import pandas as pd

from config_paths import CONFIG_DIR, JSON_MAPP, LASAR, OUTPUT_DIR


BETYGSFILER = {
    6: OUTPUT_DIR / "betyg_ak6_med_merit.xlsx",
    9: OUTPUT_DIR / "betyg_ak9_med_merit.xlsx",
}

AMNEN_AK6 = ["BI", "En", "Hkk", "idh", "Ma", "mu", "No", "So", "Sv", "Sva", "Tk"]
AMNEN_AK9 = [
    "BI", "En", "Hkk", "idh", "Ma", "mu", "Bi", "Fy", "Ke", "Ge", "Hi",
    "Re", "Sh", "SI", "Sv", "Sva", "Tn", "Tk",
]

BETYGSPOANG = {"A": 20.0, "B": 17.5, "C": 15.0, "D": 12.5, "E": 10.0, "F": 0.0}
GODKANDA_BETYG = {"A", "B", "C", "D", "E"}
SAKNAS_KODER = {"", "2", "3", "9", "Y", "Z", "NAN", "NONE"}
SPRAKVAL_BETYGSKOLUMNER = ["M1(betyg)", "M2(betyg)"]


def _json_safe(value):
    if pd.isna(value):
        return None
    if isinstance(value, float):
        return round(value, 2)
    return value


def _spara_json(data, filnamn):
    JSON_MAPP.mkdir(parents=True, exist_ok=True)
    with (JSON_MAPP / filnamn).open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=_json_safe, allow_nan=False)


def _las_subject_names():
    fil = CONFIG_DIR / "subject_names.json"
    if not fil.exists():
        return {}
    with fil.open("r", encoding="utf-8") as f:
        return json.load(f)


def _normalisera_betyg(value):
    if pd.isna(value):
        return None
    betyg = str(value).strip().upper()
    if betyg in SAKNAS_KODER:
        return None
    return betyg if betyg in BETYGSPOANG else None


def _ar_godkand(value):
    return _normalisera_betyg(value) in GODKANDA_BETYG


def _kolumn(df, namn):
    for col in df.columns:
        if str(col).strip().lower() == namn.lower():
            return col
    return None


def _amnen_for_arskurs(arskurs):
    return AMNEN_AK6 if arskurs == 6 else AMNEN_AK9


def _betygskolumner(df, arskurs):
    return [kol for kol in _amnen_for_arskurs(arskurs) if kol in df.columns]


def _sv_sva_grupp(rad):
    har_sv = _normalisera_betyg(rad.get("Sv")) is not None
    har_sva = _normalisera_betyg(rad.get("Sva")) is not None
    if har_sv and har_sva:
        return "SV_och_SVA"
    if har_sva:
        return "SVA"
    if har_sv:
        return "SV"
    return "okand"


def _berakna_merit(rad, betygskolumner):
    poang = []
    sv_sva_poang = []
    for kol in betygskolumner:
        betyg = _normalisera_betyg(rad.get(kol))
        if betyg is not None:
            if kol in {"Sv", "Sva"}:
                sv_sva_poang.append(BETYGSPOANG[betyg])
            else:
                poang.append(BETYGSPOANG[betyg])

    if sv_sva_poang:
        poang.append(max(sv_sva_poang))

    merit_16 = sum(sorted(poang, reverse=True)[:16])

    sprakvalspoang = []
    for kol in SPRAKVAL_BETYGSKOLUMNER:
        betyg = _normalisera_betyg(rad.get(kol))
        if betyg in GODKANDA_BETYG:
            sprakvalspoang.append(BETYGSPOANG[betyg])

    merit_17 = merit_16 + max(sprakvalspoang, default=0.0)
    return merit_16, merit_17


def _rakna_godkanda_andra_amnen(rad, betygskolumner):
    karnamnen = {"Sv", "Sva", "En", "Ma"}
    return sum(1 for kol in betygskolumner if kol not in karnamnen and _ar_godkand(rad.get(kol)))


def _behorig_yrkesprogram(rad, betygskolumner):
    return (
        (_ar_godkand(rad.get("Sv")) or _ar_godkand(rad.get("Sva")))
        and _ar_godkand(rad.get("En"))
        and _ar_godkand(rad.get("Ma"))
        and _rakna_godkanda_andra_amnen(rad, betygskolumner) >= 5
    )


def _behorig_es(rad, betygskolumner):
    return (
        (_ar_godkand(rad.get("Sv")) or _ar_godkand(rad.get("Sva")))
        and _ar_godkand(rad.get("En"))
        and _ar_godkand(rad.get("Ma"))
        and _rakna_godkanda_andra_amnen(rad, betygskolumner) >= 9
    )


def _behorig_ek_hu_sa(rad, betygskolumner):
    so_amnen = ["Ge", "Hi", "Re", "Sh"]
    return _behorig_es(rad, betygskolumner) and all(_ar_godkand(rad.get(kol)) for kol in so_amnen)


def _behorig_na_te(rad, betygskolumner):
    no_amnen = ["Bi", "Fy", "Ke"]
    return _behorig_es(rad, betygskolumner) and all(_ar_godkand(rad.get(kol)) for kol in no_amnen)


def _uppnatt_alla_amnen(rad, betygskolumner):
    amnen_med_betyg = [kol for kol in betygskolumner if kol not in {"Sv", "Sva"} and _normalisera_betyg(rad.get(kol)) is not None]
    if not amnen_med_betyg:
        return False
    sv_sva_finns = _normalisera_betyg(rad.get("Sv")) is not None or _normalisera_betyg(rad.get("Sva")) is not None
    sv_sva_godkand = _ar_godkand(rad.get("Sv")) or _ar_godkand(rad.get("Sva"))
    if sv_sva_finns and not sv_sva_godkand:
        return False
    return all(_ar_godkand(rad.get(kol)) for kol in amnen_med_betyg)


def _skolenhet_lookup(koder):
    fil = JSON_MAPP / "skolenheter_lookup.json"
    lookup = {}
    if fil.exists():
        with fil.open("r", encoding="utf-8") as f:
            lookup = json.load(f)

    for kod in koder:
        kod = str(kod).strip()
        if kod and kod not in lookup:
            lookup[kod] = None

    _spara_json(lookup, "skolenheter_lookup.json")
    return lookup


def _forbered_df(fil: Path, arskurs: int):
    df = pd.read_excel(fil)
    skolenhetskolumn = _kolumn(df, "Skolenhetskod")
    if skolenhetskolumn is None:
        raise ValueError(f"Skolenhetskod saknas i {fil.name}")

    df["skolenhetskod"] = df[skolenhetskolumn].astype(str).str.strip()
    if "gender" not in df.columns:
        df["gender"] = "okand"

    betygskolumner = _betygskolumner(df, arskurs)
    df["sv_sva_grupp"] = df.apply(_sv_sva_grupp, axis=1)
    merit = df.apply(lambda rad: _berakna_merit(rad, betygskolumner), axis=1)
    df["meritvarde_16"] = [v[0] for v in merit]
    df["meritvarde_17"] = [v[1] for v in merit]

    if arskurs == 9:
        df["behorig_yrkesprogram"] = df.apply(lambda rad: _behorig_yrkesprogram(rad, betygskolumner), axis=1)
        df["behorig_hogskoleforberedande_es"] = df.apply(lambda rad: _behorig_es(rad, betygskolumner), axis=1)
        df["behorig_hogskoleforberedande_ek_hu_sa"] = df.apply(lambda rad: _behorig_ek_hu_sa(rad, betygskolumner), axis=1)
        df["behorig_hogskoleforberedande_na_te"] = df.apply(lambda rad: _behorig_na_te(rad, betygskolumner), axis=1)
        df["behorig_hogskoleforberedande_nagot_program"] = (
            df["behorig_hogskoleforberedande_es"]
            | df["behorig_hogskoleforberedande_ek_hu_sa"]
            | df["behorig_hogskoleforberedande_na_te"]
        )
    else:
        for kol in [
            "behorig_yrkesprogram",
            "behorig_hogskoleforberedande_es",
            "behorig_hogskoleforberedande_ek_hu_sa",
            "behorig_hogskoleforberedande_na_te",
            "behorig_hogskoleforberedande_nagot_program",
        ]:
            df[kol] = None

    df["uppnatt_alla_amnen"] = df.apply(lambda rad: _uppnatt_alla_amnen(rad, betygskolumner), axis=1)
    df["arskurs"] = arskurs
    df["lasar"] = LASAR
    return df, betygskolumner


def _grupper(df):
    grupper = [("alla_skolenheter", "Alla", df)]
    for kod, subset in df.groupby("skolenhetskod", dropna=False):
        grupper.append(("skolenhet", str(kod), subset))
    return grupper


def _segment(subset):
    segment = [("Alla", "Alla", subset)]
    for gender, gender_df in subset.groupby("gender", dropna=False):
        segment.append((str(gender), "Alla", gender_df))
    for grupp, grupp_df in subset.groupby("sv_sva_grupp", dropna=False):
        segment.append(("Alla", str(grupp), grupp_df))
    for (gender, grupp), grupp_df in subset.groupby(["gender", "sv_sva_grupp"], dropna=False):
        segment.append((str(gender), str(grupp), grupp_df))
    return segment


def _basrad(arskurs, niva, kod, kon, elevgrupp, lookup):
    kod_value = None if niva == "alla_skolenheter" else str(kod)
    return {
        "lasar": LASAR,
        "arskurs": arskurs,
        "niva": niva,
        "skolenhetskod": kod_value,
        "skolenhetsnamn": "Alla skolenheter" if kod_value is None else lookup.get(kod_value),
        "kon": kon,
        "elevgrupp": elevgrupp,
    }


def _andel(series):
    if len(series) == 0:
        return None
    return round(float(series.mean() * 100), 2)


def _oversikt(df, arskurs, lookup):
    resultat = []
    for niva, kod, subset in _grupper(df):
        for kon, elevgrupp, seg in _segment(subset):
            rad = _basrad(arskurs, niva, kod, kon, elevgrupp, lookup)
            rad.update({
                "antal_elever": int(len(seg)),
                "genomsnittligt_meritvarde_16": _json_safe(pd.to_numeric(seg["meritvarde_16"], errors="coerce").mean()),
                "genomsnittligt_meritvarde_17": _json_safe(pd.to_numeric(seg["meritvarde_17"], errors="coerce").mean()),
                "median_meritvarde_17": _json_safe(pd.to_numeric(seg["meritvarde_17"], errors="coerce").median()),
                "andel_uppnatt_alla_amnen": _andel(seg["uppnatt_alla_amnen"]),
            })
            if arskurs == 9:
                rad.update({
                    "andel_behoriga_yrkesprogram": _andel(seg["behorig_yrkesprogram"]),
                    "andel_behoriga_hogskoleforberedande_nagot_program": _andel(seg["behorig_hogskoleforberedande_nagot_program"]),
                })
            resultat.append(rad)
    return resultat


def _behorighet(df, lookup):
    resultat = []
    program = [
        ("yrkesprogram", "behorig_yrkesprogram"),
        ("hogskoleforberedande_es", "behorig_hogskoleforberedande_es"),
        ("hogskoleforberedande_ek_hu_sa", "behorig_hogskoleforberedande_ek_hu_sa"),
        ("hogskoleforberedande_na_te", "behorig_hogskoleforberedande_na_te"),
        ("hogskoleforberedande_nagot_program", "behorig_hogskoleforberedande_nagot_program"),
    ]
    df = df[df["arskurs"] == 9]
    for niva, kod, subset in _grupper(df):
        for kon, elevgrupp, seg in _segment(subset):
            for namn, kol in program:
                rad = _basrad(9, niva, kod, kon, elevgrupp, lookup)
                antal = int(len(seg))
                behoriga = int(seg[kol].sum()) if antal else 0
                rad.update({
                    "programtyp": namn,
                    "antal_elever": antal,
                    "antal_behoriga": behoriga,
                    "antal_ej_behoriga": antal - behoriga,
                    "andel_behoriga": round(behoriga / antal * 100, 2) if antal else None,
                })
                resultat.append(rad)
    return resultat


def _meritvarde(df, arskurs, lookup):
    resultat = []
    for niva, kod, subset in _grupper(df):
        for kon, elevgrupp, seg in _segment(subset):
            rad = _basrad(arskurs, niva, kod, kon, elevgrupp, lookup)
            merit16 = pd.to_numeric(seg["meritvarde_16"], errors="coerce")
            merit17 = pd.to_numeric(seg["meritvarde_17"], errors="coerce")
            rad.update({
                "antal_elever": int(len(seg)),
                "medel_meritvarde_16": _json_safe(merit16.mean()),
                "medel_meritvarde_17": _json_safe(merit17.mean()),
                "median_meritvarde_17": _json_safe(merit17.median()),
                "q1_meritvarde_17": _json_safe(merit17.quantile(0.25)),
                "q3_meritvarde_17": _json_safe(merit17.quantile(0.75)),
            })
            resultat.append(rad)
    return resultat


def _betygsfordelning(df, arskurs, betygskolumner, lookup, subject_names):
    resultat = []
    for niva, kod, subset in _grupper(df):
        for kon, elevgrupp, seg in _segment(subset):
            for amne in betygskolumner:
                betyg = seg[amne].apply(_normalisera_betyg)
                betyg = betyg[betyg.notna()]
                antal = int(len(betyg))
                rad = _basrad(arskurs, niva, kod, kon, elevgrupp, lookup)
                rad.update({
                    "amne": amne,
                    "amnesnamn": subject_names.get(amne, amne),
                    "antal_betyg": antal,
                    "antal_A_E": int(betyg.isin(GODKANDA_BETYG).sum()),
                    "antal_F": int((betyg == "F").sum()),
                    "andel_A_E": round(float(betyg.isin(GODKANDA_BETYG).mean() * 100), 2) if antal else None,
                    "andel_F": round(float((betyg == "F").mean() * 100), 2) if antal else None,
                })
                for grade in ["A", "B", "C", "D", "E", "F"]:
                    antal_grade = int((betyg == grade).sum())
                    rad[f"antal_{grade}"] = antal_grade
                    rad[f"andel_{grade}"] = round(antal_grade / antal * 100, 2) if antal else None
                resultat.append(rad)
    return resultat


def _kunskapskriterier(df, arskurs, betygskolumner, lookup, subject_names):
    resultat = []
    for niva, kod, subset in _grupper(df):
        for kon, elevgrupp, seg in _segment(subset):
            rad = _basrad(arskurs, niva, kod, kon, elevgrupp, lookup)
            rad.update({
                "amne": "alla_amnen",
                "amnesnamn": "Alla amnen",
                "antal_elever": int(len(seg)),
                "antal_uppnatt": int(seg["uppnatt_alla_amnen"].sum()),
                "andel_uppnatt": _andel(seg["uppnatt_alla_amnen"]),
            })
            resultat.append(rad)

            for amne in betygskolumner:
                betyg = seg[amne].apply(_normalisera_betyg)
                med_betyg = betyg[betyg.notna()]
                antal = int(len(med_betyg))
                rad = _basrad(arskurs, niva, kod, kon, elevgrupp, lookup)
                rad.update({
                    "amne": amne,
                    "amnesnamn": subject_names.get(amne, amne),
                    "antal_elever": int(len(seg)),
                    "antal_i_berakning": antal,
                    "antal_uppnatt": int(med_betyg.isin(GODKANDA_BETYG).sum()),
                    "andel_uppnatt": round(float(med_betyg.isin(GODKANDA_BETYG).mean() * 100), 2) if antal else None,
                })
                resultat.append(rad)
    return resultat


def _signaler(oversikt, betygsfordelning):
    signaler = []
    for rad in betygsfordelning:
        if rad["niva"] != "skolenhet" or rad["kon"] != "Alla" or rad["elevgrupp"] != "Alla":
            continue
        if rad["antal_betyg"] >= 5 and rad["andel_F"] is not None and rad["andel_F"] >= 20:
            signaler.append({
                "lasar": rad["lasar"],
                "arskurs": rad["arskurs"],
                "skolenhetskod": rad["skolenhetskod"],
                "skolenhetsnamn": rad["skolenhetsnamn"],
                "signaltyp": "hog_andel_f",
                "amne": rad["amne"],
                "amnesnamn": rad["amnesnamn"],
                "varde": rad["andel_F"],
                "antal_i_berakning": rad["antal_betyg"],
            })

    for rad in oversikt:
        if rad["niva"] != "skolenhet" or rad["kon"] != "Alla" or rad["elevgrupp"] != "Alla":
            continue
        if rad.get("andel_behoriga_yrkesprogram") is not None and rad["andel_behoriga_yrkesprogram"] < 80:
            signaler.append({
                "lasar": rad["lasar"],
                "arskurs": rad["arskurs"],
                "skolenhetskod": rad["skolenhetskod"],
                "skolenhetsnamn": rad["skolenhetsnamn"],
                "signaltyp": "lag_behorighet_yrkesprogram",
                "varde": rad["andel_behoriga_yrkesprogram"],
                "antal_i_berakning": rad["antal_elever"],
            })
    return signaler


def bygg_betygsstatistik_json():
    subject_names = _las_subject_names()
    data = []
    betygskolumner_per_arskurs = {}

    for arskurs, fil in BETYGSFILER.items():
        if not fil.exists():
            print(f"Saknar {fil.name}, hoppar over ak {arskurs}.")
            continue
        df, betygskolumner = _forbered_df(fil, arskurs)
        data.append(df)
        betygskolumner_per_arskurs[arskurs] = betygskolumner

    if not data:
        print("Ingen betygsdata hittades for betygsstatistik.")
        return

    alla = pd.concat(data, ignore_index=True)
    lookup = _skolenhet_lookup(alla["skolenhetskod"].dropna().unique())

    oversikt = []
    meritvarde = []
    betygsfordelning = []
    kunskapskriterier = []

    for arskurs, df in alla.groupby("arskurs"):
        betygskolumner = betygskolumner_per_arskurs[int(arskurs)]
        oversikt.extend(_oversikt(df, int(arskurs), lookup))
        meritvarde.extend(_meritvarde(df, int(arskurs), lookup))
        betygsfordelning.extend(_betygsfordelning(df, int(arskurs), betygskolumner, lookup, subject_names))
        kunskapskriterier.extend(_kunskapskriterier(df, int(arskurs), betygskolumner, lookup, subject_names))

    behorighet = _behorighet(alla, lookup)
    signaler = _signaler(oversikt, betygsfordelning)

    _spara_json(oversikt, "betygsstatistik_oversikt.json")
    _spara_json(meritvarde, "betygsstatistik_meritvarde.json")
    _spara_json(behorighet, "betygsstatistik_behorighet_gy.json")
    _spara_json(betygsfordelning, "betygsstatistik_betygsfordelning_amne.json")
    _spara_json(kunskapskriterier, "betygsstatistik_kunskapskriterier.json")
    _spara_json(signaler, "betygsstatistik_signaler.json")
    print("Sparade JSON-filer for betygsstatistik.")


if __name__ == "__main__":
    bygg_betygsstatistik_json()
