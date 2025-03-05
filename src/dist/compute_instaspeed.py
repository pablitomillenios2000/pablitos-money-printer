import os
import json5
import pandas as pd
import numpy as np

# ---------------------
# File paths
# ---------------------
CONFIG_FILE = "apikey-crypto.json"
ASSET_FILE = "../view/output/asset.txt"
ACCEL_FILE = "../view/output/acceleration_.txt"

# Create output directory if needed
os.makedirs(os.path.dirname(ACCEL_FILE), exist_ok=True)

# ---------------------
# Load configuration
# ---------------------
try:
    with open(CONFIG_FILE, 'r') as file:
        config = json5.load(file)
except FileNotFoundError:
    print(f"Configuration file {CONFIG_FILE} not found.")
    exit(1)

# ---------------------
# Read asset data
# ---------------------
try:
    asset_data = pd.read_csv(ASSET_FILE, header=None, names=["Timestamp", "Price"])
    asset_data["Timestamp"] = pd.to_numeric(asset_data["Timestamp"])  # Ensure numeric
    asset_data = asset_data.sort_values(by="Timestamp")              # Sort by time
except FileNotFoundError:
    print(f"Asset file {ASSET_FILE} not found.")
    exit(1)

# ---------------------
# Compute transformed log price
# ---------------------
asset_data["LogPrice"] = np.log(asset_data["Price"])

# ---------------------
# Compute acceleration (second derivative)
# ---------------------
asset_data["Acceleration"] = asset_data["LogPrice"].diff() / asset_data["LogPrice"]  * 10000 / 2 #.diff()

# ---------------------
# Save to output file
# ---------------------
# Drop rows with NaN in Acceleration (first two diffs will be NaN)
accel_data = asset_data.dropna(subset=["Acceleration"])[["Timestamp", "Acceleration"]]

# Write to CSV without header or index
accel_data.to_csv(ACCEL_FILE, index=False, header=False)

print(f"Acceleration values have been saved to {ACCEL_FILE}.")
