
# Phius Resilience Weather Generator v26.1.0

This tool has been developed by Phius to generate weather data to be used in thermal resilience simulation. It searches through the historical record available in the NOAA ISD (from 1970 to present) and generates a dataframe of the entire historical record. 

It searches for user-defined nth-year return temperatures for summer and winter, filtering for weeks where the peak temperature is ±0.5°C from the input temperature. The tie-breaking element in winter is to identify a week with the lowest average global horizontal radiation; for summer, it is the highest average heat index. These extreme design weeks are then extracted and merged into a user-input base EPW weather file that can be used in simulations.

## Getting Started (For Standard Users)

The easiest way to use the Phius Resilience Weather Generator is to download the standalone executable. You do not need to install Python.

1. Go to the **[Releases](../../releases)** page on this GitHub repository.
2. Download the latest `weather_app.exe` file.
3. Double-click the `.exe` to launch the terminal UI. *(Note: Windows may show a "Windows protected your PC" warning since the publisher is unrecognized. Click "More info" -> "Run anyway").*

## Building and Running from Source (For Developers)

If you want to run the Python script directly or build your own executable, follow these steps:

### Prerequisites
* Python 3.9 or higher
* Git
* 
## Getting Started (For Developers)

 1. Clone the Repository
```
git clone [https://github.com/Phius-ResearchComittee/ClimateData.git](https://github.com/Phius-ResearchComittee/ClimateData.git)
cd ClimateData/weather_app
```

2. Install Dependencies
It is recommended to use a virtual environment. Install the required packages using pip:
```
pip install pandas textual diyepw pythermalcomfort pyinstaller
```

3. Run the Application
Run the script directly via your terminal:
```
python weather_app.py
```
