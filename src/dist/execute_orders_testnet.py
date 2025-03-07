import os
import json5

API_KEY_FILE = "apikey-crypto.json"

# Load the JSON file
with open(API_KEY_FILE, 'r') as file:
    config = json5.load(file)
    exchange = config.get("exchange").lower()

def read_last_timestamp(file_path):
    """Reads the last timestamp from the given file."""
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            line = file.readline().strip()
            return int(line) if line else None
    return None

def read_trades(file_path):
    """Reads the trades from the given file and returns them as a list of tuples."""
    trades = []
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            for line in file:
                parts = line.strip().split(',')
                if len(parts) == 3:
                    trades.append((int(parts[0]), parts[1], parts[2]))
    return trades

def execute_trade(trade):
    """Executes the trade by running the respective file."""
    timestamp, action, strategy = trade
    script_path = buy_order_file if action == 'buy' else sell_order_file

    print(f"Executing {action} trade with strategy {strategy} at timestamp {timestamp}")
    os.system(f"python3 {script_path}")

def write_last_timestamp(file_path, timestamp):
    """Writes the given timestamp to the file, overwriting existing content."""
    with open(file_path, 'w') as file:
        file.write(str(timestamp))

if __name__ == "__main__":
    last_timestamp_file = "../view/output/last_timestamp.txt"
    trades_file = "../view/output/trades.txt"

    buy_order_file = f"../python/{exchange}/long_order.py"
    sell_order_file = f"../python/{exchange}/short_order.py"

    # Read the last executed timestamp
    last_timestamp = read_last_timestamp(last_timestamp_file)

    # Read the trades from the file
    trades = read_trades(trades_file)

    if not trades:
        print("No trades to execute.")
    else:
        # Get the last trade from the list
        last_trade = trades[-1]
        last_trade_timestamp = last_trade[0]

        # Compare timestamps and execute the trade if necessary
        if last_timestamp is None or last_timestamp < last_trade_timestamp:
            execute_trade(last_trade)
            write_last_timestamp(last_timestamp_file, last_trade_timestamp)
        else:
            print("No new trades to execute.")
