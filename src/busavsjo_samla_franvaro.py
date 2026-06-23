import xlrd
import xlwt
from config_paths import RAW_FRANVARO_DIR, OUTPUT_DIR, LASAR


def busavsjo_samla_franvarorapporter():
    """
    Slår ihop alla .xls-filer i ``data/raw/franvaro/<läsår>`` till en fil
    (``data/output/<läsår>/franvaro.xls``),
    behåller bara rubriken från första filen och hoppar över de fyra första raderna i resten.
    """
    indata_mapp = RAW_FRANVARO_DIR
    output_fil = OUTPUT_DIR / "franvaro.xls"

    wb_out = xlwt.Workbook()
    ws_out = wb_out.add_sheet("Data")

    rad_index = 0
    antal_filer = 0

    for filväg in sorted(indata_mapp.iterdir()):
        if filväg.suffix == ".xls" and filväg.name != "franvaro.xls":
            try:
                wb_in = xlrd.open_workbook(filväg)
                sheet = wb_in.sheet_by_index(0)

                start_row = 0 if antal_filer == 0 else 4  # behåll rubrik bara från första filen

                # Infoga filnamn som kommentarrad (om inte första filen)
                if antal_filer > 0:
                    ws_out.write(rad_index, 0, f"Från fil: {filväg.name}")
                    rad_index += 1

                for row_idx in range(start_row, sheet.nrows):
                    for col_idx, cell in enumerate(sheet.row_values(row_idx)):
                        ws_out.write(rad_index, col_idx, str(cell))
                    rad_index += 1

                antal_filer += 1

            except Exception as e:
                print(f"⚠️ Kunde inte läsa {filväg.name}: {e}")

    wb_out.save(output_fil)
    print(f"✔️ Skapade '{output_fil}' med {antal_filer} rapporter")


if __name__ == "__main__":
    busavsjo_samla_franvarorapporter()
