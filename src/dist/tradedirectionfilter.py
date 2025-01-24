import os
import json5
from datetime import datetime, timezone
from tqdm import tqdm

# Define paths
config_file = "apikey-crypto.json"
direction_file = "../view/output/direction.txt"
output_file = "../view/output/trades.txt"

# Function to read the direction file
def read_direction_file(filepath):
    direction_data = {}
    with open(filepath, 'r') as file:
        for line in file:
            timestamp, value = line.strip().split(',')
            direction_data[int(timestamp)] = int(value)
    return direction_data

# Function to read the trades file
def read_trades_file(filepath):
    trades = []
    with open(filepath, 'r') as file:
        for line in file:
            timestamp, action, reason = line.strip().split(',')
            trades.append({
                'timestamp': int(timestamp),
                'action': action,
                'reason': reason
            })
    return trades

# Function to write the updated trades to the file
def write_trades_file(filepath, trades):
    with open(filepath, 'w') as file:
        for trade in trades:
            file.write(f"{trade['timestamp']},{trade['action']},{trade['reason']}\n")

# Main script logic
def main():
    # Read the direction and trades files
    direction_data = read_direction_file(direction_file)
    trades = read_trades_file(output_file)

    # Process trades
    for trade in trades:
        if trade['action'] == 'buy' and direction_data.get(trade['timestamp']) == 4000:
            trade['action'] = 'sell'
            trade['reason'] = 'hysteresis'

    # Write the updated trades back to the file
    write_trades_file(output_file, trades)

if __name__ == "__main__":
    main()
