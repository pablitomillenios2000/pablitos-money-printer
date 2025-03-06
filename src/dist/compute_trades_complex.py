import os
import json5

# File paths
api_key_file = "apikey-crypto.json"
asset_file = "../view/output/asset.txt"
trades_file = "../view/output/trades.txt"

polyup_file   = "../view/output/polyup.txt"
polydown_file = "../view/output/polydown.txt"

POLYACC_FILE_UP    = "../view/output/polyacc_abs_up.txt"
POLYACC_FILE_DOWN  = "../view/output/polyacc_abs_down.txt"

##############################################################################
# 1. Load config (if needed)
##############################################################################
with open(api_key_file, 'r') as f:
    config = json5.load(f)

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

def read_timestamps_file(path):
    """
    Reads a file containing lines of <timestamp>,<price or something>.
    We only care about the timestamp part, so we return a set of timestamps.
    This is helpful for polyacc_abs_up.txt, polyacc_abs_down.txt, etc.
    If a line has '---' or is malformed, we skip it.
    """
    ts_set = set()
    if not os.path.exists(path):
        return ts_set  # Return empty set if file not found

    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(',')
            if len(parts) < 1:
                continue
            try:
                # The first part is a timestamp
                t = int(float(parts[0]))
                ts_set.add(t)
            except ValueError:
                pass
    return ts_set

##############################################################################
# 3. Parsing "polyup.txt" and "polydown.txt" to find segments
##############################################################################
def parse_poly_file(poly_path, asset_map,
                    reason_start, reason_end,
                    trades_path,
                    eligible_ts=None):
    """
    Reads a file like polyup.txt or polydown.txt.  
    Identifies contiguous segments of numeric data (i.e. lines NOT '---').  

    - For each segment of length >= 2:
        - If eligible_ts is None:
            * The 'start' is the first line in the segment.
        - Else:
            * The 'start' is the first line in that segment whose timestamp is in eligible_ts.
              If none match, skip the entire segment.
        - The 'end' is the last timestamp of that segment.

    :param eligible_ts: set of timestamps that are allowed as the "start" of the trade.
                       If None, we place the start at the first line in the segment (classic logic).
    """
    segment = []  # will hold (timestamp, price) for the current contiguous block

    def close_segment(segment_list):
        """When we have a closed segment, place buy at start, sell at end (only if length >= 2)."""
        if len(segment_list) < 2:
            return

        # Decide which index in segment_list is the "start."
        start_index = 0
        if eligible_ts is not None:
            # Look for the first line in the segment that is in eligible_ts
            start_index = None
            for i, (ts, p) in enumerate(segment_list):
                if ts in eligible_ts:
                    start_index = i
                    break
            if start_index is None:
                # No line in this segment is eligible => skip
                return

        # We have a valid start
        first_ts, first_price = segment_list[start_index]
        write_trade_if_in_asset_map(first_ts, first_price, "buy", reason_start)

        # End is always the last line in the segment
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

    # 4c. Load down-eligible timestamps from polyacc_abs_down (for downstart)
    down_eligible_ts = read_timestamps_file(POLYACC_FILE_DOWN)

    # 4d. Parse polydown => for each contiguous numeric segment:
    #     buy at the first line that appears in down_eligible_ts,
    #     sell at the last line.
    parse_poly_file(
        poly_path=polydown_file,
        asset_map=asset_map,
        reason_start="downstart",
        reason_end="downend",
        trades_path=trades_file,
        eligible_ts=down_eligible_ts
    )

    # 4e. Load up-eligible timestamps from polyacc_abs_up (for upstart)
    up_eligible_ts = read_timestamps_file(POLYACC_FILE_UP)

    # 4f. Parse polyup => for each contiguous numeric segment:
    #     buy at the first line that appears in up_eligible_ts,
    #     sell at the last line.
    parse_poly_file(
        poly_path=polyup_file,
        asset_map=asset_map,
        reason_start="upstart",
        reason_end="upend",
        trades_path=trades_file,
        eligible_ts=up_eligible_ts
    )

    print("writing buy and sell trades")

if __name__ == "__main__":
    main()
