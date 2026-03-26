import pandas as pd
import os
import diyepw

years = list(range(1970, 2025, 1))
wmo_list = [744860]   # add more if needed

print(years)

for year in years:
    for wmo in wmo_list:
        try:
            diyepw.create_amy_epw_files_for_years_and_wmos(
                [year],
                [wmo],
                max_records_to_interpolate=10,
                max_missing_amy_rows=300,
                allow_downloads=True,
                amy_epw_dir='Y:\\DIY_EPW\\newyork_jk'
            )
            print(f"Success: WMO {wmo}, Year {year}")
        except Exception as e:
            print(f"Skipped: WMO {wmo}, Year {year} -> {e}")
