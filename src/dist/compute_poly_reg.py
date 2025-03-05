import os
import json5
import pandas as pd
import numpy as np

# ---------------------
# Example parameters
# ---------------------
INPUT_SOURCE_VALUE = "close"         # In your case, you might just read 'Price' from CSV
SMOOTH_DATA_BEFORE_CURVE_FITTING = True
DATA_SMOOTHING_PERIOD = 2          # Rolling window or other smoothing method
REGRESSION_SAMPLE_PERIOD = 20      # How many data points (bars) to include in the regression
POLYNOMIAL_ORDER = 2
REGRESSION_OFFSET = 0                # How many bars into the future you shift the fitted curve
WIDTH_COEFFICIENT = 2                # How wide to draw channel around the fitted curve
FORECAST_FROM_BARS_AGO = 0           # If > 0, we only fit up to some bars_ago and forecast forward
SHOW_FITTED_CURVE = True
SHOW_FITTED_CHANNEL_HIGH = False
SHOW_FITTED_CHANNEL_LOW = False
CURVE_DRAWING_STEP_SIZE = 10         # For generating new points for a smoother line
AUTO_DECIDE_STEP_SIZE_INSTEAD = True # If True, you might let the script decide a step size automatically

# ---------------------
# File paths
# ---------------------
CONFIG_FILE = "apikey-crypto.json"
ASSET_FILE = "../view/output/asset.txt"
POLYREG_FILE = "../view/output/polyreg.txt"

# Create output directory if needed
os.makedirs(os.path.dirname(POLYREG_FILE), exist_ok=True)

# ---------------------
# Load configuration
# ---------------------
try:
    with open(CONFIG_FILE, 'r') as file:
        config = json5.load(file)
        # Example: read some parameters from config if desired
        # EMA_DAYS = config.get("ema_days", 5)
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
    asset_data["Datetime"] = pd.to_datetime(asset_data["Timestamp"], unit="s")
except FileNotFoundError:
    print(f"Asset file {ASSET_FILE} not found.")
    exit(1)

# ---------------------
# Smoothing (optional)
# ---------------------
if SMOOTH_DATA_BEFORE_CURVE_FITTING:
    # Simple rolling average
    asset_data["Smoothed"] = asset_data["Price"].rolling(window=DATA_SMOOTHING_PERIOD, min_periods=1).mean()
    price_col = "Smoothed"
else:
    price_col = "Price"

# ---------------------
# Windowing the data (REGRESSION_SAMPLE_PERIOD)
# ---------------------
# If you want only the last N bars:
if REGRESSION_SAMPLE_PERIOD > 0 and REGRESSION_SAMPLE_PERIOD < len(asset_data):
    recent_data = asset_data.iloc[-REGRESSION_SAMPLE_PERIOD:].copy()
else:
    recent_data = asset_data.copy()

# ---------------------
# Potential partial fit: FORECAST_FROM_BARS_AGO
# ---------------------
# If FORECAST_FROM_BARS_AGO > 0, we pretend the last X bars “don’t exist” for the fit,
# and then forecast them.
fit_data = recent_data.copy()
forecast_data = None

if FORECAST_FROM_BARS_AGO > 0 and FORECAST_FROM_BARS_AGO < len(recent_data):
    cutoff = len(recent_data) - FORECAST_FROM_BARS_AGO
    fit_data = recent_data.iloc[:cutoff].copy()      # Use up to (cutoff-1) for polynomial fitting
    forecast_data = recent_data.iloc[cutoff:].copy() # This chunk will get “predicted”

# ---------------------
# Polynomial regression
# ---------------------
x_fit = fit_data["Timestamp"].values
y_fit = fit_data[price_col].values

# Fit polynomial
coeffs = np.polyfit(x_fit, y_fit, POLYNOMIAL_ORDER)
poly_func = np.poly1d(coeffs)

# Generate polynomial predictions for the portion we fitted
fit_data["PolyFit"] = poly_func(fit_data["Timestamp"])

# ---------------------
# Forecast (if FORECAST_FROM_BARS_AGO > 0)
# ---------------------
if forecast_data is not None:
    forecast_data["PolyFit"] = poly_func(forecast_data["Timestamp"])
    # We can combine them for final output
    all_data = pd.concat([fit_data, forecast_data])
else:
    all_data = fit_data

