import os                # Module for interacting with the operating system (e.g., file paths, executing commands)
import json5             # Module for parsing JSON5 files which allow for more relaxed JSON syntax
import json              # Standard JSON module to ensure keys are written with double quotes

# Define the file that contains the API key and other configuration details
API_KEY_FILE = "apikey-crypto.json"

# ------------------------------ #
#   Load Configuration Settings  #
# ------------------------------ #

with open(API_KEY_FILE, 'r') as file:
    config = json5.load(file)
    exchange = config.get("exchange").lower()

# --------------------------------------------------- #
#   Function to Read the Last Executed Timestamp      #
#   (now using the new notes.json format)             #
# --------------------------------------------------- #

def read_last_timestamp(file_path):
    """
    Reads the last executed trade timestamp from a JSON file.
    
    The file is expected to have keys:
        - "last_polyupacc_time"
        - "last_polydownacc_time"
        - "last_order_time"
        
    This function uses the "last_order_time" key.
    
    Args:
        file_path (str): Path to the JSON file containing the timestamps.
        
    Returns:
        int or None: The last order timestamp as an integer if available, otherwise None.
    """
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            data = json5.load(file)
            if "last_order_time" in data:
                return int(data["last_order_time"])
    return None

# --------------------------------------------------- #
#   Function to Write the Last Executed Timestamp     #
#   (updating only the "last_order_time" key)         #
#   Using json.dump to enforce double quotes for keys  #
# --------------------------------------------------- #

def write_last_timestamp(file_path, timestamp):
    """
    Writes the provided timestamp to the JSON file under the "last_order_time" key.
    If the file already exists, it preserves other keys.
    
    Args:
        file_path (str): Path to the JSON file where the timestamp will be updated.
        timestamp (int): The timestamp to write.
    """
    data = {}
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            data = json5.load(file)
    data["last_order_time"] = float(timestamp)
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

# --------------------------------------------------- #
#   Function to Read Trades from a File               #
#   (updated to handle four fields per trade)         #
# --------------------------------------------------- #

def read_trades(file_path):
    """
    Reads trades from a file and returns them as a list of tuples.
    
    Each line in the file is expected to have four comma-separated values:
    timestamp, action, price, and strategy.
    
    Args:
        file_path (str): Path to the file containing trade details.
        
    Returns:
        list of tuples: Each tuple contains (timestamp (int), action (str), price (float), strategy (str)).
    """
    trades = []
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            for line in file:
                parts = line.strip().split(',')
                if len(parts) == 4:
                    timestamp = int(parts[0])
                    action = parts[1]
                    price = float(parts[2])
                    strategy = parts[3]
                    trades.append((timestamp, action, price, strategy))
    return trades

# --------------------------------------------------- #
#   Function to Execute a Trade Based on Strategy      #
# --------------------------------------------------- #

def execute_trade(trade):
    """
    Executes a trade by running the corresponding Python script based on the trade's strategy.
    
    - If strategy is "upstart": Executes the long trades script (buy_order_file).
    - If strategy is "downstart": Executes the short trades script (sell_order_file).
    - If strategy is "upend" or "downend": Executes the close_all orders script (close_all_orders_file).
    
    Args:
        trade (tuple): A tuple containing (timestamp, action, price, strategy).
    """
    timestamp, action, price, strategy = trade
    if strategy == "upstart":
        script_path = buy_order_file
    elif strategy == "downstart":
        script_path = sell_order_file
    elif strategy in ("upend", "downend"):
        script_path = close_all_orders_file
    else:
        print(f"Unknown strategy: {strategy}. No action taken.")
        return
    print(f"Executing trade: {strategy} at timestamp {timestamp}, price {price}")
    os.system(f"python3 {script_path}")

# --------------------------------------------------- #
#                   Main Execution Block             #
# --------------------------------------------------- #

if __name__ == "__main__":
    last_timestamp_file = "../view/output/notes.json"
    trades_file = "../view/output/trades.txt"

    # If notes.json does not exist, create it with default content.
    if not os.path.exists(last_timestamp_file):
        default_data = {
            "last_polyupacc_time": 1,
            "last_polydownacc_time": 1,
            "last_order_time": 1
        }
        with open(last_timestamp_file, 'w') as file:
            json.dump(default_data, file, indent=4)

    buy_order_file = f"../python/{exchange}/long_order.py"
    sell_order_file = f"../python/{exchange}/short_order.py"
    close_all_orders_file = f"../python/{exchange}/close_positions.py"

    last_timestamp = read_last_timestamp(last_timestamp_file)
    trades = read_trades(trades_file)

    if not trades:
        print("No trades to execute.")
    else:
        last_trade = trades[-1]
        last_trade_timestamp = last_trade[0]

        # If the last timestamp in the JSON equals the last timestamp in trades.txt, do nothing.
        if last_timestamp is not None and last_timestamp == last_trade_timestamp:
            print("No new trades to execute.")
        else:
            execute_trade(last_trade)
            write_last_timestamp(last_timestamp_file, last_trade_timestamp)
