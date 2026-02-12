import diyepw
import os
from pathlib import Path
from urllib.error import HTTPError
from datetime import datetime

def generate_epw(wmo_number, year, folder_path):
    # Ensure folder exists
    output_dir = Path(folder_path)
    if not output_dir.exists():
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Error creating directory: {e}")
            return False

    try:
        wmo_int = int(wmo_number)
        year_int = int(year)
    except ValueError:
        print("Invalid WMO or Year format.")
        return False

    current_year = datetime.now().year
    if not (1800 <= year_int <= current_year):
        print(f"Year {year_int} is out of range.")
        return False

    try:
        # diyepw handles the download and transformation
        diyepw.create_amy_epw_files_for_years_and_wmos(
            [year_int],
            [wmo_int],
            max_records_to_interpolate=100,
            max_records_to_impute=50,
            max_missing_amy_rows=50,
            allow_downloads=True,
            amy_epw_dir=str(output_dir),
        )
        return True
    except HTTPError as e:
        print(f"Network Error: NOAA data likely unavailable for WMO {wmo_int} in {year_int}.")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

# Main Execution
folder_input = input("Enter output folder path: ").strip()

while True:
    wmo_input = input("\nEnter WMO Number (or 'exit'): ").strip()
    if wmo_input.lower() == 'exit':
        break
    
    year_input = input("Enter Year: ").strip()
    
    if generate_epw(wmo_input, year_input, folder_input):
        print(f"--- Success! Check {folder_input} for your file. ---")
    else:
        print(f"--- Generation failed for {wmo_input}. ---")