import csv
from datetime import datetime

# Adjust these paths/variables as needed
input_file = "../view/output/trades.txt"
output_file = "../view/output/portfolio.txt"

initial_capital = 1000.0

# fee_rate is per trade side
# for example: if fee_rate=0.002, it’s ~0.2% fee each side, or 0.4% round-trip
fee_rate = 0.002  

# Fee for 1x leverage
margin_fee_1x = 0.02  

# For margin version, you can set e.g. Margin = 10 for 10x leverage
# If Margin=1, margin is effectively disabled (as if no leverage).
Margin = 10


def compute_portfolio_value(trades_path, output_path):
    # 1. Read and parse trades
    with open(trades_path, 'r') as f:
        reader = csv.reader(f)
        trades = []
        for row in reader:
            # row format: [timestamp, side, price, label]
            # Example: ['1741107240', 'buy', '83251.56', 'upstart']
            timestamp = int(row[0])
            side      = row[1].strip().lower()   # 'buy' or 'sell' if you like
            price     = float(row[2])
            label     = row[3].strip().lower()   # e.g. 'upstart', 'upend'
            trades.append((timestamp, side, price, label))
    
    # 2. Sort trades by timestamp ascending
    trades.sort(key=lambda x: x[0])

    # 3. Set up tracking
    portfolio = initial_capital
    
    in_up_position = False
    up_open_price  = 0.0
    up_notional    = 0.0  # Track the leveraged notional for the open position

    in_down_position = False
    down_open_price  = 0.0
    down_notional    = 0.0

    # For output lines
    output_lines = []
    trade_count = 0

    def timestamp_to_str(ts):
        # Convert to a human-readable format, e.g. UTC
        return datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    
    # Figure out which fee rate to use
    # If Margin == 1, use margin_fee_1x; else use fee_rate
    def current_fee_rate():
        return margin_fee_1x if Margin == 1 else fee_rate

    # 4. Process trades in chronological order
    for (timestamp, side, price, label) in trades:
        old_portfolio = portfolio
        ts_str = timestamp_to_str(timestamp)

        # We'll fill these if it's a closing trade
        entry_price_str = "N/A"
        exit_price_str  = "N/A"
        pct_gain_str    = "N/A"

        # For "end" trades, we will show new_val_before_fee vs. after_fee
        new_val_before_fee = old_portfolio
        new_val_after_fee  = old_portfolio

        #
        # ============ OPENING A LONG POSITION ============ 
        #
        if label == 'upstart':
            if in_up_position:
                # Already in a long; ignore or handle as you wish
                continue

            if Margin == 1:
                # Use margin_fee_1x for 1x margin
                fee = portfolio * current_fee_rate()
                portfolio -= fee
                up_open_price = price
                in_up_position = True
                up_notional = portfolio  # Not used exactly in old code, but keep consistent
            else:
                # Leverage approach:
                notional = portfolio * Margin
                open_fee = notional * current_fee_rate()
                portfolio -= open_fee
                up_open_price = price
                up_notional = notional
                in_up_position = True

        #
        # ============ OPENING A SHORT POSITION ============ 
        #
        elif label == 'downstart':
            if in_down_position:
                # Already in a short; ignore or handle as you wish
                continue

            if Margin == 1:
                fee = portfolio * current_fee_rate()
                portfolio -= fee
                down_open_price = price
                in_down_position = True
                down_notional = portfolio
            else:
                notional = portfolio * Margin
                open_fee = notional * current_fee_rate()
                portfolio -= open_fee
                down_open_price = price
                down_notional   = notional
                in_down_position = True

        #
        # ============ CLOSING A LONG POSITION ============ 
        #
        elif label == 'upend' and in_up_position:
            trade_count += 1
            entry_price_str = f"{up_open_price:.2f}"
            exit_price_str  = f"{price:.2f}"

            # Compute % gain (no matter margin or not)
            pnl_percent = (price - up_open_price) / up_open_price
            pct_gain_str = f"{pnl_percent * 100:.2f}%"

            if Margin == 1:
                # Original approach but using margin_fee_1x instead of fee_rate
                new_val_before_fee = portfolio * (1.0 + pnl_percent)
                portfolio = new_val_before_fee
                fee = portfolio * current_fee_rate()
                portfolio -= fee
                new_val_after_fee = portfolio
            else:
                # Leverage approach
                pnl = up_notional * pnl_percent
                new_val_before_fee = portfolio + pnl
                close_fee = up_notional * current_fee_rate()
                new_val_after_fee = new_val_before_fee - close_fee
                portfolio = new_val_after_fee

            # Build output block
            block = [
                f"============= ** Trade: {trade_count} ** ===============",
                f"Timestamp (human readable): {ts_str}",
                f"Current portfolio value before close: {old_portfolio:.2f}",
                f"Direction: Long",
                f"Entry price: {entry_price_str}",
                f"Exit price: {exit_price_str}",
                f"Percentage gain: {pct_gain_str}",
                f"New portfolio value (before fee): {new_val_before_fee:.2f}",
                f"New portfolio value (after fee): {new_val_after_fee:.2f}",
            ]
            output_lines.extend(block)
            output_lines.append("")

            # Reset
            in_up_position = False
            up_open_price  = 0.0
            up_notional    = 0.0

        #
        # ============ CLOSING A SHORT POSITION ============ 
        #
        elif label == 'downend' and in_down_position:
            trade_count += 1
            entry_price_str = f"{down_open_price:.2f}"
            exit_price_str  = f"{price:.2f}"

            # For a short, PnL% is (entry - exit)/entry
            pnl_percent = (down_open_price - price) / down_open_price
            pct_gain_str = f"{pnl_percent * 100:.2f}%"

            if Margin == 1:
                new_val_before_fee = portfolio * (1.0 + pnl_percent)
                portfolio = new_val_before_fee
                fee = portfolio * current_fee_rate()
                portfolio -= fee
                new_val_after_fee = portfolio
            else:
                pnl = down_notional * pnl_percent
                new_val_before_fee = portfolio + pnl
                close_fee = down_notional * current_fee_rate()
                new_val_after_fee = new_val_before_fee - close_fee
                portfolio = new_val_after_fee

            # Build output block
            block = [
                f"============= ** Trade: {trade_count} ** ===============",
                f"Timestamp (human readable): {ts_str}",
                f"Current portfolio value before close: {old_portfolio:.2f}",
                f"Direction: Short",
                f"Entry price: {entry_price_str}",
                f"Exit price: {exit_price_str}",
                f"Percentage gain: {pct_gain_str}",
                f"New portfolio value (before fee): {new_val_before_fee:.2f}",
                f"New portfolio value (after fee): {new_val_after_fee:.2f}",
            ]
            output_lines.extend(block)
            output_lines.append("")

            # Reset
            in_down_position = False
            down_open_price  = 0.0
            down_notional    = 0.0

        # Else: ignore any other label or situation

    # 5. Capture final portfolio value
    final_value = portfolio
    output_lines.append(f"Final Portfolio Value: {final_value:.2f}")

    # 6. Write out the results to the specified file
    with open(output_path, 'w') as f_out:
        for line in output_lines:
            f_out.write(line + "\n")

    return final_value


if __name__ == "__main__":
    final_val = compute_portfolio_value(input_file, output_file)
    print(f"Final Portfolio Value: {final_val:.2f}")
