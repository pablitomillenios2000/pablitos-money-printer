from pathlib import Path
import sys
import json5
import json
import math
import time
import datetime
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException

# Start the timer at the very beginning of the script execution
script_start_time = time.time()

print("Executing Margin SELL order script...")
home_dir = Path.home()

def sync_server_time(client):
    """
    Synchronizes local system time with Binance server time.
    This updates the client's internal timestamp offset.
    """
    try:
        server_time_response = client.get_server_time()
        server_time = server_time_response['serverTime']  # in milliseconds
        local_time = int(time.time() * 1000)  # in milliseconds
        time_offset = server_time - local_time
        client.time_offset = time_offset  # Update the client's internal time offset

        # For debugging: Print the server time, local time, and offset
        server_time_dt = datetime.datetime.fromtimestamp(server_time / 1000.0)
        local_time_dt = datetime.datetime.fromtimestamp(local_time / 1000.0)
        offset_seconds = time_offset / 1000.0

        print(f"[Time Sync] Server Time: {server_time_dt} | Local Time: {local_time_dt} | Offset: {offset_seconds} seconds")

    except Exception as e:
        print(f"Failed to synchronize time: {e}")
        raise

def place_order_with_retry(client, symbol, side, order_quantity, max_retries=3):
    """
    Place a margin order with retry logic for timestamp errors.
    """
    for attempt in range(1, max_retries + 1):
        try:
            order = client.create_margin_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=order_quantity
            )
            return order
        except BinanceAPIException as e:
            if e.code == -1021:  # Timestamp error
                print(f"Attempt {attempt}: Timestamp error detected. Resynchronizing time...")
                sync_server_time(client)
                time.sleep(2)  # Adding a longer sleep to ensure time sync takes effect
            else:
                print(f"Binance API Exception on attempt {attempt}: {e.message} (Code: {e.code})")
                raise
        except BinanceRequestException as e:
            print(f"Binance Request Exception on attempt {attempt}: {e}")
            raise
        except Exception as e:
            print(f"General Exception on attempt {attempt}: {e}")
            raise
    raise Exception("Failed to place order after multiple retries due to timestamp issues.")

try:
    # Step 1: Read API keys (and the number of simulation orders) from the JSON file
    with open(f"{home_dir}/CRYPTO-Trader/src/dist/apikey-crypto.json", "r") as file:
        api_keys = json5.load(file)
    
    api_key = api_keys['key']
    api_secret = api_keys['secret']
    trading_pair = api_keys['pair']

    # Read the number of orders (default to 20 if not found)
    num_orders = int(api_keys.get("number_sim_orders", 20))

    # Step 2: Initialize the Binance client
    client = Client(api_key, api_secret)

    # Synchronize time with Binance server
    sync_server_time(client)

    # Step 3: Extract the base asset from the trading pair
    if trading_pair.endswith('USDC'):
        asset_to_sell = trading_pair.replace('USDC', '')
    else:
        raise Exception(f"Unsupported trading pair format: {trading_pair}")

    print(f"Trading Pair: {trading_pair} | Base Asset: {asset_to_sell}")

    # Step 4: Fetch the balance from the margin account
    margin_account_info = client.get_margin_account()
    asset_balance = 0.0
    for asset in margin_account_info['userAssets']:
        if asset['asset'] == asset_to_sell:
            asset_balance = float(asset['free'])
            break

    if asset_balance <= 0:
        raise Exception(f"No {asset_to_sell} balance available to liquidate.")

    # Step 5: Round down the balance using floor
    asset_balance = math.floor(asset_balance)

    if asset_balance <= 0:
        raise Exception(f"Rounded {asset_to_sell} balance is zero, no asset to sell.")

    print(f"Ready to SELL {asset_balance} {asset_to_sell} in {num_orders} orders.")

    # Calculate the size of each order
    order_size = asset_balance // num_orders
    remainder = asset_balance % num_orders

    if order_size <= 0:
        raise Exception("Calculated order size is too small to execute multiple orders.")

    # Step 6: Execute margin market sell orders in parts
    for i in range(1, num_orders + 1):
        # For the last order, add the remainder if any
        current_order_size = order_size + (remainder if i == num_orders else 0)
        if current_order_size <= 0:
            print(f"Skipping order {i} because the size is {current_order_size}.")
            continue

        print(f"Placing SELL order {i}/{num_orders} for {current_order_size} {asset_to_sell}...")
        order = place_order_with_retry(client, trading_pair, 'SELL', current_order_size)
        print(f"Order {i} executed successfully. Order details:")
        print(json.dumps(order, indent=4))
        time.sleep(1)  # small pause to respect rate limits

    # Step 7: Refresh margin account info after the sell
    margin_account_info = client.get_margin_account()

    # Step 8: Repay all outstanding loans
    repaid_anything = False
    for asset in margin_account_info['userAssets']:
        borrowed_amount = float(asset['borrowed'])
        if borrowed_amount > 0:
            client.repay_margin_loan(asset=asset['asset'], amount=borrowed_amount)
            print(f"Repaid {borrowed_amount} of {asset['asset']} successfully.")
            repaid_anything = True

    if not repaid_anything:
        print("No debt to repay.")

except BinanceAPIException as e:
    if e.code == -1100:
        print("API Error -1100, character error. [Possibly invalid symbol or insufficient balance]")
    else:
        print(f"Error executing Margin SELL order script: {e}")
except Exception as e:
    print("Error executing Margin SELL order script:", str(e))
    sys.exit(1)
finally:
    # Stop the timer and print elapsed time
    script_end_time = time.time()
    elapsed_time = script_end_time - script_start_time
    print(f"Script completed in {elapsed_time:.2f} seconds.")
