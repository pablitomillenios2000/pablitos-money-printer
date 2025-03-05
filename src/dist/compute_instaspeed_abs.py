import pandas as pd
import numpy as np

POLYREG_FILE = "../view/output/polyreg.txt"
POLYACC_FILE = "../view/output/polyacc_abs.txt"

# 1. Load the polyreg data
df = pd.read_csv(POLYREG_FILE, header=0, names=["Timestamp", "LSMA"])

# 2. Drop rows with missing LSMA
df = df.dropna(subset=["LSMA"])

# 3. Convert Timestamp to numeric and sort by Timestamp
df["Timestamp"] = pd.to_numeric(df["Timestamp"])
df = df.sort_values(by="Timestamp").reset_index(drop=True)

# 4. Calculate acceleration
df["Acceleration"] = df["LSMA"].diff() / df["LSMA"] * 1000

# 5. Take absolute value, drop NaN rows
acc_result = abs(df.dropna(subset=["Acceleration"])[["Timestamp", "Acceleration"]])

# 6. Categorize acceleration: if > 1.5 then 4, else keep it
acc_result["Acceleration"] = acc_result["Acceleration"].apply(lambda x: 4 if x > 1.5 else x)

# 7. Write categorized acceleration to the output file without headers or index
acc_result.to_csv(POLYACC_FILE, index=False, header=False)

print(f"Categorized acceleration values have been saved to {POLYACC_FILE}.")
