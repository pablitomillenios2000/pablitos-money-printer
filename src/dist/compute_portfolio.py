import csv

# Adjust these paths/variables as needed

input_file = "../view/output/trades.txt"
output_file = "../view/output/portfolio.txt"

initial_capital = 1000.0
fee_rate = 0.02  # 2%

def compute_portfolio_value(trades_path):
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
            label     = row[3].strip().lower()   # e.g. 'upstart', 'downend'
            trades.append((timestamp, side, price, label))
    
    # 2. Sort trades by timestamp ascending
    trades.sort(key=lambda x: x[0])

    # 3. Set up tracking
    portfolio = initial_capital
    
    # For clarity, track whether we are "in" a position and its details
    in_up_position = False
    in_down_position = False
    up_open_price = 0.0
    down_open_price = 0.0
    
    # 4. Process trades in chronological order
    for (timestamp, side, price, label) in trades:
        # Apply logic based on label (upstart/upend, downstart/downend)
        if label == 'upstart':
            # Open a long position
            # Subtract fee
            fee = portfolio * fee_rate
            portfolio -= fee
            
            up_open_price = price
            in_up_position = True
            
        elif label == 'upend' and in_up_position:
            # Close the long position
            # Gain/loss for a long = (close_price - open_price) / open_price
            pnl_percent = (price - up_open_price) / up_open_price
            portfolio *= (1.0 + pnl_percent)
            
            # Subtract fee after closing
            fee = portfolio * fee_rate
            portfolio -= fee
            
            in_up_position = False
            up_open_price = 0.0
        
        elif label == 'downstart':
            # Open a short position
            # Subtract fee
            fee = portfolio * fee_rate
            portfolio -= fee
            
            down_open_price = price
            in_down_position = True
            
        elif label == 'downend' and in_down_position:
            # Close the short position
            # Gain/loss for a short = (open_price - close_price) / open_price
            pnl_percent = (down_open_price - price) / down_open_price
            portfolio *= (1.0 + pnl_percent)
            
            # Subtract fee after closing
            fee = portfolio * fee_rate
            portfolio -= fee
            
            in_down_position = False
            down_open_price = 0.0

    return portfolio


if __name__ == "__main__":
    final_value = compute_portfolio_value(input_file)
    print(f"Final Portfolio Value: {final_value:.2f}")
    
    # If you also want to write to an output file:
    with open(output_file, 'w') as f_out:
        f_out.write(f"Final Portfolio Value: {final_value:.2f}\n")
