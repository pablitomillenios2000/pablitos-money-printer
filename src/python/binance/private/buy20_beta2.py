import requests
import time
import hmac
import hashlib
import math
import json5
import json
from pathlib import Path
import sys
import datetime

from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException

BASE_URL = 'https://api.binance.com'
SLIPPAGE_FILE = '/home/g1pablo_escaida1/pablitos-money-printer/src/view/output/slippage.txt'

# ------------------- HELPER FUNCTIONS ------------------- #
def parse_pair(pair: str):
    """
    Given a trading pair like 'SUIUSDC' or 'HBARUSDC',
    return (base_symbol, quote_symbol).
    Assumes quote is always 'USDC'.
    """
    if not pair.endswith("USDC"):
        raise ValueError(f"Unexpected pair format '{pair}'. Expected to end with 'USDC'.")
    base_symbol = pair[:-4]  # everything before the last 4 chars
    quote_symbol = "USDC"
    return base_symbol, quote_symbol

def get_price_from_binance(pair: str):
    """
    Fetch the price for the specified pair (e.g. 'SUIUSDC', 'HBARUSDC').
    Returns float price of base in terms of quote.
    """
    try:
        response = requests.get(
            f'{BASE_URL}/api/v3/ticker/price',
            params={'symbol': pair}
        )
        response.raise_for_status()
        data = response.json()
        return float(data.get("price", 0))
    except Exception as e:
        print(f"[ERROR] Failed to get price for {pair}: {e}")
        return 0.0

def get_margin_account_info(api_key, secret_key, base_symbol, quote_symbol, debug=False):
    """
    Fetch margin account info but only print the relevant base/quote assets if debug=True.
    """
    try:
        timestamp = int(time.time() * 1000)
        query_string = f'timestamp={timestamp}'
        signature = hmac.new(
            secret_key.encode(),
            query_string.encode(),
            hashlib.sha256
        ).hexdigest()
        query_string += f'&signature={signature}'
        headers = {'X-MBX-APIKEY': api_key}

        response = requests.get(
            f'{BASE_URL}/sapi/v1/margin/account',
            headers=headers,
            params=query_string
        )
        response.raise_for_status()
        account_info = response.json()

        if debug:
            user_assets = account_info.get("userAssets", [])
            relevant_assets = [
                x
                for x in user_assets
                if x["asset"] in [base_symbol, quote_symbol]
            ]
            print("[DEBUG] Margin Assets (base/quote):")
            print(json.dumps(relevant_assets, indent=4))

        return account_info
    except Exception as e:
        print(f"[ERROR] An error occurred in get_margin_account_info: {e}")
        return None

def sync_server_time(client):
    """Sync local system time with Binance server to avoid timestamp errors."""
    try:
        server_time_info = client.get_server_time()
        server_time = server_time_info['serverTime']  # ms
        local_time = int(time.time() * 1000)          # ms
        client.time_offset = server_time - local_time
        print(f"[Time Sync] Offset: {client.time_offset/1000:.3f}s")
    except Exception as e:
        print(f"Failed to sync server time: {e}")
        raise

def place_order_with_retry(client, trading_pair, order_size, max_retries=3):
    """
    Place a BUY margin MARKET order (quoteOrderQty=order_size),
    retrying if we hit a timestamp error (-1021).
    """
    for attempt in range(1, max_retries + 1):
        try:
            order = client.create_margin_order(
                symbol=trading_pair,
                side='BUY',
                type='MARKET',
                quoteOrderQty=order_size
            )
            return order
        except BinanceAPIException as e:
            if e.code == -1021:  # Timestamp for this request is outside recvWindow
                print(f"Attempt {attempt}: Timestamp error. Re-syncing time.")
                sync_server_time(client)
                time.sleep(1)
            else:
                print(f"[ERROR] Binance API on attempt {attempt}: {e.message} (Code: {e.code})")
                raise
        except BinanceRequestException as e:
            print(f"[ERROR] Binance Request on attempt {attempt}: {e}")
            raise
        except Exception as e:
            print(f"[ERROR] General error on attempt {attempt}: {e}")
            raise

    raise Exception("Failed to place order after several timestamp errors.")

def write_slippage_to_file(slippage_percent):
    """
    Append the slippage (in percentage) to SLIPPAGE_FILE with a timestamp.
    """
    try:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(SLIPPAGE_FILE, "a") as f:
            f.write(f"{now_str} - Slippage: {slippage_percent:.4f}%\n")
    except Exception as e:
        print(f"[ERROR] Could not write slippage to file: {e}")

