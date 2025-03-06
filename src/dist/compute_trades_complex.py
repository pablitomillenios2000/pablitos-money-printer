import os
import json5

# ------------------------------------------------------------------------------
# File paths
# ------------------------------------------------------------------------------
api_key_file = "apikey-crypto.json"
asset_file = "../view/output/asset.txt"
trades_file = "../view/output/trades.txt"
polyup_file = "../view/output/polyup.txt"
polyacc_file = "../view/output/polyacc.txt"  # acceleration file
polydown_file = "../view/output/polydown.txt"
LINREG_SLOPE_FILE = "../view/output/linreg_slopes.txt"

# ------------------------------------------------------------------------------
# Parameters
# ------------------------------------------------------------------------------
MIN_STEEPNESS = 0.05  # Minimum slope magnitude for opening trades
MIN_ACCELERATION = 0   # Minimum acceleration magnitude for opening trades
MIN_OFFICIAL_TRADE_AGE = 5  # in minutes; used to distinguish tempstart vs. upstart/downstart

# ------------------------------------------------------------------------------
# 1. Load config (optional)
# ------------------------------------------------------------------------------
with open(api_key_file, 'r') as f:
    config = json5.load(f)
# For example, you could do something with config, e.g.:
# trailing_stop_loss_percentage = config["sl_percentage"]

# ------------------------------------------------------------------------------
# 2. Helpers: reading data and writing trades
# ------------------------------------------------------------------------------
def read_asset_file(path):
    """
    Reads asset data into a dictionary of {timestamp: price}.
    Each line: <timestamp>,<price>
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
    Each line: <timestamp>,<slope>
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
    Each line: <timestamp>,<acceleration>
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
        f.write("")  # Just wipe the file

def write_trade(path, timestamp, action, price, reason):
    """
    Appends a trade line to trades file in the format:
      timestamp,action,price,reason
    """
    with open(path, 'a') as f:
        f.write(f"{timestamp},{action},{price},{reason}\n")

# ------------------------------------------------------------------------------
# 3. Local max/min check
# ------------------------------------------------------------------------------
def build_sorted_timestamps(asset_map):
    """Returns a sorted list of timestamps from the given asset_map."""
    return sorted(asset_map.keys())

def is_local_maximum(ts, asset_map, sorted_ts):
    """
    A point is a local maximum if:
      price(ts) > price(prev_ts) and price(ts) > price(next_ts).
    If 'ts' is the first or last in sorted_ts, returns False.
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

    return (current_price > prev_price) and (current_price > next_price)

