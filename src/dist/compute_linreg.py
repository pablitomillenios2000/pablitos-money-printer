import pandas as pd
import numpy as np

ASSET_FILE = "../view/output/asset.txt"
POLYACC_FILE = "../view/output/polyacc_abs.txt"
LINREG_FILE = "../view/output/linreg.txt"

def main():
    # 1) Read the asset data: each line "<timestamp>,<price>"
    df_asset = pd.read_csv(
        ASSET_FILE, 
        names=["timestamp", "price"], 
        header=None,
        dtype={"timestamp": np.int64, "price": np.float64}
    )

    # 2) Read the polyacc data: each line "<timestamp>,<something>"
    #    We care only when <something> is either "-4" or "4"
    df_poly = pd.read_csv(
        POLYACC_FILE,
        names=["timestamp", "acc"],
        header=None
    )

    # 3) Convert '---' to NaN (or None) and keep only numeric entries
    #    so we can identify -4 or 4.
    df_poly.loc[df_poly["acc"] == "---", "acc"] = np.nan
    df_poly["acc"] = pd.to_numeric(df_poly["acc"], errors="coerce")

    # 4) We want to find intervals:
    #    - Start when polyacc_abs has -4
    #    - End when polyacc_abs has 4
    #    Then again start at 4, end at -4, etc.
    #    We'll loop through the polyacc data in ascending time order 
    df_poly.sort_values("timestamp", inplace=True)
    df_poly.dropna(subset=["acc"], inplace=True)  # keep only rows where acc is numeric (-4 or 4)

    # This list will hold tuples of (start_ts, end_ts, start_val, end_val)
    intervals = []
    current_start_ts = None
    current_start_val = None

    for _, row in df_poly.iterrows():
        ts = row["timestamp"]
        val = row["acc"]  # either -4 or 4

        # if we don't have an open segment, open one
        if current_start_val is None:
            current_start_ts = ts
            current_start_val = val
        else:
            # we do have an open segment, check if we have the opposite sign
            if (current_start_val == -4 and val == 4) or (current_start_val == 4 and val == -4):
                # We found a matching end for the segment
                intervals.append((current_start_ts, ts, current_start_val, val))
                # after closing, the new start is the one we just ended on
                current_start_ts = ts
                current_start_val = val
            else:
                # same sign as before, so just continue (no new segment)
                # or you could decide to close and reopen if you prefer. 
                # But from the instructions we only care about switching from -4 to 4 or 4 to -4.
                pass

    # 5) For each interval, do a linear regression on the asset data
    #    We'll write out for each timestamp in that interval: 
    #    "<timestamp>,<linreg_value>" to LINREG_FILE
    #    The user wants one piecewise linear regression for each interval. 
    #    We fit to the asset data in [start_ts, end_ts] (inclusive).
    #    Then for each row in that subset, we output the predicted value.

    # Sort the asset data by timestamp (just in case)
    df_asset.sort_values("timestamp", inplace=True)

    # We will open LINREG_FILE for writing fresh each time
    # (If you'd prefer to append, open in 'a')

    print("Writing Linear Regressions to file") 
    with open(LINREG_FILE, "w") as f_out:
        for (start_ts, end_ts, start_val, end_val) in intervals:
            # subset the asset data
            mask = (df_asset["timestamp"] >= start_ts) & (df_asset["timestamp"] <= end_ts)
            df_sub = df_asset.loc[mask].copy()

            if len(df_sub) < 2:
                # Not enough points to do a regression
                continue

            # do a simple linear regression using np.polyfit
            x = df_sub["timestamp"].values.astype(float)
            y = df_sub["price"].values

            # polyfit(x, y, 1) gives slope, intercept
            slope, intercept = np.polyfit(x, y, 1)
            # predicted values
            df_sub["linreg"] = slope * x + intercept

            # write out to file: each row "timestamp,linreg_value"
            for _, r in df_sub.iterrows():
                f_out.write(f"{int(r['timestamp'])},{r['linreg']}\n")

               

if __name__ == "__main__":
    main()