# ---------------------
# Regression offset
# ---------------------
# If you want to shift the fitted curve forward by some “bars” notion,
# you have to know how big a “bar” is in your timestamp domain.
# A naive approach is to simply add (REGRESSION_OFFSET * bar_spacing)
# to your X-values. But in daily data with 60-second bars, that can be tricky.
# For example, if each bar is 60 seconds, then shifting forward 10 bars = 600 seconds.
if REGRESSION_OFFSET != 0:
    # For demonstration, assume each bar is spaced equally:
    # We'll detect an approximate bar spacing from the last portion of data
    unique_timestamps = np.sort(all_data["Timestamp"].unique())
    if len(unique_timestamps) > 1:
        bar_spacing = np.median(np.diff(unique_timestamps))  # approximate spacing
        shift_seconds = REGRESSION_OFFSET * bar_spacing
        # Shift the predicted curve
        # Option 1: shift the Timestamps used for the polynomial
        # Option 2: shift the final predicted values along the time axis
        # Below, we “shift” timestamps in a new column
        all_data["OffsetTimestamp"] = all_data["Timestamp"] + shift_seconds
    else:
        all_data["OffsetTimestamp"] = all_data["Timestamp"]
else:
    all_data["OffsetTimestamp"] = all_data["Timestamp"]

# ---------------------
# (Optional) Channel computations
# ---------------------
# For a “fitted channel,” you’d typically compute how far each actual point is
# from the fitted curve. Then you might define an upper/lower channel
# as “fitted curve ± (std of residuals * WIDTH_COEFFICIENT).”
residuals = all_data[price_col] - all_data["PolyFit"]
std_resid = np.nanstd(residuals)

all_data["PolyFit_Upper"] = all_data["PolyFit"] + WIDTH_COEFFICIENT * std_resid
all_data["PolyFit_Lower"] = all_data["PolyFit"] - WIDTH_COEFFICIENT * std_resid

# ---------------------
# Drawing step size
# ---------------------
# If you want a smooth curve, you can sample a range of timestamps at intervals
# based on CURVE_DRAWING_STEP_SIZE (seconds, or bars, etc.). The simplest approach:
# 1. Create a new array of X points.
# 2. Evaluate poly_func at those points.
# For demonstration, we do “dense timestamps” from min to max:
if AUTO_DECIDE_STEP_SIZE_INSTEAD:
    # Maybe create 100 new points from min to max:
    num_points = 100
    x_min, x_max = all_data["Timestamp"].min(), all_data["Timestamp"].max()
    X_dense = np.linspace(x_min, x_max, num_points)
else:
    # We'll guess each bar is about “bar_spacing” seconds, so step size * bar_spacing
    # to go from min to max
    bar_spacing = np.median(np.diff(all_data["Timestamp"].unique())) if len(all_data) > 1 else 1
    step_in_seconds = CURVE_DRAWING_STEP_SIZE * bar_spacing
    X_dense = np.arange(all_data["Timestamp"].min(), 
                        all_data["Timestamp"].max() + step_in_seconds, 
                        step_in_seconds)

dense_fit = pd.DataFrame({"Timestamp": X_dense})
dense_fit["PolyFit"] = poly_func(dense_fit["Timestamp"])
dense_fit["OffsetTimestamp"] = dense_fit["Timestamp"]  # or shift if needed
dense_residuals = np.interp(X_dense, all_data["Timestamp"], residuals)  # naive approach
dense_fit["PolyFit_Upper"] = dense_fit["PolyFit"] + WIDTH_COEFFICIENT * np.nanstd(dense_residuals)
dense_fit["PolyFit_Lower"] = dense_fit["PolyFit"] - WIDTH_COEFFICIENT * np.nanstd(dense_residuals)

# ---------------------
# Write out to polyreg.txt
# ---------------------
# For simplicity, we’ll just write the main fitted curve. 
# If you want channels, you could write them as separate columns or separate files.
to_write = dense_fit if SHOW_FITTED_CURVE else all_data

with open(POLYREG_FILE, 'w') as f:
    # Example format:  timestamp,polyfit,channel_hi,channel_lo
    f.write("Timestamp,PolyFit,PolyFit_Upper,PolyFit_Lower\n")
    for i, row in to_write.iterrows():
        # Only write channels if asked
        # (for demonstration, we write them if they exist)
        hi_val = row["PolyFit_Upper"] if SHOW_FITTED_CHANNEL_HIGH else ""
        lo_val = row["PolyFit_Lower"] if SHOW_FITTED_CHANNEL_LOW else ""
        # Format them carefully (some columns might be empty)
        line = f"{int(row['Timestamp'])},{row['PolyFit']:.2f}"
        if SHOW_FITTED_CHANNEL_HIGH:
            line += f",{hi_val:.2f}"
        else:
            line += ","
        if SHOW_FITTED_CHANNEL_LOW:
            line += f",{lo_val:.2f}"
        else:
            line += ","
        line += "\n"
        f.write(line)

print(f"Polynomial regression + optional channel saved to {POLYREG_FILE}")
