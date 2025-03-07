import os
import json5
import requests
from datetime import datetime, timezone
from binance.client import Client
from tqdm import tqdm

# Define paths
config_file = "../../dist/apikey-crypto.json"
output_file = "../../view/output/history.txt"

# Ensure the output directory exists
os.makedirs(os.path.dirname(output_file), exist_ok=True)

# Read the JSON configuration file
with open(config_file, "r") as json_file:
    config = json5.load(json_file)
    start_date_str = config.get("start_date")  # Extract the start date (as string)
    end_date_str = config.get("end_date")      # Extract the end date (as string)
    api_key = config.get("key")  
    api_secret = config.get("secret")  

# Initialize Binance Client (for Testnet)
client = Client(api_key, api_secret, testnet=True)

# Convert dates to timestamps (handle full datetime format)
start_timestamp = int(datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S")
                      .replace(tzinfo=timezone.utc).timestamp() * 1000)

end_timestamp = int(datetime.strptime(end_date_str, "%Y-%m-%d %H:%M:%S")
                    .replace(tzinfo=timezone.utc).timestamp() * 1000)

# Fetch all order history
try:
    orders = client.futures_account_trades(startTime=start_timestamp, endTime=end_timestamp)

    # Save the order history to a file
    with open(output_file, "w") as f:
        for order in tqdm(orders, desc="Saving orders"):
            f.write(json5.dumps(order, indent=4) + "\n")

    print(f"Order history saved to {output_file}")

except Exception as e:
    print(f"Error fetching trade history: {e}")
