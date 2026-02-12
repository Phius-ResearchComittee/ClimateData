import diyepw
from urllib.error import HTTPError
from datetime import datetime


def generate_epw(wmo_number, year, folder_path):
    try:
        wmo_int = int(wmo_number)
    except ValueError:
        print(f"Invalid WMO number: {wmo_number}")
        return False

    try:
        year_int = int(year)
    except ValueError:
        print(f"Invalid year: {year}")
        return False

    current_year = datetime.now().year
    if not (1800 <= year_int <= current_year):
        print(f"Year {year_int} out of expected range (1800-{current_year}).")
        return False

    try:
        diyepw.create_amy_epw_files_for_years_and_wmos(
            [year_int],
            [wmo_int],
            max_records_to_interpolate=100,
            max_records_to_impute=50,
            max_missing_amy_rows=50,
            allow_downloads=True,
            amy_epw_dir=str(folder_path),
        )
    except HTTPError as e:
        print(f"Network Error: Unable to download data from NOAA ({getattr(e,'code', 'N/A')})")
        print(f"URL: {getattr(e,'filename', 'N/A')}")
        print("This could mean:")
        print("  1. The NOAA server is temporarily unavailable")
        print("  2. The data for this WMO/year combination doesn't exist")
        print("  3. Your internet connection may be blocked by a firewall")
        return False
    except Exception as e:
        print(f"Error generating EPW: {e}")
        return False

    return True


# Beginning of the program

folder_path = input("Type in the folder path to save the EPW file: ")

while True:
    # try:
    wmo_number = input("Type in WMO Number (or 'exit' to quit): ")
    if wmo_number.lower() == 'exit':
        break

    year = input("Type in the year for the AMY EPW file: ")
    success = generate_epw(wmo_number, year, folder_path)
    if success:
        print(f"AMY EPW file generated successfully for WMO number {wmo_number} and year {year}.")
    else:
        print(f"Failed to generate AMY EPW for WMO {wmo_number} year {year}.")
    
    
    
    # except ValueError:
    #     print("Invalid input. Please enter a valid WMO number or 'exit' to quit.")
    #     continue