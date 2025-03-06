import pandas as pd
import numpy as np

ASSET_FILE = "../view/output/asset.txt"
POLYUP_FILE = "../view/output/polyup.txt"
POLYDOWN_FILE = "../view/output/polydown.txt"
LINREG_FILE = "../view/output/linreg.txt"

def parse_segments(filename):
    """
    Parse the given poly-file (either polyup or polydown) looking for segments
    separated by lines containing '---'. Each numeric line is 'timestamp, value'.
    
    Returns a list of (start_ts, end_ts) tuples, where start_ts = min of all
    timestamps in that segment, end_ts = max of all timestamps in that segment.
    """
    segments = []
    current_timestamps = []  # hold timestamps for the current segment

    with open(filename, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue  # skip empty lines if any

            # Each line is "timestamp, something"
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
                # A numeric line (hopefully). We'll parse or skip if invalid.
                try:
                    float_val = float(val_str)  # just to confirm it's numeric
                    current_timestamps.append(ts)
                except ValueError:
                    # Not numeric, ignore
                    pass

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

    # Combine them all (you could keep them separate if you want different outputs)
    all_segments = up_segments + down_segments

    # Sort by start time (optional, for convenience)
    all_segments.sort(key=lambda x: x[0])

    # 3) Perform linear regression for each segment and write out
    print("Computing linear regressions and writing to:", LINREG_FILE)
    with open(LINREG_FILE, "w") as f_out:
        for (start_ts, end_ts) in all_segments:
            # Subset asset data for [start_ts, end_ts]
            mask = (df_asset["timestamp"] >= start_ts) & (df_asset["timestamp"] <= end_ts)
            df_sub = df_asset.loc[mask].copy()

            # Skip if fewer than 2 points
            if len(df_sub) < 2:
                continue

            x = df_sub["timestamp"].values.astype(float)
            y = df_sub["price"].values

            slope, intercept = np.polyfit(x, y, 1)
            df_sub["linreg"] = slope * x + intercept

            # Write "timestamp, linreg" for each row
            for _, row in df_sub.iterrows():
                f_out.write(f"{int(row['timestamp'])},{row['linreg']}\n")

if __name__ == "__main__":
    main()
