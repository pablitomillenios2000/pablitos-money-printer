import os
import json5
import pandas as pd
import numpy as np

# ---------------------
# File paths
# ---------------------
CONFIG_FILE = "apikey-crypto.json"
ASSET_FILE = "../view/output/asset.txt"
SLOPE_FILE = "../view/output/pricediff.txt"

# Create output directory if needed
os.makedirs(os.path.dirname(SLOPE_FILE), exist_ok=True)

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
# Calculate rolling difference
# ---------------------
# Diff of 1 period (i.e., current price - previous price)
asset_data["PriceDiff"] = asset_data["Price"].diff(periods=1)

# ---------------------
# Save to output file
# ---------------------
# Drop the first row which will have a NaN difference, then save Timestamp and PriceDiff
diff_data = asset_data.dropna(subset=["PriceDiff"])[["Timestamp", "PriceDiff"]]
diff_data.to_csv(SLOPE_FILE, index=False, header=False)

print(f"Rolling price differences have been saved to {SLOPE_FILE}.")
