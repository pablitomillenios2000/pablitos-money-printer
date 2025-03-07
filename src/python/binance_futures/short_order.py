import os
import json5
from datetime import datetime, timezone
from binance.client import Client
from tqdm import tqdm
from collections import defaultdict

# Define paths
config_file = "../../dist/apikey-crypto.json"
output_file = "../../view/output/orders.txt"

# Ensure the output directory exists
os.makedirs(os.path.dirname(output_file), exist_ok=True)

# Read the JSON configuration file
with open(config_file, "r") as json_file:
    config = json5.load(json_file)
    leverage = config.get("margin")  
    pair = config.get("pair")  
    investment = config.get("investment")      
    api_key = config.get("key")  
    api_secret = config.get("secret")  

# Initialize Binance client for Testnet
client = Client(api_key, api_secret, testnet=True)

# Ensure margin trading is enabled (set leverage if applicable)
try:
    client.futures_change_leverage(symbol=pair, leverage=leverage)
except Exception as e:
    print(f"Error setting leverage: {e}")
    exit()

# Get ticker price
try:
    ticker = client.futures_symbol_ticker(symbol=pair)
    price = float(ticker["price"])
except Exception as e:
    print(f"Error fetching ticker price: {e}")
    exit()

# Calculate order quantity
quantity = round(investment / price, 3)  # Adjust rounding as needed per Binance requirements

# Place a market sell order (short trade)
try:
    order = client.futures_create_order(
        symbol=pair,
        side=Client.SIDE_SELL,
        type=Client.ORDER_TYPE_MARKET,
        quantity=quantity,
        newOrderRespType='RESULT'  # or 'FULL' if your API version supports it
    )
    
    # Log order details
    with open(output_file, "a") as f:
        f.write(f"{datetime.now(timezone.utc)} - Short Order: {order}\n")
    print("Short order placed successfully:", order)
except Exception as e:
    print(f"Error placing short order: {e}")
