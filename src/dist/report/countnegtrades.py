import pandas as pd

# Specify file paths
TRADES_FILE = "../../view/output/trades.txt"
NEGTRADES_FILE = "../../view/report/repoutput/negtrades.txt"

# 1. Load trades data
df_trades = pd.read_csv(
    TRADES_FILE,
    header=None,
    names=["timestamp", "side", "trade_price", "marker"]
)

# 2. Sort trades chronologically
df_trades.sort_values("timestamp", inplace=True)
df_trades.reset_index(drop=True, inplace=True)

# 3. Identify and pair each 'downstart' with the next row (which ideally is 'downend')
df_downstart = df_trades[df_trades["marker"] == "downstart"].copy()
downstart_indices = df_downstart.index

# Only keep downstart rows that actually have a valid subsequent row index
downstart_indices = [i for i in downstart_indices if i + 1 in df_trades.index]
downend_indices = [i + 1 for i in downstart_indices]

# Build the paired DataFrames
df_start = df_trades.loc[downstart_indices].reset_index(drop=True)
df_end   = df_trades.loc[downend_indices].reset_index(drop=True)

# Rename columns for clarity
df_start.columns = ["start_timestamp", "start_side", "start_trade_price", "start_marker"]
df_end.columns   = ["end_timestamp",   "end_side",   "end_trade_price",   "end_marker"]

# Concatenate side-by-side into a single DataFrame
df_pairs = pd.concat([df_start, df_end], axis=1)

# Filter only the valid pairs where the next row is truly 'downend'
df_pairs = df_pairs[df_pairs["end_marker"] == "downend"].copy()

# 4. Compute ratio = 1 - (start_price / end_price)
df_pairs["ratio"] = 1 - (df_pairs["start_trade_price"] / df_pairs["end_trade_price"])

# 5. Write to negtrades.txt in the requested format:
#    columns: start_timestamp,start_price,end_timestamp,end_price,1-(start_price/end_price)
df_pairs.to_csv(
    NEGTRADES_FILE,
    columns=[
        "start_timestamp",
        "start_trade_price",
        "end_timestamp",
        "end_trade_price",
        "ratio",
    ],
    header=[
        "start_timestamp",
        "start_price",
        "end_timestamp",
        "end_price",
        "1-(start_price/end_price)",
    ],
    index=False
)

# (Optional) Print output for illustration
print("Matched downstart→downend pairs with ratio = 1 - (start_price / end_price):\n")
print(
    df_pairs[
        [
            "start_timestamp",
            "start_trade_price",
            "end_timestamp",
            "end_trade_price",
            "ratio",
        ]
    ]
)
