import os
import json5
import pandas as pd

# Paths
config_file = "apikey-crypto.json"
asset_file = "../view/output/asset.txt"
ema_file = "../view/output/expma.txt"
slope_file = "../view/output/ema_slopes.txt"

# Ensure the output directory exists
os.makedirs(os.path.dirname(ema_file), exist_ok=True)

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
    # Convert Timestamp to human-readable datetime
    asset_data["Datetime"] = pd.to_datetime(asset_data["Timestamp"], unit="s")
except FileNotFoundError:
    print(f"Asset file {asset_file} not found.")
    exit(1)

# Calculate EMA
try:
    asset_data["EMA"] = asset_data["Price"].ewm(span=ema_days, adjust=False).mean()
except Exception as e:
    print(f"Error calculating EMA: {e}")
    exit(1)

# Write EMA to output file
try:
    asset_data[["Timestamp", "EMA"]].to_csv(ema_file, index=False, header=False)
    print(f"Exponential Moving Average (EMA) written to {ema_file}.")
except Exception as e:
    print(f"Error writing EMA to output file {ema_file}: {e}")
    exit(1)

# Calculate slopes of the EMA
try:
    asset_data["EMA_Slope"] = asset_data["EMA"].diff()  # Calculate the difference between consecutive EMA values
except Exception as e:
    print(f"Error calculating EMA slopes: {e}")
    exit(1)

# Write slopes to the slope file, including a human-readable datetime column
try:
    asset_data[["Timestamp", "EMA_Slope", "Datetime"]].dropna().to_csv(
        slope_file, index=False, header=False
    )
    print(f"EMA slopes written to {slope_file} with human-readable datetime.")
except Exception as e:
    print(f"Error writing EMA slopes to output file {slope_file}: {e}")
    exit(1)
