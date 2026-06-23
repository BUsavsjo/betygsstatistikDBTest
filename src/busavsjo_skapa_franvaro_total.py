import pandas as pd
from config_paths import OUTPUT_DIR

# Infil och utfil
FIL_RENSAD = OUTPUT_DIR / "franvaro_rensad_kategoriserad.xlsx"
FIL_TOTAL = OUTPUT_DIR / "franvaro_total.xlsx"

def skapa_franvaro_total():
    """Extraherar PersonNr och frånvarokolumner till ny fil för korrelationsanalys."""
    print("📤 Skapar franvaro_total.xlsx...")

    try:
        df = pd.read_excel(FIL_RENSAD, sheet_name="Rensad data")
    except FileNotFoundError:
        print(f"❌ Hittar inte {FIL_RENSAD}")
        return
    except Exception as e:
        print(f"❌ Fel vid läsning av rensad data: {e}")
        return

    if "personnr" not in df.columns or "närvaro_pct" not in df.columns or "ogiltig_frånvaro_pct" not in df.columns:
        print("❌ Nödvändiga kolumner saknas i rensad data.")
        return

    # Bygg ny dataframe
    df_ut = df[["personnr", "närvaro_pct", "ogiltig_frånvaro_pct"]].copy()
    df_ut = df_ut.rename(columns={
        "personnr": "PersonNr",
        "närvaro_pct": "narvaro_pct",
        "ogiltig_frånvaro_pct": "ogiltig_franvaro_pct"
    })

    # Beräkna total och giltig frånvaro
    df_ut["total_franvaro_pct"] = 100 - df_ut["narvaro_pct"]
    df_ut["giltig_franvaro_pct"] = df_ut["total_franvaro_pct"] - df_ut["ogiltig_franvaro_pct"]

    # Rensa bort rader utan personnummer
    df_ut.dropna(subset=["PersonNr"], inplace=True)

    df_ut.to_excel(FIL_TOTAL, index=False)
    print(f"✅ Skapade {FIL_TOTAL.name} med {len(df_ut)} rader.")

if __name__ == "__main__":
    skapa_franvaro_total()
