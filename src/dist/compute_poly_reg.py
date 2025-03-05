import os
import json5
import pandas as pd
import numpy as np

# Paths
config_file = "apikey-crypto.json"
asset_file = "../view/output/asset.txt"
polyreg_file = "../view/output/polyreg.txt"

# Load configuration
try:
    with open(config_file, 'r') as file:
        config = json5.load(file)
        ema_days = config.get("ema_days", 5)  # Default to 5 days if not specified
except FileNotFoundError:
    print(f"Configuration file {config_file} not found.")
    exit(1)

# Read asset data
try:
    asset_data = pd.read_csv(asset_file, header=None, names=["Timestamp", "Price"])
    asset_data["Timestamp"] = pd.to_numeric(asset_data["Timestamp"])  # Ensure timestamps are numeric
    asset_data = asset_data.sort_values(by="Timestamp")  # Ensure data is sorted by timestamp
    asset_data["Datetime"] = pd.to_datetime(asset_data["Timestamp"], unit="s")
except FileNotFoundError:
    print(f"Asset file {asset_file} not found.")
    exit(1)

# Polynomial regression
degree = 2  # you can change this to any degree you want to experiment with
x = asset_data["Timestamp"].values
y = asset_data["Price"].values

# Fit polynomial
coeffs = np.polyfit(x, y, degree)
poly_func = np.poly1d(coeffs)

# Generate predictions
y_pred = poly_func(x)

# Write polynomial regression results to polyreg.txt
os.makedirs(os.path.dirname(polyreg_file), exist_ok=True)
with open(polyreg_file, 'w') as f:
    for timestamp_val, pred_val in zip(x, y_pred):
        f.write(f"{int(timestamp_val)},{pred_val:.2f}\n")

print(f"Polynomial regression predictions saved to {polyreg_file}")
