import pandas as pd

# Specify file paths
TRADES_FILE = "../../view/output/trades.txt"
NEGTRADES_FILE = "../../view/report/repoutput/negtrades.txt"  # Only for summary output

THRESHOLD = 0.12

# 1. Load trades data
df_trades = pd.read_csv(
    TRADES_FILE,
    header=None,
    names=["timestamp", "side", "trade_price", "marker"]
)

# 2. Sort trades chronologically
df_trades.sort_values("timestamp", inplace=True)
df_trades.reset_index(drop=True, inplace=True)

# --------------------------------------------------
#      DOWNSTART → DOWNEND
# --------------------------------------------------
df_downstart = df_trades[df_trades["marker"] == "downstart"].copy()
downstart_indices = df_downstart.index

# Only keep valid subsequent row
downstart_indices = [i for i in downstart_indices if i + 1 in df_trades.index]
downend_indices = [i + 1 for i in downstart_indices]

df_start_down = df_trades.loc[downstart_indices].reset_index(drop=True)
df_end_down   = df_trades.loc[downend_indices].reset_index(drop=True)

df_start_down.columns = ["start_timestamp", "start_side", "start_trade_price", "start_marker"]
df_end_down.columns   = ["end_timestamp",   "end_side",   "end_trade_price",   "end_marker"]

df_pairs_down = pd.concat([df_start_down, df_end_down], axis=1)
df_pairs_down = df_pairs_down[df_pairs_down["end_marker"] == "downend"].copy()

# Ratio for down trades
df_pairs_down["ratio"] = (df_pairs_down["start_trade_price"] / df_pairs_down["end_trade_price"] - 1) * 100
df_pairs_down["ratio"] = df_pairs_down["ratio"].round(5)

total_down_trades = len(df_pairs_down)
down_below_threshold = df_pairs_down[df_pairs_down["ratio"] < THRESHOLD]
count_down_below_threshold = len(down_below_threshold)
ratio_down_below_threshold = (
    count_down_below_threshold / total_down_trades * 100
    if total_down_trades > 0
    else 0
)

# --------------------------------------------------
#      UPSTART → UPEND
# --------------------------------------------------
df_upstart = df_trades[df_trades["marker"] == "upstart"].copy()
upstart_indices = df_upstart.index

# Only keep valid subsequent row
upstart_indices = [i for i in upstart_indices if i + 1 in df_trades.index]
upend_indices = [i + 1 for i in upstart_indices]

df_start_up = df_trades.loc[upstart_indices].reset_index(drop=True)
df_end_up   = df_trades.loc[upend_indices].reset_index(drop=True)

df_start_up.columns = ["start_timestamp", "start_side", "start_trade_price", "start_marker"]
df_end_up.columns   = ["end_timestamp",   "end_side",   "end_trade_price",   "end_marker"]

df_pairs_up = pd.concat([df_start_up, df_end_up], axis=1)
df_pairs_up = df_pairs_up[df_pairs_up["end_marker"] == "upend"].copy()

# Ratio for up trades
df_pairs_up["ratio"] = (df_pairs_up["end_trade_price"] / df_pairs_up["start_trade_price"] - 1) * 100
df_pairs_up["ratio"] = df_pairs_up["ratio"].round(5)

total_up_trades = len(df_pairs_up)
up_below_threshold = df_pairs_up[df_pairs_up["ratio"] < THRESHOLD]
count_up_below_threshold = len(up_below_threshold)
ratio_up_below_threshold = (
    count_up_below_threshold / total_up_trades * 100
    if total_up_trades > 0
    else 0
)

# --------------------------------------------------
#      Print Terminal Summary (as before)
# --------------------------------------------------
# DOWN trades summary
print("===== DOWNSTART → DOWNEND =====")
print(f"Total down trades: {total_down_trades}")
print(f"Down trades below threshold (ratio < {THRESHOLD}%): {count_down_below_threshold}")
print(f"Percentage of down trades below threshold: {ratio_down_below_threshold:.2f}%")

print("\nSample (3 rows) of downstart→downend pairs (omitting end_timestamp) with ratio in %:\n")
print(
    df_pairs_down[
        ["start_timestamp", "start_trade_price", "end_trade_price", "ratio"]
    ].head(3)
)

# UP trades summary
print("\n===== UPSTART → UPEND =====")
print(f"Total up trades: {total_up_trades}")
print(f"Up trades below threshold (ratio < {THRESHOLD}%): {count_up_below_threshold}")
print(f"Percentage of up trades below threshold: {ratio_up_below_threshold:.2f}%")

print("\nSample (3 rows) of upstart→upend pairs (omitting end_timestamp) with ratio in %:\n")
print(
    df_pairs_up[
        ["start_timestamp", "start_trade_price", "end_trade_price", "ratio"]
    ].head(3)
)

# --------------------------------------------------
#      Write Combined Summary to negtrades.txt
# --------------------------------------------------
total_trades = total_up_trades + total_down_trades

summary_text = (
    f"total_trades: {total_trades}\n"
    f"threshold: {THRESHOLD}\n"
    f"total_uptrades: {total_up_trades}\n"
    f"total_downtrades: {total_down_trades}\n\n"
    f"upwtrades_below_threshold: {count_up_below_threshold}\n"
    f"upwtrades_below_threshold_ratio: {ratio_up_below_threshold:.2f}\n\n"
    f"dowtrades_below_threshold: {count_down_below_threshold}\n"
    f"dowtrades_below_threshold_ratio: {ratio_down_below_threshold:.2f}\n"
)

with open(NEGTRADES_FILE, "w") as f:
    f.write(summary_text)

# print("\n----- Summary written to negtrades.txt (no commas) -----\n")
# print(summary_text)
