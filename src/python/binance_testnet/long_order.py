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
    invest_all = config.get("invest_all")
    api_key = config.get("key")
    api_secret = config.get("secret")

# Initialize Binance client for Testnet
client = Client(api_key, api_secret, testnet=True)

# Ensure margin (leverage) is enabled
try:
    client.futures_change_leverage(symbol=pair, leverage=leverage)
except Exception as e:
    print(f"Error setting leverage: {e}")
    exit()

# Fetch current ticker price
try:
    ticker = client.futures_symbol_ticker(symbol=pair)
    price = float(ticker["price"])
except Exception as e:
    print(f"Error fetching ticker price: {e}")
    exit()

# Query the current USDT balance before placing the order
try:
    futures_balances = client.futures_account_balance()
    usdt_balance_entry = next(item for item in futures_balances if item["asset"] == "USDT")
    available_balance = float(usdt_balance_entry["availableBalance"])
except StopIteration:
    print("USDT asset not found in your futures account balance.")
    exit()
except Exception as e:
    print(f"Error retrieving USDT balance: {e}")
    exit()

# Log the available USDT balance to the output file
with open(output_file, "a") as f:
    f.write(f"{datetime.now(timezone.utc)} - Available USDT Balance before order: {available_balance}\n")

# Determine if we're investing all available USDT
invest_all_str = str(invest_all).strip().lower()

if invest_all_str == "true":
    if available_balance <= 0:
        print("No available USDT balance to invest.")
        exit()
    
    # Calculate quantity based on all available balance * leverage
    raw_quantity = (available_balance * leverage) / price
    # Apply a 3% reduction as a safety buffer to account for fees or minor fluctuations
    adjusted_quantity = round(raw_quantity * 0.97, 3)
    print(f"Investing all: {available_balance} USDT at leverage {leverage}, adjusted quantity = {adjusted_quantity}")
    quantity = adjusted_quantity
else:
    # Use fixed investment from config if not investing all available funds
    quantity = round(investment / price, 3)

# Place a market BUY order (long trade)
try:
    order = client.futures_create_order(
        symbol=pair,
        side=Client.SIDE_BUY,
        type=Client.ORDER_TYPE_MARKET,
        quantity=quantity,
        newOrderRespType='RESULT'  # or 'FULL' if your API version supports it
    )

    # Log order details
    with open(output_file, "a") as f:
        f.write(f"{datetime.now(timezone.utc)} - Long Order: {order}\n")
    print("Long order placed successfully:", order)

except Exception as e:
    print(f"Error placing long order: {e}")
