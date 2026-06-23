import pandas as pd
from pathlib import Path
from config_paths import OUTPUT_DIR  # Se till att din sys.path är korrekt
import re

def busavsjo_berakna_koen(personnummer: str) -> str:
    """
    Returnerar kön utifrån personnummer:
    - Udda näst sista siffra: 'pojke'
    - Jämn näst sista siffra: 'flicka'
    """
    match = re.search(r'\d{6}[-+]?(\d{4})', str(personnummer))
    if not match:
        return "okänd"
    individnummer = match.group(1)
    if len(individnummer) != 4:
        return "okänd"
    näst_sista = int(individnummer[-2])
    return "pojke" if näst_sista % 2 == 1 else "flicka"

def bearbeta_fil(filnamn: str):
    filvag = OUTPUT_DIR / filnamn
    df = pd.read_excel(filvag)
    
    if 'PersonNr' not in df.columns:
        raise ValueError(f"'PersonNr' saknas i {filnamn}")
    
    df['gender'] = df['PersonNr'].apply(busavsjo_berakna_koen)
    df.to_excel(filvag, index=False)
    print(f"Kön tillagd i: {filnamn}")

if __name__ == "__main__":
    filer = ["betyg_ak6_med_merit.xlsx", "betyg_ak9_med_merit.xlsx"]
    for fil in filer:
        bearbeta_fil(fil)
