import os
import json5
from collections import deque

# Define file paths 
api_key_file = "apikey-crypto.json"
asset_file = "../view/output/asset.txt"
trades_file = "../view/output/trades.txt"
slope_file = "../view/output/ema_slopes.txt"

# Trading parameters
SLOPE_WINDOW_SIZE = 400
TRAILING_STOP_PERCENTAGE = 0.90  # 7% trailing stop loss
positive_slope_limit = 0
negative_slope_limit = 0

# Ensure the output directory exists
os.makedirs(os.path.dirname(trades_file), exist_ok=True)

# Read the API key JSON file for configuration values
with open(api_key_file, "r") as f:
    api_data = json5.load(f)

# Read asset data
with open(asset_file, "r") as f:
    asset_data = [line.strip().split(",") for line in f]

# Read slope data
with open(slope_file, "r") as f:
    slope_data = {line.strip().split(",")[0]: float(line.strip().split(",")[1]) for line in f}

# Initialize variables for trading
in_market = False                   # Whether we currently hold the asset
trades = []                         # Store trades
slope_window = deque(maxlen=SLOPE_WINDOW_SIZE)  # Rolling window to calculate average slope
highest_price = None                # Track the highest price after buying

# Process each asset price and its slope
for timestamp, price in asset_data:
    price = float(price)
    
    # Get the slope for the current timestamp
    slope = slope_data.get(timestamp, None)
    if slope is None:
        continue  # Skip processing if slope is not available

    # Update the rolling window of slopes
    slope_window.append(slope)
    
    # Trailing stop loss logic
    if in_market:
        # Update the highest price
        if highest_price is None or price > highest_price:
            highest_price = price

        # Check for a drop from the highest price
        if price <= highest_price * (1 - TRAILING_STOP_PERCENTAGE):
            # Sell due to trailing stop loss
            trades.append((timestamp, "sell", "stl"))
            in_market = False
            highest_price = None  # Reset the highest price
            continue  # Skip further processing to avoid multiple actions

    # Calculate the average slope over the last window (if we have enough data)
    if len(slope_window) == SLOPE_WINDOW_SIZE:
        avg_slope = sum(slope_window) / len(slope_window)

        # Buy condition
        if avg_slope > positive_slope_limit and not in_market:
            trades.append((timestamp, "buy", "slope"))
            in_market = True
            highest_price = price  # Initialize highest price after buying

        # Sell condition
        elif avg_slope <= negative_slope_limit and in_market:
            trades.append((timestamp, "sell", "slope"))
            in_market = False
            highest_price = None  # Reset the highest price

# Write trades to the output file with the reason
with open(trades_file, "w") as f:
    for timestamp, action, reason in trades:
        f.write(f"{timestamp},{action},{reason}\n")