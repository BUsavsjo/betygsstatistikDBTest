from __future__ import annotations

from dataclasses import dataclass

VALID_GRADES = {"A", "B", "C", "D", "E", "F"}
PASSING_GRADES = {"A", "B", "C", "D", "E"}
SPECIAL_CODES = {"", "2", "3", "9", "Y", "Z"}
NP_SPECIAL_CODES = {"77", "88", "99"}
GRADE_POINTS = {"A": 20.0, "B": 17.5, "C": 15.0, "D": 12.5, "E": 10.0, "F": 0.0}
PUBLIC_JSON_FILES = [
    "manifest.json",
    "betygsstatistik_oversikt.json",
    "betygsstatistik_sv_sva.json",
    "betygsstatistik_betygsfordelning_amne.json",
    "betygsstatistik_kontroll_betyg.json",
    "np_andel_godkanda.json",
    "np_betyg_relation.json",
    "skolenheter_lookup.json",
]
SAVSJO_SCHOOL_NAMES = {
    "13654995": "Hagneskolan",
    "28504550": "Savsjo kristna skola",
    "53857703": "Vallsjoskolan",
    "59983229": "Hofgardsskolan",
    "60194444": "Vrigstad skola",
    "74170440": "Rorviks skola",
    "77440739": "Stockaryds skola",
}

AK6_COLUMNS = [
    "System", "Datum", "Version", "PersonNr", "Skolenhetskod", "Klass", "Fornamn", "Efternamn",
    "Bl", "En", "Hkk", "Idh", "Ma", "M1_sprak", "M1_betyg", "M2_sprak", "M2_betyg",
    "Modm_anm", "Modmalbe", "Mu", "No", "Bi", "Fy", "Ke", "So", "Ge", "Hi", "Re", "Sh",
    "Sl", "Sv", "Sva", "Tn", "Tk", "Ovr",
]

AK9_COLUMNS = [
    "System", "Datum", "Version", "PersonNr", "Skolenhetskod", "Klass", "Fornamn", "Efternamn",
    "Bl", "En", "Hkk", "Idh", "Ma", "M1_sprak", "M1_betyg", "M2_sprak", "M2_betyg",
    "ML_sprak", "ML_betyg", "Mu", "Bi", "Fy", "Ke", "Ge", "Hi", "Re", "Sh", "Sl",
    "Sv", "Sva", "Tn", "Tk", "Ovr",
]

AK6_SUBJECTS = ["Bl", "En", "Hkk", "Idh", "Ma", "M1_betyg", "M2_betyg", "Modmalbe", "Mu", "No", "Bi", "Fy", "Ke", "So", "Ge", "Hi", "Re", "Sh", "Sl", "Sv", "Sva", "Tn", "Tk", "Ovr"]
AK9_SUBJECTS = ["Bl", "En", "Hkk", "Idh", "Ma", "M1_betyg", "M2_betyg", "ML_betyg", "Mu", "Bi", "Fy", "Ke", "Ge", "Hi", "Re", "Sh", "Sl", "Sv", "Sva", "Tn", "Tk", "Ovr"]


@dataclass(frozen=True)
class GradeSpec:
    arskurs: int
    raw_folder: str
    columns: list[str]
    subjects: list[str]


SPECS = {
    6: GradeSpec(6, "ak6", AK6_COLUMNS, AK6_SUBJECTS),
    9: GradeSpec(9, "ak9", AK9_COLUMNS, AK9_SUBJECTS),
}

NP_AK3_COLUMNS = [
    "System", "Datum", "Version", "PersonNr", "Skolenhetskod",
    "MA_GRUPP", "MA_A_PR", "MA_B_PR", "MA_C_PR", "MA_D_PR", "MA_E_PR", "MA_F_PR", "MA_G_PR",
    "MA_G1_PR", "MA_G2_PR", "MA_B_POANG", "MA_C_POANG", "MA_D_POANG", "MA_E_POANG",
    "MA_F_POANG", "MA_G_POANG", "MA_G1_POANG", "MA_G2_POANG",
    "SV_GRUPP", "SV_KURSPLAN", "SV_A_PR", "SV_B_PR", "SV_C_PR", "SV_D_PR", "SV_E_PR",
    "SV_F_PR", "SV_G_PR", "SV_H_PR", "SV_B_POANG", "SV_C_POANG",
]

