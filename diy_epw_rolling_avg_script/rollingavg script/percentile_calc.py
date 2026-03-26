
import pandas as pd
import numpy as np
import os
# Path to your file with rolling averages
input_file = "Y:/DIY_EPW/Results_AllWMOS/Rochester/output_with_weekly_rolling.csv"


# Excel's PERCENTILE.EXC implementation
def percentile_exc(series, q):
    arr = series.dropna().sort_values().to_numpy()
    n = len(arr)
    if n < 2:
        return np.nan
    # Excel EXC definition
    rank = q * (n + 1)
    if rank < 1 or rank > n:
        return np.nan  # out of bounds
    k = int(np.floor(rank))
    d = rank - k
    return arr[k-1] + d * (arr[k] - arr[k-1])

df = pd.read_csv(input_file)

dbt_col = "first of rolling avg dbt"
hi_col = "first of rolling avg HI"
date_col = "first rolling avg date"  

dbt_values = df[dbt_col].dropna()
hi_values = df[hi_col].dropna()

percentiles = {
    "DBT_99.6": (dbt_col, 0.004),
    "DBT_99":  (dbt_col, 0.01),
    "HI_1":     (hi_col, 0.99),
    "HI_0.4":   (hi_col, 0.996),
}

results = {}

for label, (col, q) in percentiles.items():
    series = df[col].dropna()
    pval = round(percentile_exc(series, q), 2)
    
    # Find closest value in series
    idx = (series - pval).abs().idxmin()
    date_val = df.loc[idx, date_col]
    
    results[label + "_value"] = pval
    results[label + "_date"] = date_val

# ----------------------------
# Print and save results
# ----------------------------
input_dir = os.path.dirname(input_file)
out_file = os.path.join(input_dir, "extreme_weeks.csv")

for k, v in results.items():
    print(f"{k}: {v}")


pd.DataFrame([results]).to_csv(out_file, index=False)
print(f" Saved percentile values with dates to: {out_file}")
