import os
import json5
import pandas as pd
import numpy as np

# ---------------------
# File paths
# ---------------------
CONFIG_FILE = "apikey-crypto.json"
ASSET_FILE = "../view/output/asset.txt"
INSTASPEED_FILE = "../view/output/instaspeed.txt"

# Create output directory if needed
os.makedirs(os.path.dirname(INSTASPEED_FILE), exist_ok=True)

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
# Calculate Instantaneous Speed
# ---------------------
# Percentage change from previous price
asset_data["InstantaneousSpeed"] = asset_data["Price"].pct_change() * 100

# Optional: Amplify and log the speed
amplification_factor = 10
asset_data["AmplifiedSpeed"] = asset_data["InstantaneousSpeed"] * amplification_factor

def symmetric_log(x, small_value=1e-6):
    return np.sign(x) * np.log1p(np.abs(x) + small_value)

asset_data["LogAmplifiedSpeed"] = symmetric_log(asset_data["AmplifiedSpeed"])

# ---------------------
# Save to instaspeed.txt
# ---------------------
# You can choose which speed to save. Let's save the LogAmplifiedSpeed.
asset_data[["Timestamp", "LogAmplifiedSpeed"]].dropna().to_csv(
    INSTASPEED_FILE, header=False, index=False, float_format="%.8f"
)

print(f"Instantaneous speed saved to {INSTASPEED_FILE}")
