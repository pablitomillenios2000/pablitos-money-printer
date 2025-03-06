import os
import json5

# File paths
api_key_file = "apikey-crypto.json"
asset_file = "../view/output/asset.txt"
trades_file = "../view/output/trades.txt"
polyup_file = "../view/output/polyup.txt"
polydown_file = "../view/output/polydown.txt"
LINREG_SLOPE_FILE = "../view/output/linreg_slopes.txt"

MIN_STEEPNESS = 0.17 # Minimum Steepness of the Linreg to open trade

##############################################################################
# 1. Load config (if needed)
##############################################################################
with open(api_key_file, 'r') as f:
    config = json5.load(f)
# (Optional) Example usage of config parameters, if needed:
# trailing_stop_loss_percentage = config["sl_percentage"]

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

def read_linreg_slopes(path):
    """
    Reads slope data into a dictionary of {timestamp: slope}.
    Assumes each line is: <timestamp>,<slope>.
    Returns dict[int -> float].
    """
    slope_map = {}
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
                slope_val = float(parts[1])
                slope_map[t] = slope_val
            except ValueError:
                pass
    return slope_map

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
# 3. Parsing "polyup.txt" / "polydown.txt" to find segments, checking slope
##############################################################################
def parse_poly_file(poly_path, asset_map, slope_map, min_steepness,
                    reason_start, reason_end, trades_path):
    """
    Reads a file like polyup.txt or polydown.txt.  
    Identifies contiguous segments of numeric data (i.e. lines NOT '---').  
    - For each segment, the *first* timestamp => place a BUY (reason=reason_start)
      ONLY if abs(slope_map[first_timestamp]) > min_steepness.  
    - The *last* timestamp => place a SELL (reason=reason_end) if the buy occurred.

    Lines in poly file have format:  <timestamp>,<price or '---'>
    We skip lines with '---'.
    """
    segment = []

    def close_segment(segment_list):
        """When we have a closed segment, place buy at first, sell at last
           only if the slope at the first timestamp is steep enough."""
        if not segment_list:
            return

        first_ts, first_price = segment_list[0]
        # Check if we have a slope for the first_ts and if it's steep enough
        slope = slope_map.get(first_ts, None)
        if slope is None or abs(slope) <= min_steepness:
            # Skip placing trades for this segment
            return

        # If slope is steep enough, place the buy at the first candle
        write_trade_if_in_asset_map(first_ts, first_price, "buy", reason_start)

        # Then place the sell at the last candle of the segment
        if len(segment_list) > 1:
            last_ts, last_price = segment_list[-1]
            write_trade_if_in_asset_map(last_ts, last_price, "sell", reason_end)

    def write_trade_if_in_asset_map(ts, suggested_price, action, reason):
        """
        Writes a trade if we find the exact timestamp in asset_map. 
        Otherwise, skip or implement interpolation logic if needed.
        """
        if ts in asset_map:
            actual_price = asset_map[ts]
            write_trade(trades_path, ts, action, actual_price, reason)
        else:
            # If you need interpolation, place your interpolation logic here.
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
    # 4a. Read the asset data
    if not os.path.exists(asset_file):
        raise FileNotFoundError(f"Asset file not found: {asset_file}")
    asset_map = read_asset_file(asset_file)

    # 4b. Read the linreg slopes
    if not os.path.exists(LINREG_SLOPE_FILE):
        raise FileNotFoundError(f"Slope file not found: {LINREG_SLOPE_FILE}")
    slope_map = read_linreg_slopes(LINREG_SLOPE_FILE)

    # 4c. Clear the trades file
    initialize_trades_file(trades_file)

    # 4d. Parse polyup => for each contiguous numeric segment: buy at start (if slope steep),
    #     sell at end
    parse_poly_file(
        polyup_file,
        asset_map=asset_map,
        slope_map=slope_map,
        min_steepness=MIN_STEEPNESS,
        reason_start="upstart",
        reason_end="upend",
        trades_path=trades_file
    )

    # 4e. Parse polydown => for each contiguous numeric segment: buy at start (if slope steep),
    #     sell at end
    parse_poly_file(
        polydown_file,
        asset_map=asset_map,
        slope_map=slope_map,
        min_steepness=MIN_STEEPNESS,
        reason_start="downstart",
        reason_end="downend",
        trades_path=trades_file
    )

    print("Finished writing buy and sell trades.")

if __name__ == "__main__":
    main()
