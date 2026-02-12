import diyepw
import os
from urllib.error import HTTPError

def run_for_wmo(years, wmo, outdir):
    os.makedirs(outdir, exist_ok=True)
    try:
        result = diyepw.create_amy_epw_files_for_years_and_wmos(
            years,
            [wmo],
            max_records_to_interpolate=100,
            max_records_to_impute=50,
            max_missing_amy_rows=50,
            allow_downloads=True,
            amy_epw_dir=outdir,
        )
        print("Success:\n", result)
    except HTTPError as e:
        print(f"HTTPError: code={getattr(e,'code','N/A')} url={getattr(e,'filename','N/A')}")
    except Exception as e:
        print("ERROR:", e)


if __name__ == '__main__':
    years = [2024, 2025]
    wmo = 725280
    outdir = r"C:\Users\amitc_crl\OneDrive\Documents\GitHub\ClimateData\AMY Generation\test_output_725280"
    run_for_wmo(years, wmo, outdir)
