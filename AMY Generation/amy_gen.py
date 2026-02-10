import diyepw
from urllib.error import HTTPError

def generate_epw(wmo_number, year, folder_path):
    try:
        diyepw.create_amy_epw_file(
        [int(wmo_number)],
        [int(year)], 
        max_records_to_interpolate=100, 
        max_records_to_impute=50, 
        max_missing_amy_rows=50, 
        allow_downloads=True,
        amy_epw_dir=str(folder_path)
        )
    except HTTPError as e:
        print(f"Network Error: Unable to download data from NOAA ({e.code})")
        print(f"URL: {e.filename}")
        print("This could mean:")
        print("  1. The NOAA server is temporarily unavailable")
        print("  2. The data for this WMO/year combination doesn't exist")
        print("  3. Your internet connection may be blocked by a firewall")
        raise


# Beginning of the program

folder_path = input("Type in the folder path to save the EPW file: ")

while True:
    # try:
    wmo_number = input("Type in WMO Number (or 'exit' to quit): ")
    if wmo_number.lower() == 'exit':
        break

    year = input("Type in the year for the AMY EPW file: ")
    generate_epw(wmo_number, year, folder_path)
    print(f"AMY EPW file generated successfully for WMO number {wmo_number} and year {year}.")
    
    
    
    # except ValueError:
    #     print("Invalid input. Please enter a valid WMO number or 'exit' to quit.")
    #     continue