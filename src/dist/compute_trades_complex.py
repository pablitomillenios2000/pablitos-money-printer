import os
import json5

# File paths
api_key_file = "apikey-crypto.json"
asset_file = "../view/output/asset.txt"
trades_file = "../view/output/trades.txt"
polyup_file = "../view/output/polyup.txt"
polyacc_file = "../view/output/polyacc.txt"  # acceleration file
polydown_file = "../view/output/polydown.txt"
LINREG_SLOPE_FILE = "../view/output/linreg_slopes.txt"

MIN_STEEPNESS = 0.15  # Minimum steepness of the linreg to open trade
MIN_ACCELERATION = 0.001 # Minimum acceleration steepness of the polyreg

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

def read_acceleration_file(path):
    """
    Reads acceleration data into a dictionary of {timestamp: acceleration}.
    Assumes each line is: <timestamp>,<acceleration>.
    Returns dict[int -> float].
    """
    acceleration_map = {}
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
                acc_val = float(parts[1])
                acceleration_map[t] = acc_val
            except ValueError:
                pass
    return acceleration_map

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
# 3. Local max/min check
##############################################################################
def build_sorted_timestamps(asset_map):
    """Return a sorted list of timestamps from the asset_map keys."""
    return sorted(asset_map.keys())

def is_local_maximum(ts, asset_map, sorted_ts):
    """
    A point is considered a local maximum if:
      price(ts) > price(prev_ts) AND price(ts) > price(next_ts)
    where prev_ts and next_ts are the immediate neighbors of 'ts' in sorted_ts.
    If 'ts' is the first or last in sorted_ts, return False (cannot check).
    """
    if ts not in asset_map:
        return False
    try:
        idx = sorted_ts.index(ts)
    except ValueError:
        return False  # If we can't even find it (shouldn't happen), skip
    if idx == 0 or idx == len(sorted_ts) - 1:
        return False  # no neighbors to both sides

    current_price = asset_map[ts]
    prev_ts = sorted_ts[idx - 1]
    next_ts = sorted_ts[idx + 1]
    prev_price = asset_map[prev_ts]
    next_price = asset_map[next_ts]

    return (current_price > prev_price) and (current_price > next_price)

def is_local_minimum(ts, asset_map, sorted_ts):
    """
    A point is considered a local minimum if:
      price(ts) < price(prev_ts) AND price(ts) < price(next_ts)
    If 'ts' is the first or last in sorted_ts, return False (cannot check).
    """
    if ts not in asset_map:
        return False
    try:
        idx = sorted_ts.index(ts)
    except ValueError:
        return False
    if idx == 0 or idx == len(sorted_ts) - 1:
        return False

    current_price = asset_map[ts]
    prev_ts = sorted_ts[idx - 1]
    next_ts = sorted_ts[idx + 1]
    prev_price = asset_map[prev_ts]
    next_price = asset_map[next_ts]

    return (current_price < prev_price) and (current_price < next_price)

##############################################################################
# 4. Parsing "polyup.txt" / "polydown.txt" to find segments, checking slope,
#    acceleration, and skipping local max/min for upstart/downstart
##############################################################################
def parse_poly_file(
    poly_path,
    asset_map,
    slope_map,
    acceleration_map,
    min_steepness,
    min_acceleration,
    reason_start,
    reason_end,
    trades_path,
    is_up=True
):
    """
    Reads a file like polyup.txt or polydown.txt.
    Identifies contiguous segments of numeric data (i.e. lines NOT '---').
    - For each segment, the *first* timestamp => place a BUY (reason=reason_start)
      ONLY if both the slope and the acceleration at that timestamp exceed their thresholds.
    - The *last* timestamp => place a SELL (reason=reason_end) if the buy occurred.
    
    Lines in the poly file have the format: <timestamp>,<price or '---'>
    We skip lines with '---'.
    
    Additional conditions:
    - If is_up=True, skip the "buy" if that first timestamp is a local maximum.
    - If is_up=False, skip the "buy" if that first timestamp is a local minimum.
    """
    segment = []
    sorted_ts = build_sorted_timestamps(asset_map)

    def close_segment(segment_list):
        """When we have a closed segment, place buy at first, sell at last
           only if slope and acceleration are steep enough and it passes the local max/min checks."""
        if not segment_list:
            return

        first_ts, first_price = segment_list[0]

        # Check slope condition
        slope = slope_map.get(first_ts, None)
        if slope is None or abs(slope) <= min_steepness:
            return  # Not steep enough, skip trades

        # Check acceleration condition
        acceleration = acceleration_map.get(first_ts, None)
        if acceleration is None or abs(acceleration) <= min_acceleration:
            return  # Acceleration not high enough, skip trades

        # Check local max/min condition
        if is_up:
            # For an "upstart", skip if first_ts is a local maximum
            if is_local_maximum(first_ts, asset_map, sorted_ts):
                return
        else:
            # For a "downstart", skip if first_ts is a local minimum
            if is_local_minimum(first_ts, asset_map, sorted_ts):
                return

        # If both conditions are met and we pass local max/min check, place the buy
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
                continue  # Skip malformed line

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
                    pass

    # End of file: if there's a segment still open, close it
    if segment:
        close_segment(segment)

##############################################################################
# 5. Main logic
##############################################################################
def main():
    # 5a. Read the asset data
    if not os.path.exists(asset_file):
        raise FileNotFoundError(f"Asset file not found: {asset_file}")
    asset_map = read_asset_file(asset_file)

    # 5b. Read the linreg slopes
    if not os.path.exists(LINREG_SLOPE_FILE):
        raise FileNotFoundError(f"Slope file not found: {LINREG_SLOPE_FILE}")
    slope_map = read_linreg_slopes(LINREG_SLOPE_FILE)

    # 5c. Read the acceleration data
    if not os.path.exists(polyacc_file):
        raise FileNotFoundError(f"Acceleration file not found: {polyacc_file}")
    acceleration_map = read_acceleration_file(polyacc_file)

    # 5d. Clear the trades file
    initialize_trades_file(trades_file)

    # 5e. Parse polyup => for each contiguous numeric segment:
    #     - buy at start (if slope and acceleration exceed thresholds and NOT a local max),
    #     - sell at end.
    parse_poly_file(
        polyup_file,
        asset_map=asset_map,
        slope_map=slope_map,
        acceleration_map=acceleration_map,
        min_steepness=MIN_STEEPNESS,
        min_acceleration=MIN_ACCELERATION,
        reason_start="upstart",
        reason_end="upend",
        trades_path=trades_file,
        is_up=True
    )

    # 5f. Parse polydown => for each contiguous numeric segment:
    #     - buy at start (if slope and acceleration exceed thresholds and NOT a local min),
    #     - sell at end.
    parse_poly_file(
        polydown_file,
        asset_map=asset_map,
        slope_map=slope_map,
        acceleration_map=acceleration_map,
        min_steepness=MIN_STEEPNESS,
        min_acceleration=MIN_ACCELERATION,
        reason_start="downstart",
        reason_end="downend",
        trades_path=trades_file,
        is_up=False
    )

    print("Finished writing buy and sell trades.")

if __name__ == "__main__":
    main()
