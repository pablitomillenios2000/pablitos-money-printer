import pandas as pd

# Specify file paths
TRADES_FILE = "../../view/output/trades.txt"
NEGTRADES_FILE = "../../view/report/repoutput/negtrades.txt"

# Define threshold in percentage points (5%).
# Since we multiply ratio by 100, a threshold of 5 corresponds to 5%.
THRESHOLD = 0.05 

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

# Filter only valid pairs where the next row is truly 'downend'
df_pairs = df_pairs[df_pairs["end_marker"] == "downend"].copy()

# 4. Compute ratio as: (start_price / end_price - 1) * 100
#    This gives a percentage change relative to end_price (multiplied by -1 from your original formula).
df_pairs["ratio"] = (df_pairs["start_trade_price"] / df_pairs["end_trade_price"] - 1) * 100

# Round ratio to 5 decimal places
df_pairs["ratio"] = df_pairs["ratio"].round(5)

# 5. Write to negtrades.txt, omitting end_timestamp
df_pairs.to_csv(
    NEGTRADES_FILE,
    columns=[
        "start_timestamp",
        "start_trade_price",
        "end_trade_price",
        "ratio"
    ],
    header=[
        "start_timestamp",
        "start_price",
        "end_price",
        "ratio"
    ],
    index=False
)

# ----- Summary Stats -----
total_trades = len(df_pairs)

# "Below threshold" means ratio < THRESHOLD (which is 5, i.e. 5%)
trades_below_threshold = df_pairs[df_pairs["ratio"] < THRESHOLD]
count_below_threshold = len(trades_below_threshold)
percentage_below_threshold = (
    count_below_threshold / total_trades * 100
    if total_trades > 0
    else 0
)

# Print summary
print(f"Total trades: {total_trades}")
print(f"Trades below threshold (ratio < {THRESHOLD}%): {count_below_threshold}")
print(f"Percentage of trades below threshold: {percentage_below_threshold:.2f}%")

# Print sample output (omitting end_timestamp)
print("\nMatched downstart→downend pairs (omitting end_timestamp) with ratio in % (rounded to 5 decimals):\n")
print(
    df_pairs[
        [
            "start_timestamp",
            "start_trade_price",
            "end_trade_price",
            "ratio",
        ]
    ]
)
