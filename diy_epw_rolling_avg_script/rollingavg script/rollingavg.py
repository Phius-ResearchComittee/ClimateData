import os
import pandas as pd
from pythermalcomfort.models import heat_index_rothfusz

# -----------------------------
# 1. Combine all CSV files
# -----------------------------
input_dir = 'Y:/Regan'
combined_file = 'Y:/combined_output_new.csv'
final_file = 'Y:/combined_with_heat_index.csv'

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
            print(f"⚠️ Error processing {filename}: {e}")

# Merge and save intermediate
if not all_dataframes:
    raise RuntimeError("No valid CSV files found!")

combined_df = pd.concat(all_dataframes, ignore_index=True)
combined_df.to_csv(combined_file, index=False)
print(f"✅ Combined CSV saved as: {combined_file}")

# -----------------------------
# 2. Compute Heat Index
# -----------------------------
# Keep only the relevant columns
cols_to_keep = [
    "Date",
    "HH:MM",
    "Dry Bulb Temperature {C}",
    "Relative Humidity {%}",
    "Global Horizontal Radiation {Wh/m2}",
]

df = combined_df[cols_to_keep].dropna().copy()

# Prepare result list
hi_list = []

# Compute heat index for each row
for _, row in df.iterrows():
    tdb = row["Dry Bulb Temperature {C}"]
    rh = row["Relative Humidity {%}"]

    try:
        result = heat_index_rothfusz(tdb=tdb, rh=rh)
        hi_list.append(result["hi"])
    except Exception as e:
        hi_list.append(None)
        print(f"⚠️ Error computing HI (Tdb={tdb}, RH={rh}): {e}")

# Add results
df['Heat Index'] = hi_list

# -----------------------------
# 3. Save final CSV
# -----------------------------
df.to_csv(final_file, index=False)
print(f"✅ Final CSV saved as: {final_file}")
