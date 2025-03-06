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

MIN_STEEPNESS = 0.05   # Minimum steepness of the linreg slope to open trade
MIN_ACCELERATION = 0    # Minimum acceleration (polyreg) threshold
MIN_TRADE_AGE = 5       # Segment must span at least 5 minutes to place a trade

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
    If 'ts' is the first or last in sorted_ts, return False.
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
      price(ts) < price(prev_ts) AND price(ts) < price(next_ts).
    If 'ts' is the first or last in sorted_ts, return False.
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
# 4. Parsing "polyup.txt" / "polydown.txt" to find segments,
#    checking slope, acceleration, skipping local max/min for upstart/downstart,
#    and ensuring segment duration >= MIN_TRADE_AGE minutes
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
    
    Identifies contiguous segments of numeric data (lines NOT containing '---').
    Once '---' is encountered, we treat it as the end of that segment and:
      - BUY at the segment's first timestamp 
        (if slope & acceleration thresholds pass and not a local max/min).
      - SELL at the segment's last timestamp.
      - Only if (last_ts - first_ts) >= MIN_TRADE_AGE * 60.
    
    If the file ends without a trailing '---', that last segment remains open
    and does NOT produce a sell trade.
    """

    segment = []
    sorted_ts = build_sorted_timestamps(asset_map)

    def close_segment(segment_list):
        """
        When we have a closed segment (triggered by '---'), place buy at first, sell at last
        only if slope/acceleration pass checks, we skip local max/min for starts,
        and the segment's duration is >= MIN_TRADE_AGE minutes.
        """
        if not segment_list:
            return

        # Check that the segment is at least 2 points
        if len(segment_list) < 2:
            return

        # Calculate duration in seconds
        first_ts, first_price = segment_list[0]
        last_ts, _ = segment_list[-1]
        duration_seconds = last_ts - first_ts

        # Ensure segment is at least MIN_TRADE_AGE minutes
        if duration_seconds < MIN_TRADE_AGE * 60:
            return

        # --- Slope check at segment start ---
        slope = slope_map.get(first_ts, None)
        if slope is None:
            return

        # For upstart, need slope > min_steepness
        # For downstart, need slope < -min_steepness
        if is_up:
            if slope <= min_steepness:
                return
        else:
            if slope >= -min_steepness:
                return

        # --- Acceleration check (also at segment start) ---
        acceleration = acceleration_map.get(first_ts, None)
        if acceleration is None or abs(acceleration) <= min_acceleration:
            return

        # --- Local max/min check at segment start ---
        if is_up:
            # For an "upstart", skip if first_ts is a local maximum
            if is_local_maximum(first_ts, asset_map, sorted_ts):
                return
        else:
            # For a "downstart", skip if first_ts is a local minimum
            if is_local_minimum(first_ts, asset_map, sorted_ts):
                return

        # Conditions pass => place BUY at first candle
        write_trade_if_in_asset_map(first_ts, first_price, "buy", reason_start)

        # SELL at the segment's last candle
        last_ts, last_price = segment_list[-1]
        write_trade_if_in_asset_map(last_ts, last_price, "sell", reason_end)

    def write_trade_if_in_asset_map(ts, suggested_price, action, reason):
        """
        Writes a trade if we find the exact timestamp in asset_map. 
        Otherwise, skip or implement interpolation if needed.
        """
        if ts in asset_map:
            actual_price = asset_map[ts]
            write_trade(trades_path, ts, action, actual_price, reason)
        else:
            # If you need interpolation, place your logic here
            pass

    # -------------------------------------------------------------------------
    # Read the poly file; every time we encounter '---', we close the segment.
    # If the file ends with an open segment, that segment remains open => no SELL.
    # -------------------------------------------------------------------------
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
                continue  # skip malformed line

            # Check if second part is numeric or '---'
            price_str = parts[1]
            if price_str == '---':
                # End the current segment if it exists
                if segment:
                    close_segment(segment)
                    segment = []
            else:
                # Price is numeric
                try:
                    price_val = float(price_str)
                    segment.append((ts, price_val))
                except ValueError:
                    pass

    # -------------------------------------------------------------------------
    # IMPORTANT: We do NOT close_segment(segment) here if there's no trailing '---'.
    # Thus, the last segment is only closed if '---' appears. 
    # -------------------------------------------------------------------------

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
    #     - Place BUY at the segment's first timestamp if:
    #       (a) slope > MIN_STEEPNESS, 
    #       (b) acceleration > MIN_ACCELERATION, 
    #       (c) not local max, 
    #       (d) segment duration >= MIN_TRADE_AGE
    #     - Place SELL at the segment's last timestamp
    #     - Only if '---' is encountered to close that segment
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

    # 5f. Parse polydown => similarly for down segments:
    #     - BUY at segment start (slope < -MIN_STEEPNESS, etc.),
    #     - SELL at segment end,
    #     - Only if '---' is encountered to close that segment
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
