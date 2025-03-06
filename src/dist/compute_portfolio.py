#!/usr/bin/env python3

import csv
from datetime import datetime, timezone

# Adjust these paths/variables as needed
input_file = "../view/output/trades.txt"
output_file = "../view/output/portfolio.txt"

initial_capital = 1000.0

# fee_rate is per trade side
# for example: if fee_rate=0.002, it’s ~0.2% fee each side, or 0.4% round-trip
fee_rate = 0.002  

# Fee for 1x leverage
margin_fee_1x = 0.002  

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
            side      = row[1].strip().lower()
            price     = float(row[2])
            label     = row[3].strip().lower()
            trades.append((timestamp, side, price, label))
    
    # 2. Sort trades by timestamp ascending
    trades.sort(key=lambda x: x[0])

    # 3. Set up tracking
    portfolio = initial_capital
    
    in_up_position = False
    up_open_price  = 0.0
    up_notional    = 0.0
    up_portfolio_before_open = 0.0  # We store the portfolio value before opening the long

    in_down_position = False
    down_open_price  = 0.0
    down_notional    = 0.0
    down_portfolio_before_open = 0.0  # We store the portfolio value before opening the short

    # For output lines
    output_lines = []
    trade_count = 0
    trade_pnls = []  # Each trade’s net PnL, including opening+closing fees

    def timestamp_to_str(ts):
        # Convert to a human-readable format (timezone-aware UTC)
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    
    def current_fee_rate():
        # Return correct fee rate depending on margin
        return margin_fee_1x if Margin == 1 else fee_rate

    # 4. Process trades
    for (timestamp, side, price, label) in trades:
        ts_str = timestamp_to_str(timestamp)

        # We'll fill these if it's a closing trade
        entry_price_str = "N/A"
        exit_price_str  = "N/A"
        pct_gain_str    = "N/A"

        #
        # ============ OPENING A LONG (UP) POSITION ============
        #
        if label == 'upstart':
            if in_up_position:
                # Already in a long; ignore or handle as you wish
                continue

            # Store the portfolio value *before* paying the opening fee
            up_portfolio_before_open = portfolio

            # Now pay the fee and adjust
            if Margin == 1:
                fee = portfolio * current_fee_rate()
                portfolio -= fee
                up_open_price = price
                in_up_position = True
                up_notional = portfolio  # 1x means notional ~ portfolio
            else:
                notional = portfolio * Margin
                open_fee = notional * current_fee_rate()
                portfolio -= open_fee
                up_open_price = price
                in_up_position = True
                up_notional = notional

        #
        # ============ OPENING A SHORT (DOWN) POSITION ============
        #
        elif label == 'downstart':
            if in_down_position:
                # Already in a short; ignore or handle as you wish
                continue

            down_portfolio_before_open = portfolio

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
                in_down_position = True
                down_notional   = notional

        #
        # ============ CLOSING A LONG POSITION ============
        #
        elif label == 'upend' and in_up_position:
            trade_count += 1
            entry_price_str = f"{up_open_price:.2f}"
            exit_price_str  = f"{price:.2f}"

            # PnL% for a long
            pnl_percent = (price - up_open_price) / up_open_price
            pct_gain_str = f"{pnl_percent * 100:.2f}%"

            # Calculate new portfolio after the price move and fee
            if Margin == 1:
                # Gains/loss are on 'portfolio' capital (since no real leverage).
                # Then we subtract the close fee.
                new_val_before_fee = portfolio * (1.0 + pnl_percent)
                portfolio = new_val_before_fee
                close_fee = portfolio * current_fee_rate()
                portfolio -= close_fee
            else:
                # Gains/loss are on up_notional.
                # Then we pay close fee on the notional as well.
                pnl = up_notional * pnl_percent
                new_val_before_fee = portfolio + pnl
                portfolio = new_val_before_fee
                close_fee = up_notional * current_fee_rate()
                portfolio -= close_fee

            new_val_after_fee = portfolio

            # Net trade PnL = (portfolio AFTER close) - (portfolio BEFORE open)
            trade_pnl = new_val_after_fee - up_portfolio_before_open
            trade_pnls.append(trade_pnl)

            # Write results for this trade
            block = [
                f"============= ** Trade: {trade_count} ** ===============",
                f"Timestamp (human readable): {ts_str}",
                f"Portfolio before open: {up_portfolio_before_open:.2f}",
                f"Direction: Long",
                f"Entry price: {entry_price_str}",
                f"Exit price: {exit_price_str}",
                f"Percentage gain (price-based): {pct_gain_str}",
                f"New portfolio value (before close fee): {new_val_before_fee:.2f}",
                f"New portfolio value (after close fee): {new_val_after_fee:.2f}",
                f"Trade PnL (net of fees): {trade_pnl:.2f}",
            ]
            output_lines.extend(block)
            output_lines.append("")

            # Reset
            in_up_position = False
            up_open_price  = 0.0
            up_notional    = 0.0
            up_portfolio_before_open = 0.0

        #
        # ============ CLOSING A SHORT POSITION ============
        #
        elif label == 'downend' and in_down_position:
            trade_count += 1
            entry_price_str = f"{down_open_price:.2f}"
            exit_price_str  = f"{price:.2f}"

            # PnL% for a short is (entry - exit)/entry
            pnl_percent = (down_open_price - price) / down_open_price
            pct_gain_str = f"{pnl_percent * 100:.2f}%"

            if Margin == 1:
                new_val_before_fee = portfolio * (1.0 + pnl_percent)
                portfolio = new_val_before_fee
                close_fee = portfolio * current_fee_rate()
                portfolio -= close_fee
            else:
                pnl = down_notional * pnl_percent
                new_val_before_fee = portfolio + pnl
                portfolio = new_val_before_fee
                close_fee = down_notional * current_fee_rate()
                portfolio -= close_fee

            new_val_after_fee = portfolio

            # Net trade PnL = (portfolio AFTER close) - (portfolio BEFORE open)
            trade_pnl = new_val_after_fee - down_portfolio_before_open
            trade_pnls.append(trade_pnl)

            # Write results for this trade
            block = [
                f"============= ** Trade: {trade_count} ** ===============",
                f"Timestamp (human readable): {ts_str}",
                f"Portfolio before open: {down_portfolio_before_open:.2f}",
                f"Direction: Short",
                f"Entry price: {entry_price_str}",
                f"Exit price: {exit_price_str}",
                f"Percentage gain (price-based): {pct_gain_str}",
                f"New portfolio value (before close fee): {new_val_before_fee:.2f}",
                f"New portfolio value (after close fee): {new_val_after_fee:.2f}",
                f"Trade PnL (net of fees): {trade_pnl:.2f}",
            ]
            output_lines.extend(block)
            output_lines.append("")

            in_down_position = False
            down_open_price  = 0.0
            down_notional    = 0.0
            down_portfolio_before_open = 0.0

        # else: ignore any other label or situation

    # 5. Final portfolio value and summary
    final_value = portfolio

    output_lines.append(f"Final Portfolio Value: {final_value:.2f}")
    output_lines.append(f"Number of Trades: {trade_count}")

    # Total net PnL across all trades (now includes opening & closing fees properly)
    total_pnl = sum(trade_pnls)
    output_lines.append(f"Total PnL (net of fees): {total_pnl:.2f}")

    # Average PnL per trade
    if trade_count > 0:
        avg_pnl = total_pnl / trade_count
    else:
        avg_pnl = 0.0
    output_lines.append(f"Average PnL per trade (net of fees): {avg_pnl:.2f}")

    # Percentage Increase from initial capital to final value
    pct_increase = (final_value - initial_capital) / initial_capital * 100.0
    output_lines.append(f"Percentage Increase (beginning to end): {pct_increase:.2f}%")

    # 6. Write out the results
    with open(output_path, 'w') as f_out:
        for line in output_lines:
            f_out.write(line + "\n")

    # Return metrics for console print
    return final_value, trade_count, total_pnl, avg_pnl, pct_increase

if __name__ == "__main__":
    (
        final_val, 
        trade_count, 
        total_pnl, 
        avg_pnl, 
        pct_increase
    ) = compute_portfolio_value(input_file, output_file)
    
    # Print the summary to the terminal
    print(f"Final Portfolio Value: {final_val:.2f}")
    print(f"Number of Trades: {trade_count}")
    print(f"Total PnL (net of fees): {total_pnl:.2f}")
    print(f"Average PnL per trade (net of fees): {avg_pnl:.2f}")
    print(f"Percentage Increase (beginning to end): {pct_increase:.2f}%")
