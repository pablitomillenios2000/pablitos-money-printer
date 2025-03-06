import pandas as pd
import numpy as np

THRESHOLD           = 1.5  # <-- Added threshold for filtering
POLYREG_FILE        = "../view/output/polyreg.txt"
POLYACC_FILE_UP     = "../view/output/polyacc_abs_up.txt"
POLYACC_FILE_DOWN   = "../view/output/polyacc_abs_down.txt"

# 1. Load polyreg data
df = pd.read_csv(POLYREG_FILE, header=0, names=["Timestamp", "LSMA"])

# 2. Drop rows with missing LSMA
df = df.dropna(subset=["LSMA"])

# 3. Convert Timestamp to numeric and sort by Timestamp
df["Timestamp"] = pd.to_numeric(df["Timestamp"], errors="coerce")
df = df.dropna(subset=["Timestamp"])
df = df.sort_values(by="Timestamp").reset_index(drop=True)

# 4. Calculate acceleration
df["Acceleration"] = df["LSMA"].diff() / df["LSMA"] * 1000

# 5. Drop NaN rows (the first row for which we cannot compute acceleration)
df = df.dropna(subset=["Acceleration"])

# 6a. Filter to keep timestamps where Acceleration >= THRESHOLD
df_up = df.loc[df["Acceleration"] >= THRESHOLD, ["Timestamp", "LSMA"]]

# 6b. Filter to keep timestamps where Acceleration <= -THRESHOLD
df_down = df.loc[df["Acceleration"] <= -THRESHOLD, ["Timestamp", "LSMA"]]

# 7. Write to the respective output files without headers or index
df_up.to_csv(POLYACC_FILE_UP, index=False, header=False)
df_down.to_csv(POLYACC_FILE_DOWN, index=False, header=False)

print(f"Filtered polyreg values (LSMA) for acceleration >= +{THRESHOLD} have been saved to {POLYACC_FILE_UP}.")
print(f"Filtered polyreg values (LSMA) for acceleration <= -{THRESHOLD} have been saved to {POLYACC_FILE_DOWN}.")
