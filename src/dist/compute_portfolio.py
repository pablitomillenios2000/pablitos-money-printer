import csv
from datetime import datetime

# Adjust these paths/variables as needed
input_file = "../view/output/trades.txt"
output_file = "../view/output/portfolio.txt"

initial_capital = 1000.0
fee_rate = 0.002  # 0.001 fee per trade x2 on binance
                  # approx 2 euros on a 1000 eur trade
                  # find a way to verify this

def compute_portfolio_value(trades_path, output_path):
    # 1. Read and parse trades
    with open(trades_path, 'r') as f:
        reader = csv.reader(f)
        trades = []
        for row in reader:
            # row format: [timestamp, side, price, label]
            # Example: ['1741107240', 'buy', '83251.56', 'upstart']
            timestamp = int(row[0])
            side      = row[1].strip().lower()   # 'buy' or 'sell'
            price     = float(row[2])
            label     = row[3].strip().lower()   # e.g. 'upstart', 'upend'
            trades.append((timestamp, side, price, label))
    
    # 2. Sort trades by timestamp ascending
    trades.sort(key=lambda x: x[0])

    # 3. Set up tracking
    portfolio = initial_capital
    
    in_up_position = False
    up_open_price  = 0.0
    
    in_down_position = False
    down_open_price  = 0.0

    # For output lines
    output_lines = []
    # We'll keep a count of closed trades
    trade_count = 0

    def timestamp_to_str(ts):
        # Convert to a human-readable format, e.g. UTC
        return datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    
    # 4. Process trades in chronological order
    for (timestamp, side, price, label) in trades:
        # The portfolio value before applying this trade
        old_portfolio = portfolio
        
        # Convert timestamp
        ts_str = timestamp_to_str(timestamp)
        
        # We'll fill these if it's a closing trade
        entry_price_str = "N/A"
        exit_price_str  = "N/A"
        pct_gain_str    = "N/A"
        
        # For "end" trades, we will compute new_val_before_fee
        new_val_before_fee = old_portfolio
        new_val_after_fee  = old_portfolio

        # Handle opening trades
        if label == 'upstart':
            # Open a long position
            fee = portfolio * fee_rate
            portfolio -= fee
            in_up_position = True
            up_open_price  = price

        elif label == 'downstart':
            # Open a short position
            fee = portfolio * fee_rate
            portfolio -= fee
            in_down_position = True
            down_open_price  = price

        # Handle closing trades
        elif label == 'upend' and in_up_position:
            # We've closed a long position
            trade_count += 1  # increment the trade count

            entry_price_str = f"{up_open_price:.2f}"
            exit_price_str  = f"{price:.2f}"
            
            # 1) Compute PnL
            pnl_percent = (price - up_open_price) / up_open_price
            # 2) Update portfolio before fee
            new_val_before_fee = portfolio * (1.0 + pnl_percent)
            portfolio = new_val_before_fee

            # 3) Subtract fee
            fee = portfolio * fee_rate
            portfolio -= fee
            new_val_after_fee = portfolio

            pct_gain_str = f"{pnl_percent * 100:.2f}%"

            in_up_position = False
            up_open_price  = 0.0

            # Construct output block (closing trade)
            block = [
                f"============= ** Trade: {trade_count} ** ===============",
                f"Timestamp (human readable): {ts_str}",
                f"Current portfolio value: {old_portfolio:.2f}",
                f"Direction: Long",  # <-- Added line
                f"Entry price: {entry_price_str}",
                f"Exit price: {exit_price_str}",
                f"Percentage gain: {pct_gain_str}",
                f"New portfolio value (before fee): {new_val_before_fee:.2f}",
                f"New portfolio value (after fee): {new_val_after_fee:.2f}",
            ]
            output_lines.extend(block)
            output_lines.append("")  # blank line separator if desired

        elif label == 'downend' and in_down_position:
            # We've closed a short position
            trade_count += 1  # increment the trade count

            entry_price_str = f"{down_open_price:.2f}"
            exit_price_str  = f"{price:.2f}"

            # 1) Compute PnL
            pnl_percent = (down_open_price - price) / down_open_price
            # 2) Update portfolio (before fee)
            new_val_before_fee = portfolio * (1.0 + pnl_percent)
            portfolio = new_val_before_fee

            # 3) Subtract fee
            fee = portfolio * fee_rate
            portfolio -= fee
            new_val_after_fee = portfolio

            pct_gain_str = f"{pnl_percent * 100:.2f}%"

            in_down_position = False
            down_open_price  = 0.0

            # Construct output block (closing trade)
            block = [
                f"============= ** Trade: {trade_count} ** ===============",
                f"Timestamp (human readable): {ts_str}",
                f"Current portfolio value: {old_portfolio:.2f}",
                f"Direction: Short",  # <-- Added line
                f"Entry price: {entry_price_str}",
                f"Exit price: {exit_price_str}",
                f"Percentage gain: {pct_gain_str}",
                f"New portfolio value (before fee): {new_val_before_fee:.2f}",
                f"New portfolio value (after fee): {new_val_after_fee:.2f}",
            ]
            output_lines.extend(block)
            output_lines.append("")  # blank line separator if desired

        # Any other scenario is ignored or no-op.

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