# ------------------- MAIN SCRIPT ------------------- #
def main():
    print("Executing Margin BUY order script...")
    home_dir = Path.home()

    try:
        # 1) Load config
        with open(f"{home_dir}/pablitos-money-printer/src/dist/apikey-crypto.json", "r") as f:
            api_keys = json5.load(f)

        api_key = api_keys.get('key')
        api_secret = api_keys.get('secret')
        trading_pair = api_keys.get('pair', "SUIUSDC")
        # 'margin' here means how many multiples of your own portion you want to borrow
        leverage_strength = float(api_keys.get('margin', 1))

        account_shared_str = api_keys.get('account_shared_x', "1")
        number_sim_orders_str = api_keys.get('number_sim_orders', "2")

        # Convert
        account_shared_x = max(float(account_shared_str), 1.0)
        number_sim_orders = max(int(number_sim_orders_str), 1)

        if not all([api_key, api_secret, trading_pair]):
            raise ValueError("Missing 'key', 'secret', or 'pair' in JSON config.")

        # 2) Parse pair => base/quote
        base_symbol, quote_symbol = parse_pair(trading_pair)
        print(f"[INFO] Base:  {base_symbol}, Quote: {quote_symbol}")

        # 3) Create client & sync time
        client = Client(api_key, api_secret)
        sync_server_time(client)

        # 4) Fetch margin account info
        account_info = get_margin_account_info(api_key, api_secret, base_symbol, quote_symbol, debug=True)
        if not account_info:
            raise Exception("[ERROR] Could not fetch margin account info. Exiting.")

        # 5) Get price of BASE in QUOTE
        base_quote_price = get_price_from_binance(trading_pair)
        if base_quote_price <= 0:
            print("[WARNING] Could not get price. Equity calc may be inaccurate.")

        # ------------------------------------------------------------
        # 6) Calculate total equity in QUOTE
        #    - If account_shared_x == 1 => only use netAsset(USDC)
        #    - Else => netAsset(USDC) + netAsset(BASE)*price
        # ------------------------------------------------------------
        user_assets = account_info.get("userAssets", [])
        quote_asset_info = next((a for a in user_assets if a["asset"] == quote_symbol), None)
        base_asset_info  = next((a for a in user_assets if a["asset"] == base_symbol), None)

        net_quote = float(quote_asset_info.get("netAsset", 0)) if quote_asset_info else 0.0
        net_base  = float(base_asset_info.get("netAsset", 0))  if base_asset_info  else 0.0

        if account_shared_x == 1:
            # Use only USDC
            total_equity_quote = math.floor(net_quote)
            print(f"[INFO] account_shared_x=1 => Using ONLY net USDC = {total_equity_quote}")
        else:
            # Old logic: base + quote
            total_equity_quote = math.floor(net_quote + (net_base * base_quote_price))
            print(f"[INFO] account_shared_x={account_shared_x} => Using net_quote + (net_base*price) = {total_equity_quote}")

        if total_equity_quote <= 0:
            raise Exception("Total equity is 0 or negative. Stopping.")

        # 7) Determine portion for this strategy
        portion_equity = math.floor(total_equity_quote / account_shared_x)
        print(f"[INFO] portion_equity: {portion_equity} (out of {total_equity_quote} total)")

        if portion_equity <= 0:
            raise Exception("Calculated portion is 0 or negative. Check 'account_shared_x'.")

        # ---------------------------------------------------------------
        # (B) Margin logic: margin=4 means you borrow 4× portion, total 5×
        # ---------------------------------------------------------------
        target_balance = portion_equity * (1 + leverage_strength)
        borrow_amount  = portion_equity * leverage_strength

        print(f"[INFO] leverage_strength={leverage_strength} => total_funds={target_balance}, borrowed={borrow_amount:.2f}")

        # 8) Check max borrowable
        try:
            max_borrowable_info = client.get_max_margin_loan(asset=quote_symbol)
            max_borrowable = float(max_borrowable_info.get('amount', 0.0))
        except Exception as e:
            print("[ERROR] Could not fetch max borrowable info.")
            raise

        if borrow_amount > max_borrowable:
            print(f"[WARNING] Attempted to borrow {borrow_amount:.2f}, exceeding max={max_borrowable:.2f}.")
            print("Falling back to no borrow.")
            borrow_amount = 0

        # 9) Borrow if needed
        if borrow_amount > 0:
            borrow_amount = math.floor(borrow_amount)
            try:
                client.create_margin_loan(asset=quote_symbol, amount=borrow_amount)
                print(f"[INFO] Borrowed {borrow_amount} {quote_symbol}")
            except BinanceAPIException as e:
                print(f"[ERROR] Failed to borrow: {e.message} (Code: {e.code})")
                raise

        # So total QUOTE we have to spend:
        total_quote_for_order = math.floor(portion_equity + borrow_amount)

        # 10) Split into multiple orders
        num_orders = number_sim_orders
        order_size = math.floor(total_quote_for_order / num_orders)

        if order_size <= 0:
            raise Exception("Order size is 0 or negative. Can't execute buy.")

        print(f"[INFO] Placing {num_orders} BUY orders, each for {order_size} {quote_symbol}...")

        for i in range(1, num_orders + 1):
            # Capture the price just before placing each order:
            price_before_order = get_price_from_binance(trading_pair)

            try:
                print(f" - Order {i}/{num_orders} => {order_size} {quote_symbol}")
                order_resp = place_order_with_retry(client, trading_pair, order_size)
                print(f"   [OK] orderId={order_resp.get('orderId')}")

                # ------------------
                # Calculate slippage
                # ------------------
                # For a filled order, we can calculate:
                # average fill price = cummulativeQuoteQty / executedQty
                executed_qty_str   = order_resp.get('executedQty', '0')
                cumm_quote_qty_str = order_resp.get('cummulativeQuoteQty', '0')
                try:
                    executed_qty   = float(executed_qty_str)
                    cumm_quote_qty = float(cumm_quote_qty_str)
                    if executed_qty > 0:
                        avg_fill_price = cumm_quote_qty / executed_qty
                        # slippage% = ((fill_price - expected_price) / expected_price) * 100
                        slippage = ((avg_fill_price - price_before_order) / price_before_order) * 100
                        write_slippage_to_file(slippage)
                    else:
                        print("[WARNING] No executed quantity; cannot compute slippage.")
                except ValueError:
                    print("[ERROR] Could not parse fill quantities for slippage calculation.")

                time.sleep(1)
            except Exception as e:
                print(f"[ERROR] Could not place order {i}: {e}")
                break

    except BinanceAPIException as e:
        print(f"[ERROR] Binance API Exception: {e.message} (Code:{e.code})")
    except BinanceRequestException as e:
        print(f"[ERROR] Binance Request Exception: {e}")
    except Exception as e:
        print(f"[ERROR] General Exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
