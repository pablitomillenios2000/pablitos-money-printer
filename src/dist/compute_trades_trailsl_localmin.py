import os
import json5
from collections import deque
from tqdm import tqdm

# Define file paths 
api_key_file = "apikey-crypto.json"
asset_file = "../view/output/asset.txt"
trades_file = "../view/output/trades.txt"

# Load configuration
with open(api_key_file, 'r') as f:
    config = json5.load(f)

investment = config["investment"]
trailing_stop_loss_percentage = config["sl_percentage"]  # e.g. 1.5 for 1.5%

print("Computing trailing stop loss trades and local minima")

def read_asset_file():
    """Reads the asset file and returns the data as a list of tuples (timestamp, price)."""
    with open(asset_file, 'r') as f:
        return [tuple(map(float, line.strip().split(','))) for line in f]

def initialize_trades_file():
    """Clears the contents of the trades file by opening it in write mode."""
    with open(trades_file, 'w') as f:
        f.write("")  # Clear the file contents

def write_trade(timestamp, action, reason):
    """Writes a trade action to the trades file."""
    with open(trades_file, 'a') as f:
        f.write(f"{int(timestamp)},{action},{reason}\n")

def find_local_minimum(prices, window_size=5):
    """
    Finds a local minimum in a larger window of prices.
    The local minimum is defined as the middle element of
    the window being strictly less than all other elements.

    Expects `prices` to be a deque or list of tuples (timestamp, price)
    with length >= window_size.

    Parameters:
    - prices: deque/list of (timestamp, price) tuples
    - window_size (int): The size of the window to determine a local minimum.
                         Should be an odd number so there is a clear "middle" point.

    Returns:
    - The middle (timestamp, price) tuple if it's a local minimum, otherwise None.
    """
    if len(prices) < window_size:
        return None

    mid_index = window_size // 2
    # Extract the middle element
    mid_timestamp, mid_price = prices[mid_index]

    # Check if this price is less than all other prices in the window
    for i, (_, p) in enumerate(prices):
        if i != mid_index and mid_price >= p:
            return None

    # If we reach here, mid_price is the smallest in this window
    return (mid_timestamp, mid_price)

def process_trades():
    """Processes the trades based on trailing stop loss and local minima."""
    asset_data = read_asset_file()
    trailing_stop_price = None
    # Initialize to 'sell' state to allow first buy on local minimum
    last_action = 'sell'
    # We'll keep a 5-point window for detecting local minima
    recent_prices = deque(maxlen=5)
    last_stop_loss_sell_timestamp = None  # Track last time we sold due to stop loss

    with tqdm(total=len(asset_data), desc="Processing Trades", unit="entry") as pbar:
        for timestamp, price in asset_data:
            recent_prices.append((timestamp, price))

            # Check if we can detect a local minimum (only if we're currently 'sold out')
            if last_action == 'sell' and len(recent_prices) == 5:
                local_minimum = find_local_minimum(recent_prices)
                if local_minimum is not None:
                    local_min_timestamp = local_minimum[0]

                    # Only buy if it's at least 1 minute after the last stop loss sell
                    if (last_stop_loss_sell_timestamp is None or 
                        local_min_timestamp > last_stop_loss_sell_timestamp + 60):

                        # Found a local minimum that meets timing conditions, execute a buy
                        write_trade(local_min_timestamp, 'buy', 'locmin')
                        last_action = 'buy'
                        # Set the initial trailing stop price based on the price at buy time
                        trailing_stop_price = price * (1 - trailing_stop_loss_percentage / 100)
                        
                        # After buying, skip the trailing stop check in this iteration
                        pbar.update(1)
                        continue

            # If currently in a buy state, manage trailing stop
            if last_action == 'buy':
                # Update the trailing stop price if the current price justifies a higher stop
                new_stop = price * (1 - trailing_stop_loss_percentage / 100)
                if trailing_stop_price is None:
                    trailing_stop_price = new_stop
                else:
                    trailing_stop_price = max(trailing_stop_price, new_stop)

                # Check if price hits the trailing stop
                if price <= trailing_stop_price:
                    write_trade(timestamp, 'sell', 'tsl')
                    last_action = 'sell'
                    trailing_stop_price = None
                    last_stop_loss_sell_timestamp = timestamp

            pbar.update(1)  # Update progress bar on each iteration

if __name__ == "__main__":
    if not os.path.exists(asset_file):
        raise FileNotFoundError(f"Asset file not found: {asset_file}")
    initialize_trades_file()  # Clear trades file before processing
    process_trades()