NP_AK3_COLUMNS_COMPACT = [
    "System", "Datum", "Version", "PersonNr", "Skolenhetskod",
    "MA_GRUPP", "MA_A_PR", "MA_B_PR", "MA_C_PR", "MA_D_PR", "MA_E_PR", "MA_F_PR", "MA_G_PR",
    "MA_B_POANG", "MA_C_POANG", "MA_D_POANG", "MA_E_POANG", "MA_F_POANG", "MA_G_POANG",
    "SV_GRUPP", "SV_KURSPLAN", "SV_A_PR", "SV_B_PR", "SV_C_PR", "SV_D_PR", "SV_E_PR",
    "SV_F_PR", "SV_G_PR", "SV_H_PR", "SV_B_POANG", "SV_C_POANG",
]

NP_AK6_COLUMNS = [
    "System", "Datum", "Version", "PersonNr", "Skolenhetskod",
    "MA_GRUPP", "MA_A_DELT", "MA_B_DELT", "MA_C_DELT", "MA_D_DELT", "MA_E_DELT", "MA_PROVB",
    "SV_GRUPP", "SV_KURSPLAN", "SV_A_DELT", "SV_B_DELT", "SV_C_DELT",
    "SV_A_PRP", "SV_B_PRP", "SV_C_PRP", "SV_PROVB",
    "EN_GRUPP", "EN_A_DELT", "EN_B_DELT", "EN_C_DELT", "EN_A_PRP", "EN_B_PRP", "EN_C_PRP", "EN_PROVB",
]

NP_AK6_COLUMNS_COMPACT = [
    "System", "Datum", "Version", "PersonNr", "Skolenhetskod",
    "MA_GRUPP", "MA_A_DELT", "MA_B_DELT", "MA_C_DELT", "MA_D_DELT", "MA_E_DELT", "MA_PROVB",
    "SV_GRUPP", "SV_KURSPLAN", "SV_A_PRP", "SV_B_PRP", "SV_C_PRP", "SV_PROVB",
    "EN_GRUPP", "EN_A_PRP", "EN_B_PRP", "EN_C_PRP", "EN_PROVB",
]

NP_AK9_COLUMNS = [
    "System", "Datum", "Version", "PersonNr", "Skolenhetskod",
    "MA_GRUPP", "MA_A_DELT", "MA_B_DELT", "MA_C_DELT", "MA_D_DELT", "MA_PROVB",
    "SV_GRUPP", "SV_KURSPLAN", "SV_A_PRP", "SV_B_PRP", "SV_C_PRP", "SV_PROVB",
    "EN_GRUPP", "EN_A_PRP", "EN_B_PRP", "EN_C_PRP", "EN_PROVB",
    "NO_PROV", "NO_A_DELT", "NO_B_DELT", "NO_GRUPP", "NO_PROVB",
    "SO_PROV", "SO_A_DELT", "SO_B_DELT", "SO_GRUPP", "SO_PROVB",
]


@dataclass(frozen=True)
class NpSpec:
    arskurs: int
    raw_folder: str
    columns: list[str]
    alternate_columns: list[list[str]] | None = None


NP_SPECS = {
    3: NpSpec(3, "ak3", NP_AK3_COLUMNS, alternate_columns=[NP_AK3_COLUMNS_COMPACT]),
    6: NpSpec(6, "ak6", NP_AK6_COLUMNS, alternate_columns=[NP_AK6_COLUMNS_COMPACT]),
    9: NpSpec(9, "ak9", NP_AK9_COLUMNS),
}
