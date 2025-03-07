import os
import json5
from datetime import datetime, timezone
from binance.client import Client
from tqdm import tqdm
import time

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
    """
    Returns a list of positions (dicts) from the futures account,
    filtering only those that have nonzero positionAmt.
    """
    account_info = client.futures_account()
    positions = account_info['positions']
    open_positions = [pos for pos in positions if float(pos['positionAmt']) != 0]
    return open_positions

def close_position(symbol, amount):
    """
    Closes an existing futures position via a market order.
    Uses 'reduceOnly=True' to ensure it only offsets an existing position.

    :param symbol: e.g. 'BTCUSDT'
    :param amount: float, can be positive or negative. Positive => LONG, negative => SHORT
    """
    # Determine whether we’re closing a LONG or SHORT
    if amount > 0:
        side = 'LONG'
        order_side = Client.SIDE_SELL
    else:
        side = 'SHORT'
        order_side = Client.SIDE_BUY
    
    try:
        # Place the market close order with reduceOnly
        order = client.futures_create_order(
            symbol=symbol,
            side=order_side,
            type=ORDER_TYPE_MARKET,
            quantity=abs(float(amount)),
            reduceOnly=True,               # ensures the order will only close an existing position
            newOrderRespType='FULL'        # attempt to get fill info in response
        )

        # Write the immediate response to closes.txt
        with open(output_file, "a") as f:
            f.write(f"\n{datetime.now(timezone.utc)} - Close {side} position on {symbol}:\n")
            f.write(f"Immediate response: {order}\n")

        # Wait a short moment to ensure fill details are recorded on Binance’s side
        time.sleep(1)

        # Check the order status again
        order_status = client.futures_get_order(symbol=symbol, orderId=order['orderId'])
        with open(output_file, "a") as f:
            f.write(f"Queried order status: {order_status}\n")

        # (Optional) Re-check if the position is truly closed
        # fetch positions again for this symbol only
        current_positions = get_open_positions()
        still_open = [p for p in current_positions if p['symbol'] == symbol]
        if still_open:
            f.write(f"WARNING: Position on {symbol} still open: {still_open}\n")
        else:
            f.write(f"SUCCESS: Position on {symbol} is closed.\n")

        return order

    except Exception as e:
        print(f"Error closing position for {symbol}: {e}")
        with open(output_file, "a") as f:
            f.write(f"{datetime.now(timezone.utc)} - Error closing position for {symbol}: {e}\n")
        return None

def close_all_positions():
    """
    Closes all open futures positions one by one.
    Waits briefly between closes to respect API rate limits.
    Logs output in closes.txt.
    """
    open_positions = get_open_positions()
    if not open_positions:
        print("No open positions to close.")
        with open(output_file, "a") as f:
            f.write(f"{datetime.now(timezone.utc)} - No open positions to close.\n")
        return
    
    for pos in tqdm(open_positions, desc="Closing positions"):
        symbol = pos['symbol']
        amount = float(pos['positionAmt'])
        print(f"Closing position on {symbol}: amount={amount}")
        close_position(symbol, amount)
        time.sleep(1)

# Execute position closing
close_all_positions()
print("All positions closed (or attempted to close).")
