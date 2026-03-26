import os
import pandas as pd
from pythermalcomfort.models import heat_index_rothfusz
import matplotlib.pyplot as plt
import seaborn as sns

# -----------------------------
# 1. Combine all CSV files
# -----------------------------
input_dir = 'Y:/DIY_EPW/newyork_jk'  # Directory containing CSV files
output_csv = "Y:/DIY_EPW/results_new/newyork_jk/output_with_weekly_rolling.csv"

# --- NEW: Check if output directory exists, create if not ---
output_dir = os.path.dirname(output_csv)
if output_dir and not os.path.exists(output_dir):
    try:
        os.makedirs(output_dir, exist_ok=True)
        print(f"Created new directory: {output_dir}")
    except OSError as e:
        print(f"Error creating directory {output_dir}: {e}")
# -----------------------------------------------------------

all_dataframes = []

for filename in os.listdir(input_dir):
    if filename.endswith('.csv'):
        filepath = os.path.join(input_dir, filename)
        try:
            # Read file, skip first 18 rows
            df = pd.read_csv(filepath, skiprows=18, encoding='latin1')
            df['SourceFile'] = filename  # Track origin (optional)
            all_dataframes.append(df)
            print(f"Processed: {filename}")
        except Exception as e:
            print(f" Error processing {filename}: {e}")

if not all_dataframes:
    raise RuntimeError("No valid CSV files found!")

combined_df = pd.concat(all_dataframes, ignore_index=True)

# -----------------------------
# 2. Compute Heat Index
# -----------------------------
cols_to_keep = [
    "Date",
    "HH:MM",
    "Dry Bulb Temperature {C}",
    "Dew Point Temperature {C}",
    "Relative Humidity {%}",
    "Global Horizontal Radiation {Wh/m2}",
]

df = combined_df[cols_to_keep].dropna().copy()

hi_list = []
for _, row in df.iterrows():
    tdb = row["Dry Bulb Temperature {C}"]
    rh = row["Relative Humidity {%}"]
    try:
        result = heat_index_rothfusz(tdb=tdb, rh=rh)
        hi_list.append(result["hi"])
    except Exception:
        hi_list.append(None)

df['Heat Index'] = hi_list

# -----------------------------
# 3. Rolling weekly averages
# -----------------------------
db_temp_col = "Dry Bulb Temperature {C}"
dp_temp_col = "Dew Point Temperature {C}"
heat_index = "Heat Index"
global_hor_rad = "Global Horizontal Radiation {Wh/m2}"

rolling_db_temp = "rolling average DBt"
rolling_dp_temp = "rolling average DPt"
rolling_heat_index = "rolling heat index"
rolling_GHR = "rolling GHR"

#------------------------
rolling_max_dbt = "rolling max DBt"
rolling_min_dbt = "rolling min DBt"
rolling_max_dpt = "rolling max DPt"
rolling_min_dpt = "rolling min DPt"
first_rolling_max_dbt = "first of rolling max DBt"
first_rolling_min_dbt = "first of rolling min DBt"
first_rolling_max_dpt = "first of rolling max DPt"
first_rolling_min_dpt = "first of rolling min DPt"
first_dbt_col = "first of rolling avg dbt"
first_dp_col = "first of rolling avg dpt"

first_hi_col = "first of rolling avg HI"
first_ghr_col = "first of rolling avg GHR"
first_date_col = "first rolling avg date"

# Ensure Date is datetime
df["Date"] = pd.to_datetime(df["Date"])
indexer = pd.api.indexers.FixedForwardWindowIndexer(window_size=168)  # 168h = 1 week

df[rolling_db_temp] = df[db_temp_col].rolling(window=indexer, min_periods=1).mean()
df[rolling_dp_temp] = df[dp_temp_col].rolling(window=indexer, min_periods=1).mean()
df[rolling_heat_index] = df[heat_index].rolling(window=indexer, min_periods=1).mean()
df[rolling_GHR] = df[global_hor_rad].rolling(window=indexer, min_periods=1).mean()
df[rolling_max_dbt] = df[db_temp_col].rolling(window=indexer, min_periods=1).max()
df[rolling_min_dbt] = df[db_temp_col].rolling(window=indexer, min_periods=1).min()
df[rolling_max_dpt] = df[dp_temp_col].rolling(window=indexer, min_periods=1).max()
df[rolling_min_dpt] = df[dp_temp_col].rolling(window=indexer, min_periods=1).min()

# Extract first-of-day rolling averages
seen_dates = set()
first_vals_rolling_avg_db, first_vals_rolling_avg_dp, first_vals_heat_index, first_vals_GHR, first_vals_rolling_max_dbt, first_vals_rolling_min_dbt, first_vals_rolling_max_dpt, first_vals_rolling_min_dpt = [], [], [], [], [], [], [], []
first_dates = []

for i, row in df.iterrows():
    day_key = row["Date"].date()
    if day_key not in seen_dates:
        seen_dates.add(day_key)
        first_vals_rolling_avg_db.append(row[rolling_db_temp])
        first_vals_rolling_avg_dp.append(row[rolling_dp_temp])
        first_vals_heat_index.append(row[rolling_heat_index])
        first_vals_GHR.append(row[rolling_GHR])
        first_vals_rolling_max_dbt.append(row[rolling_max_dbt])
        first_vals_rolling_min_dbt.append(row[rolling_min_dbt])
        first_vals_rolling_max_dpt.append(row[rolling_max_dpt])
        first_vals_rolling_min_dpt.append(row[rolling_min_dpt])
        first_dates.append(row["Date"])  # store actual datetime

df[first_dbt_col] = pd.Series(first_vals_rolling_avg_db).reset_index(drop=True)
df[first_dp_col] = pd.Series(first_vals_rolling_avg_dp).reset_index(drop=True)
df[first_hi_col] = pd.Series(first_vals_heat_index).reset_index(drop=True)
df[first_ghr_col] = pd.Series(first_vals_GHR).reset_index(drop=True)
df[first_date_col] = pd.Series(first_dates).reset_index(drop=True)
df[first_rolling_max_dbt]= pd.Series(first_vals_rolling_max_dbt).reset_index(drop=True)
df[first_rolling_min_dbt] = pd.Series(first_vals_rolling_min_dbt).reset_index(drop=True)
df[first_rolling_max_dpt] = pd.Series(first_vals_rolling_max_dpt).reset_index(drop=True)
df[first_rolling_min_dpt] = pd.Series(first_vals_rolling_min_dpt).reset_index(drop=True)

# Save
df.to_csv(output_csv, index=False)
print(f" Final processed dataset saved as: {output_csv}")