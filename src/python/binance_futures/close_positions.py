import os
import json5
from datetime import datetime, timezone
from binance.client import Client
from tqdm import tqdm
from collections import defaultdict
import time

# Manually define the order type constant(s) you need
ORDER_TYPE_MARKET = "MARKET"

# Define paths
config_file = "../../dist/apikey-crypto.json"
output_file = "../../view/output/closes.txt"

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

# Initialize Binance Futures Testnet Client
client = Client(api_key, api_secret, testnet=True)

def get_open_positions():
    """Fetches all open futures positions."""
    positions = client.futures_account()['positions']
    open_positions = [pos for pos in positions if float(pos['positionAmt']) != 0]
    return open_positions

def close_position(symbol, amount, side):
    """
    Closes a futures position with a market order.
    
    :param symbol: The trading pair symbol (e.g., "BTCUSDT").
    :param amount: The position amount to close (positive or negative float).
    :param side: "LONG" if the positionAmt > 0, otherwise "SHORT".
    """
    # If we are long, to close we must SELL; if short, to close we must BUY.
    order_side = 'SELL' if side == 'LONG' else 'BUY'
    try:
        order = client.futures_create_order(
            symbol=symbol,
            side=order_side,
            type=ORDER_TYPE_MARKET,       # Use our manually defined constant
            quantity=abs(float(amount))   # Just in case amount is negative
        )
        return order
    except Exception as e:
        print(f"Error closing position for {symbol}: {e}")
        return None

def close_all_positions():
    """Closes all open futures positions."""
    open_positions = get_open_positions()
    for pos in tqdm(open_positions, desc="Closing positions"):
        symbol = pos['symbol']
        amount = float(pos['positionAmt'])
        side = 'LONG' if amount > 0 else 'SHORT'
        print(f"Closing {side} position on {symbol} (Size: {amount})")
        close_position(symbol, amount, side)
        time.sleep(1)  # A brief pause to avoid hitting API rate limits

# Execute position closing
close_all_positions()
print("All positions closed.")
