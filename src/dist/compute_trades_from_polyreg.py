import os
import json5

# File paths
api_key_file = "apikey-crypto.json"
asset_file = "../view/output/asset.txt"
trades_file = "../view/output/trades.txt"
polyup_file = "../view/output/polyup.txt"
polydown_file = "../view/output/polydown.txt"

##############################################################################
# 1. Load config (if needed)
##############################################################################
with open(api_key_file, 'r') as f:
    config = json5.load(f)

# Example if you need a parameter from config:
# trailing_stop_loss_percentage = config["sl_percentage"]  # Not used here, but as an example

##############################################################################
# 2. Helpers: read data, write trades
##############################################################################
def read_asset_file(path):
    """
    Reads asset data into a dictionary of {timestamp: price}.
    Assumes each line is:  <timestamp>,<price>
    Returns dict[int -> float].
    """
    asset_map = {}
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(',')
            if len(parts) != 2:
                continue
            try:
                t = int(float(parts[0]))
                p = float(parts[1])
                asset_map[t] = p
            except ValueError:
                pass
    return asset_map

def initialize_trades_file(path):
    """Clears the contents of the trades file by opening it in write mode."""
    with open(path, 'w') as f:
        f.write("")  # Clear the file contents

def write_trade(path, timestamp, action, price, reason):
    """
    Append a trade line to trades file in the format:
      timestamp,action,price,reason
    """
    with open(path, 'a') as f:
        f.write(f"{timestamp},{action},{price},{reason}\n")

##############################################################################
# 3. Parsing "polyup.txt" and "polydown.txt" to find segments
##############################################################################
def parse_poly_file(poly_path, asset_map, reason_start, reason_end, trades_path):
    """
    Reads a file like polyup.txt or polydown.txt.  
    Identifies contiguous segments of numeric data (i.e. lines NOT '---').  
    - For each segment, the *first* timestamp => place a BUY (reason=reason_start).
    - The *last* timestamp => place a SELL (reason=reason_end).

    Lines in poly file have format:  <timestamp>,<price or '---'>
    We skip lines with '---'.
    """
    segment = []  # will hold (timestamp, price) for the current contiguous block
    def close_segment(segment_list):
        """When we have a closed segment, place buy at first, sell at last."""
        if not segment_list:
            return

        # Buy at the first in the segment
        first_ts, first_price = segment_list[0]
        write_trade_if_in_asset_map(first_ts, first_price, "buy", reason_start)

        # Sell at the last in the segment
        if len(segment_list) > 1:
            last_ts, last_price = segment_list[-1]
            write_trade_if_in_asset_map(last_ts, last_price, "sell", reason_end)

    def write_trade_if_in_asset_map(ts, suggested_price, action, reason):
        """
        Writes a trade if we find the exact timestamp in asset_map. 
        Otherwise, skip or implement your interpolation logic if needed.
        """
        if ts in asset_map:
            actual_price = asset_map[ts]
            write_trade(trades_path, ts, action, actual_price, reason)
        else:
            # If you need interpolation, place your interpolation logic here.
            # For now, skip if timestamp not found.
            pass

    with open(poly_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(',')
            if len(parts) != 2:
                continue

            # Extract timestamp
            try:
                ts = int(float(parts[0]))
            except ValueError:
                # skip malformed line
                continue

            # Check if price is numeric or '---'
            price_str = parts[1]
            if price_str == '---':
                # This breaks the current segment
                if segment:
                    close_segment(segment)
                    segment = []
            else:
                # Valid price
                try:
                    price_val = float(price_str)
                    segment.append((ts, price_val))
                except ValueError:
                    # skip malformed price
                    pass

    # End of file => if there's a segment still open, close it
    if segment:
        close_segment(segment)

##############################################################################
# 4. Main logic
##############################################################################
def main():
    # 4a. Read the asset data into a dictionary
    if not os.path.exists(asset_file):
        raise FileNotFoundError(f"Asset file not found: {asset_file}")
    asset_map = read_asset_file(asset_file)

    # 4b. Clear the trades file
    initialize_trades_file(trades_file)

    # 4c. Parse polyup => for each contiguous numeric segment: buy at start, sell at end
    parse_poly_file(polyup_file, asset_map, reason_start="upstart", reason_end="upend", trades_path=trades_file)

    # 4d. Parse polydown => for each contiguous numeric segment: buy at start, sell at end
    parse_poly_file(polydown_file, asset_map, reason_start="downstart", reason_end="downend", trades_path=trades_file)

if __name__ == "__main__":
    main()