def is_local_minimum(ts, asset_map, sorted_ts):
    """
    A point is a local minimum if:
      price(ts) < price(prev_ts) and price(ts) < price(next_ts).
    If 'ts' is the first or last in sorted_ts, returns False.
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

# ------------------------------------------------------------------------------
# 4. parse_poly_file: logic for polyup.txt / polydown.txt
#    If the file does not end with '---', the last SELL is named "tempend".
# ------------------------------------------------------------------------------
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
    is_up=True,
    max_timestamp=None
):
    """
    Reads lines from poly_path (like polyup.txt or polydown.txt).
    Identifies contiguous segments of numeric data (lines NOT containing '---').

    - For each segment, the *first* timestamp => place a BUY 
      (reason=reason_start or a "tempstart" if it's too recent).
    - The *last* timestamp => place a SELL. If the file ends with '---',
      that SELL reason is reason_end, otherwise it's "tempend".
    - If we encounter '---' mid-file, we close the current segment normally 
      (with reason_end).
    - We skip a segment if slope/acceleration isn't steep enough or 
      if the first_ts is a local max/min in the wrong direction.
    """

    # --------------------------------------------------------------------------
    # Read all lines so we can check if the file ends with '---'.
    # --------------------------------------------------------------------------
    with open(poly_path, 'r') as f:
        all_lines = f.read().strip().splitlines()

    # If file is empty, do nothing
    if not all_lines:
        return

    # Does the last line end with '---'?
    last_line = all_lines[-1].strip()
    last_line_is_break = False
    if last_line:
        parts = last_line.split(',')
        if len(parts) == 2 and parts[1] == '---':
            last_line_is_break = True

    # If NOT ending with '---', final SELL should be "tempend"
    final_sell_reason = "tempend" if not last_line_is_break else reason_end

    # Prepare to accumulate a segment
    segment = []
    sorted_ts = build_sorted_timestamps(asset_map)

    # For up or down "tempstart"
    temp_reason_start = "utempstart" if is_up else "dtempstart"

    def write_trade_if_in_asset_map(ts, suggested_price, action, reason):
        """
        Writes a trade if we find the exact timestamp in asset_map. 
        Otherwise skip or do interpolation logic if needed.
        """
        if ts in asset_map:
            actual_price = asset_map[ts]
            write_trade(trades_path, ts, action, actual_price, reason)

    def close_segment(segment_list, forced_reason_end=None):
        """
        Closes a segment by:
          - Checking slope/acc on the first timestamp.
          - Checking local max/min skip logic.
          - Buying at the first candle (with upstart/downstart or tempstart).
          - Selling at the last candle (with forced_reason_end or reason_end).
        """
        if not segment_list:
            return

        first_ts, first_price = segment_list[0]

        # Slope check
        slope = slope_map.get(first_ts, None)
        if slope is None:
            return

        if is_up:
            # upstart => slope > min_steepness
            if slope <= min_steepness:
                return
        else:
            # downstart => slope < -min_steepness
            if slope >= -min_steepness:
                return

        # Acceleration check
        acceleration = acceleration_map.get(first_ts, None)
        if (acceleration is None) or (abs(acceleration) <= min_acceleration):
            return

        # Local max/min check
        if is_up:
            # skip if it's a local max
            if is_local_maximum(first_ts, asset_map, sorted_ts):
                return
        else:
            # skip if it's a local min
            if is_local_minimum(first_ts, asset_map, sorted_ts):
                return

        # Decide if start is tempstart or normal
        if max_timestamp is not None:
            age_seconds = max_timestamp - first_ts
            if age_seconds < (MIN_OFFICIAL_TRADE_AGE * 60):
                chosen_reason_start = temp_reason_start
            else:
                chosen_reason_start = reason_start
        else:
            chosen_reason_start = reason_start

        # Place BUY at first candle
        write_trade_if_in_asset_map(first_ts, first_price, "buy", chosen_reason_start)

        # Place SELL at last candle
        if len(segment_list) > 1:
            last_ts, last_price = segment_list[-1]
            # Use forced_reason_end if provided, else the normal reason_end
            sell_reason = forced_reason_end if forced_reason_end else reason_end
            write_trade_if_in_asset_map(last_ts, last_price, "sell", sell_reason)

    # --------------------------------------------------------------------------
    # Parse the lines
    # --------------------------------------------------------------------------
    for line in all_lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split(',')
        if len(parts) != 2:
            continue

        try:
            ts = int(float(parts[0]))
        except ValueError:
            continue

        price_str = parts[1]
        if price_str == '---':
            # Break this segment
            if segment:
                close_segment(segment, forced_reason_end=reason_end)
                segment = []
        else:
            try:
                price_val = float(price_str)
                segment.append((ts, price_val))
            except ValueError:
                pass

    # --------------------------------------------------------------------------
    # If there's a remaining segment, close it with final_sell_reason
    # --------------------------------------------------------------------------
    if segment:
        close_segment(segment, forced_reason_end=final_sell_reason)

# ------------------------------------------------------------------------------
# 5. Main logic
# ------------------------------------------------------------------------------
def main():
    # Read the asset data
    if not os.path.exists(asset_file):
        raise FileNotFoundError(f"Asset file not found: {asset_file}")
    asset_map = read_asset_file(asset_file)

    # Read the linreg slopes
    if not os.path.exists(LINREG_SLOPE_FILE):
        raise FileNotFoundError(f"Slope file not found: {LINREG_SLOPE_FILE}")
    slope_map = read_linreg_slopes(LINREG_SLOPE_FILE)

    # Read the acceleration data
    if not os.path.exists(polyacc_file):
        raise FileNotFoundError(f"Acceleration file not found: {polyacc_file}")
    acceleration_map = read_acceleration_file(polyacc_file)

    # Clear the trades file
    initialize_trades_file(trades_file)

    # Determine the maximum timestamp in our asset_map
    max_ts = max(asset_map.keys())

    # Parse polyup
    parse_poly_file(
        poly_path=polyup_file,
        asset_map=asset_map,
        slope_map=slope_map,
        acceleration_map=acceleration_map,
        min_steepness=MIN_STEEPNESS,
        min_acceleration=MIN_ACCELERATION,
        reason_start="upstart",
        reason_end="upend",
        trades_path=trades_file,
        is_up=True,
        max_timestamp=max_ts
    )

    # Parse polydown
    parse_poly_file(
        poly_path=polydown_file,
        asset_map=asset_map,
        slope_map=slope_map,
        acceleration_map=acceleration_map,
        min_steepness=MIN_STEEPNESS,
        min_acceleration=MIN_ACCELERATION,
        reason_start="downstart",
        reason_end="downend",
        trades_path=trades_file,
        is_up=False,
        max_timestamp=max_ts
    )

    print("Finished writing buy and sell trades.")

if __name__ == "__main__":
    main()
