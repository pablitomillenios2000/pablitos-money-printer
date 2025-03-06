import pandas as pd
import numpy as np

ASSET_FILE = "../view/output/asset.txt"
POLYUP_FILE = "../view/output/polyup.txt"
POLYDOWN_FILE = "../view/output/polydown.txt"
LINREG_FILE = "../view/output/linreg.txt"
LINREG_SLOPE_FILE = "../view/output/linreg_slopes.txt"

VERTICAL_OFFSET = 220

def parse_segments(filename):
    """
    Parse the given poly-file (either polyup or polydown) looking for segments
    separated by lines containing '---'. Each numeric line is 'timestamp, value'.

    Returns a list of (start_ts, end_ts) tuples, where:
        start_ts = min of all timestamps in that segment,
        end_ts = max of all timestamps in that segment.
    """
    segments = []
    current_timestamps = []  # hold timestamps for the current segment

    with open(filename, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue  # skip empty lines if any

            parts = line.split(",")
            if len(parts) != 2:
                continue  # skip malformed lines

            ts_str, val_str = parts[0], parts[1]

            try:
                ts = int(ts_str)
            except ValueError:
                # If we can't parse the timestamp, skip the line
                continue

            if val_str == "---":
                # A delimiter: close the current segment, if any
                if current_timestamps:
                    start_ts = min(current_timestamps)
                    end_ts = max(current_timestamps)
                    segments.append((start_ts, end_ts))
                    current_timestamps = []
            else:
                # A numeric line
                try:
                    float_val = float(val_str)  # just to confirm it's numeric
                    current_timestamps.append(ts)
                except ValueError:
                    pass  # Not numeric, ignore

    # If file did not end with '---' and there's a leftover segment
    if current_timestamps:
        start_ts = min(current_timestamps)
        end_ts = max(current_timestamps)
        segments.append((start_ts, end_ts))

    return segments

def main():
    # 1) Read asset data
    df_asset = pd.read_csv(
        ASSET_FILE,
        names=["timestamp", "price"],
        header=None,
        dtype={"timestamp": np.int64, "price": np.float64}
    )
    # Ensure ascending order by timestamp
    df_asset.sort_values("timestamp", inplace=True)

    # 2) Parse segments from polyup and polydown
    up_segments = parse_segments(POLYUP_FILE)
    down_segments = parse_segments(POLYDOWN_FILE)

    # Label them: 'up' or 'down'
    labeled_segments = [(start_ts, end_ts, "up")   for (start_ts, end_ts) in up_segments] + \
                       [(start_ts, end_ts, "down") for (start_ts, end_ts) in down_segments]

    # Sort all segments by their start time
    labeled_segments.sort(key=lambda x: x[0])

    # 3) Perform linear regression for each segment.
    #    Write the offset regression curves to LINREG_FILE
    #    and write the slope for each segment to LINREG_SLOPE_FILE
    print("Computing linear regressions and writing results...")

    with open(LINREG_FILE, "w") as f_out, open(LINREG_SLOPE_FILE, "w") as f_slope:
        for (start_ts, end_ts, segment_type) in labeled_segments:
            # Subset asset data for [start_ts, end_ts]
            mask = (df_asset["timestamp"] >= start_ts) & (df_asset["timestamp"] <= end_ts)
            df_sub = df_asset.loc[mask].copy()

            # Skip if fewer than 2 points
            if len(df_sub) < 2:
                continue

            x = df_sub["timestamp"].values.astype(float)
            y = df_sub["price"].values

            slope, intercept = np.polyfit(x, y, 1)

            # Write the slope info at the beginning of each segment
            f_slope.write(f"{start_ts},{slope}\n")

            # Determine offset direction for up vs. down segments
            if segment_type == "up":
                offset = -VERTICAL_OFFSET
            else:  # segment_type == "down"
                offset = VERTICAL_OFFSET

            # Write each point with its Y-value shifted (up or down)
            for ts_val in x:
                shifted_val = slope * ts_val + intercept + offset
                f_out.write(f"{int(ts_val)},{shifted_val}\n")

            # After writing a segment, write a break line
            # (using the last timestamp for clarity)
            last_timestamp = int(x[-1])
            f_out.write(f"{last_timestamp},---\n")

if __name__ == "__main__":
    main()
