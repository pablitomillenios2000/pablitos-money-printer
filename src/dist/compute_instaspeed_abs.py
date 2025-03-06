import pandas as pd
import numpy as np

ASSET_FILE   = "../view/output/asset.txt"
POLYREG_FILE = "../view/output/polyreg.txt"
POLYACC_FILE = "../view/output/polyacc_abs.txt"

# 1. Load asset data
df_asset = pd.read_csv(ASSET_FILE, header=0, names=["Timestamp", "AssetValue"])
# Convert Timestamp to numeric
df_asset["Timestamp"] = pd.to_numeric(df_asset["Timestamp"], errors="coerce")
# Drop any rows with invalid numeric timestamp
df_asset = df_asset.dropna(subset=["Timestamp"])
# Sort just to be sure (optional, but good practice)
df_asset = df_asset.sort_values(by="Timestamp").reset_index(drop=True)

# 2. Load polyreg data
df = pd.read_csv(POLYREG_FILE, header=0, names=["Timestamp", "LSMA"])

# 3. Drop rows with missing LSMA
df = df.dropna(subset=["LSMA"])

# 4. Convert Timestamp to numeric and sort by Timestamp
df["Timestamp"] = pd.to_numeric(df["Timestamp"], errors="coerce")
df = df.dropna(subset=["Timestamp"])
df = df.sort_values(by="Timestamp").reset_index(drop=True)

# 5. Calculate acceleration
df["Acceleration"] = df["LSMA"].diff() / df["LSMA"] * 1000

# 6. Drop NaN rows (the first row for which we cannot compute acceleration)
df = df.dropna(subset=["Acceleration"])

# 7. Filter to keep timestamps where |Acceleration| >= 1.5
df_filtered = df.loc[df["Acceleration"].abs() >= 1.5, ["Timestamp", "Acceleration"]]

# 8. Merge with asset data on Timestamp (inner join) 
#    so that only timestamps present in both dataframes remain
merged = pd.merge(df_filtered, df_asset, on="Timestamp", how="inner")

# 9. We only need to output Timestamp and AssetValue 
output = merged[["Timestamp", "AssetValue"]]

# 10. Write to the output file without headers or index
output.to_csv(POLYACC_FILE, index=False, header=False)

print(f"Filtered asset values have been saved to {POLYACC_FILE}.")
