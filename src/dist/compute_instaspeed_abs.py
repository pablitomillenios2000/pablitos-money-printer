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

# 4. Calculate acceleration (no absolute value so we can retain sign)
df["Acceleration"] = df["LSMA"].diff() / df["LSMA"] * 1000

# 5. Drop NaN rows (the first row for which we cannot compute acceleration)
acc_result = df.dropna(subset=["Acceleration"])[["Timestamp", "Acceleration"]]

# 6. Categorize acceleration
def categorize_acc(x):
    if x <= -1.5:
        return -4
    elif x >= 1.5:
        return 4
    else:
        return "---"

acc_result["Acceleration"] = acc_result["Acceleration"].apply(categorize_acc)

# 7. Write categorized acceleration to the output file without headers or index
acc_result.to_csv(POLYACC_FILE, index=False, header=False)

print(f"Categorized acceleration values have been saved to {POLYACC_FILE}.")
