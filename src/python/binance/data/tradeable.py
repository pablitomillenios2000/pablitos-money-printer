#!/usr/bin/env python3

from binance.client import Client
from binance.exceptions import BinanceAPIException
import json5
from pathlib import Path

# ----------------------------------------------------------------------------
# Load the trading pair and API keys from apikey-crypto.json
# ----------------------------------------------------------------------------
home_dir = Path.home()
with open(f"{home_dir}/pablitos-money-printer/src/dist/apikey-crypto.json", "r") as file:
    config = json5.load(file)

# Validate required keys
required_keys = ["pair", "key", "secret"]
if not all(key in config for key in required_keys):
    raise ValueError("The 'apikey-crypto.json' file must contain 'pair', 'key', and 'secret'.")

symbol = config["pair"].upper()  # Convert to uppercase for Binance consistency
API_KEY = config["key"]
API_SECRET = config["secret"]

def is_tradeable(symbol):
    """
    Check if a given symbol (e.g., BTCUSDT) is tradeable on Binance.
    """
    try:
        # Initialize Binance client
        client = Client(API_KEY, API_SECRET)
        
        # Fetch exchange info to find the symbol
        exchange_info = client.get_exchange_info()
        
        # Check if the symbol exists and is tradeable
        for s in exchange_info['symbols']:
            if s['symbol'] == symbol:
                if s['status'] == 'TRADING':
                    return True
                else:
                    return False
        return False  # Symbol not found
    except BinanceAPIException as e:
        print(f"Binance API Exception: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    # Use symbol directly from the config file
    print(f"Checking if the symbol '{symbol}' is tradeable on Binance...")
    if is_tradeable(symbol):
        print(f"YES: The symbol '{symbol}' is tradeable on Binance.")
    else:
        print(f"NO: The symbol '{symbol}' is NOT tradeable on Binance.")
