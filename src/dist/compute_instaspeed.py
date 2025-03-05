import pandas as pd
import numpy as np

POLYREG_FILE = "../view/output/polyreg.txt"
POLYACC_FILE = "../view/output/polyacc.txt"

# 1. Load the polyreg data
#    First line has headers "Timestamp,LSMA", so we use header=0
df = pd.read_csv(POLYREG_FILE, header=0, names=["Timestamp", "LSMA"])

# 2. Drop rows with missing LSMA
df = df.dropna(subset=["LSMA"])

# Make sure Timestamp is numeric
df["Timestamp"] = pd.to_numeric(df["Timestamp"])

# 3. Sort by Timestamp (in case file isn't strictly ordered)
df = df.sort_values(by="Timestamp").reset_index(drop=True)

# 4. Calculate acceleration:
#    acceleration[i] = (LSMA[i] - LSMA[i-1]) / LSMA[i]
df["Acceleration"] = df["LSMA"].diff() / df["LSMA"] * 1000

# 5. Drop the first row where Acceleration is NaN
acc_result = df.dropna(subset=["Acceleration"])[["Timestamp", "Acceleration"]]

# 6. Write acceleration to polyacc.txt without headers or index
acc_result.to_csv(POLYACC_FILE, index=False, header=False)

print(f"Acceleration values have been saved to {POLYACC_FILE}.")
