import os
import pandas as pd

# Paths
config_file = "apikey-crypto.json"
asset_file = "../view/output/asset.txt"
sma_file = "../view/output/simple_ma.txt"
slope_file = "../view/output/simple_ma_slope.txt"

# Parameters
sma_window = 60000  # Configure the SMA window size

# Ensure the asset file exists
if not os.path.exists(asset_file):
    raise FileNotFoundError(f"The file {asset_file} does not exist.")

# Read asset data
try:
    df = pd.read_csv(
        asset_file,
        header=None,
        names=["timestamp", "price"],
        dtype={"timestamp": int, "price": float}
    )
except Exception as e:
    raise ValueError(f"Error reading {asset_file}: {e}")

# Sort by timestamp if it's not already sorted
df.sort_values("timestamp", inplace=True)

# Calculate SMA
df["sma"] = df["price"].rolling(window=sma_window).mean()

# Prepare SMA output
sma_df = df.dropna(subset=["sma"])[["timestamp", "sma"]]

# Write SMA with no scientific notation and 12 decimal places
sma_df.to_csv(sma_file, index=False, header=False, float_format='%.12f')
print(f"Simple Moving Average calculated and saved to {sma_file}.")

# Calculate slope as d(SMA)/d(Time)
df["slope"] = df["sma"].diff() / df["timestamp"].diff()

# Prepare slope output
slope_df = df.dropna(subset=["slope"])[["timestamp", "slope"]]

# Write slope with no scientific notation and 12 decimal places
slope_df.to_csv(slope_file, index=False, header=False, float_format='%.12f')
print(f"SMA slope calculated and saved to {slope_file}.")
