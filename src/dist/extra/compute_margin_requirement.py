import json5
import os

# Define file paths
api_key_file = "apikey-crypto.json"
MARGIN_FILE = "../view/output/margin.txt"
ASSET_FILE = "../view/output/asset.txt"
TRADES_FILE = "../view/output/trades.txt"
MAINTENANCE_MARGIN_REQUIREMENT = 0.2

# Read the API key JSON file for configuration values
with open(api_key_file, "r") as f:
    api_data = json5.load(f)

# Extract the initial investment value
investment = api_data.get("investment", 0)

# Check for necessary files
if not os.path.exists(TRADES_FILE):
    print("Trades file not found.")
    exit()
if not os.path.exists(ASSET_FILE):
    print("Asset file not found.")
    exit()

# Read trades file (without headers)
with open(TRADES_FILE, "r") as f:
    trades = [line.strip().split(",") for line in f.readlines() if line.strip()]

# Read asset prices (without headers)
with open(ASSET_FILE, "r") as f:
    asset_prices = {int(line.split(",")[0]): float(line.split(",")[1]) for line in f.readlines() if line.strip()}

# Sort asset prices by timestamp
sorted_prices = sorted(asset_prices.items())

# Initialize variables
current_investment = investment
borrowed_amount = 0
margin_points = []
position_size = 0  # Number of assets held

# Helper function to get the closest asset price for a given timestamp
def get_closest_price(timestamp):
    closest_price = None
    for t, price in sorted_prices:
        if t <= timestamp:
            closest_price = price
        else:
            break
    return closest_price

# Process trades
for trade in trades:
    if len(trade) < 2:
        continue
    timestamp = int(trade[0])  # UNIX timestamp
    action = trade[1].lower()  # "buy" or "sell"

    # Get the closest price for the trade timestamp
    price = get_closest_price(timestamp)
    if price is None:
        print(f"No price data available for timestamp {timestamp}. Skipping trade.")
        continue

    if action == "buy":
        # Calculate the total position value
        borrowed_amount = current_investment * 5
        total_position_value = current_investment + borrowed_amount
        position_size = total_position_value / price  # Calculate number of assets bought
        margin_requirement = total_position_value * MAINTENANCE_MARGIN_REQUIREMENT
        current_investment = total_position_value  # All capital invested
    elif action == "sell":
        # Sell everything
        total_position_value = position_size * price  # Current market value of the position
        margin_requirement = 0  # No margin requirement after selling
        current_investment = investment  # Reset to initial investment
        borrowed_amount = 0
        position_size = 0
    else:
        continue  # Skip invalid actions

    # Append timestamp and margin requirement
    margin_points.append(f"{timestamp},{margin_requirement:.2f}")

# Write margin points to file
os.makedirs(os.path.dirname(MARGIN_FILE), exist_ok=True)
with open(MARGIN_FILE, "w") as f:
    f.write("\n".join(margin_points))

print(f"Margin requirement curve saved to {MARGIN_FILE}")
