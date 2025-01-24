import os
import json5
from collections import deque
from datetime import datetime, timedelta

# Define file paths 
api_key_file = "apikey-crypto.json"
asset_file = "../view/output/asset.txt"
trades_file = "../view/output/trades.txt"
slope_file = "../view/output/ema_slopes.txt"
slope_file_micro = "../view/output/ema_slopes_micro.txt"

# Trading parameters
SLOPE_WINDOW_SIZE = 400
positive_slope_limit = 0
negative_slope_limit = 0

ema_micro_sl_slope_limit = -0.45
ema_micro_sl_slope_limit2 = -0.025  # Secondary stop-loss limit
buying_pause_length_hours = 168  # One week pause period
mstl_pause_length_hours = 72  # Example: 3-day pause after "mstl"
ema_micro_compute_time_minutes = 7  # Average micro EMA over the last 7 minutes

print("Writing Slope-Based Trades")

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

# Read micro EMA slope data
with open(slope_file_micro, "r") as f:
    slope_micro_data = {line.strip().split(",")[0]: float(line.strip().split(",")[1]) for line in f}

# Initialize variables for trading
in_market = False  # Whether we currently hold the asset
trades = []  # Store trades
slope_window = deque(maxlen=SLOPE_WINDOW_SIZE)  # Rolling window to calculate average slope
slope_micro_window = deque()  # New deque for micro EMA slopes over 7 minutes
last_sell_time = None  # Time of the last sell trade
last_mstl_time = None  # Time of the last "mstl" trade

# Function to check if we are in the pause period
def is_in_pause(current_time):
    global last_sell_time, last_mstl_time
    if last_sell_time is not None and current_time < last_sell_time + timedelta(hours=buying_pause_length_hours):
        return True
    if last_mstl_time is not None and current_time < last_mstl_time + timedelta(hours=mstl_pause_length_hours):
        return True
    return False

# Process each asset price and its slopes
for timestamp, price in asset_data:
    price = float(price)
    timestamp_int = int(timestamp)
    timestamp_dt = datetime.fromtimestamp(timestamp_int)

    # Get the slopes for the current timestamp
    slope = slope_data.get(timestamp, None)
    slope_micro = slope_micro_data.get(timestamp, None)
    if slope is None or slope_micro is None:
        continue  # Skip processing if any slope is not available

    # Update the rolling window of slopes
    slope_window.append(slope)

    # Update the slope_micro_window with the current slope_micro
    slope_micro_window.append((timestamp_dt, slope_micro))

    # Remove any entries older than 7 minutes
    cutoff_time = timestamp_dt - timedelta(minutes=ema_micro_compute_time_minutes)
    while slope_micro_window and slope_micro_window[0][0] < cutoff_time:
        slope_micro_window.popleft()

    # Calculate the average of slope_micro over the last 7 minutes
    if slope_micro_window:
        avg_slope_micro = sum(s[1] for s in slope_micro_window) / len(slope_micro_window)
    else:
        avg_slope_micro = None  # No data to compute average

    # Calculate the average slope over the last window (if we have enough data)
    if len(slope_window) == SLOPE_WINDOW_SIZE:
        avg_slope = sum(slope_window) / len(slope_window)

        # Sell condition based on average of micro EMA slope (primary stop-loss)
        if in_market and avg_slope_micro is not None and avg_slope_micro < ema_micro_sl_slope_limit:
            trades.append((timestamp, "sell", "stl"))
            in_market = False
            last_sell_time = timestamp_dt  # Start the general pause period

        # Sell condition based on average of micro EMA slope (secondary stop-loss)
        elif in_market and avg_slope_micro is not None and avg_slope_micro < ema_micro_sl_slope_limit2:
            trades.append((timestamp, "sell", "mstl"))
            in_market = False
            last_mstl_time = timestamp_dt  # Start the "mstl" pause period

        # Sell condition based on average slope
        elif in_market and avg_slope <= negative_slope_limit:
            trades.append((timestamp, "sell", "slope"))
            in_market = False

        # Buy condition
        elif not in_market and avg_slope > positive_slope_limit and not is_in_pause(timestamp_dt):
            trades.append((timestamp, "buy", "slope"))
            in_market = True

# Write trades to the output file with the reason
with open(trades_file, "w") as f:
    for timestamp, action, reason in trades:
        f.write(f"{timestamp},{action},{reason}\n")