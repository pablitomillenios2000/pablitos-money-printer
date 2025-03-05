#!/usr/bin/env python3

import requests
import time
import hmac
import hashlib
import json5
import json
from pathlib import Path

# ------------------------------------------------------------------------------
# 1. LOAD API KEYS AND PAIR FROM JSON5
# ------------------------------------------------------------------------------
home_dir = Path.home()
home_dir = '/home/g1pablo_escaida1/'
with open(f"{home_dir}/pablitos-money-printer/src/dist/apikey-crypto.json", "r") as file:
    config = json5.load(file)

API_KEY = config.get("key")
SECRET_KEY = config.get("secret")
leverage = config.get('margin')  # We'll use this for net equity calculation

outfile = f"{home_dir}pablitos-money-printer/src/view/output/equity.txt"

# Example: if the JSON has "pair": "HBARUSDC"
# We'll parse that down to "HBAR" as the base token.
full_pair = config.get("pair", "HBARUSDC")

BASE_URL = 'https://api.binance.com'

# ------------------------------------------------------------------------------
# 2. PARSE THE BASE TOKEN FROM THE PAIR
# ------------------------------------------------------------------------------
def parse_base_token(pair_str):
    """
    If pair_str is like 'HBARUSDC', strip 'USDC' -> 'HBAR'.
    If the pair doesn't end with 'USDC', adapt the logic accordingly.
    """
    pair_str = pair_str.upper()
    if pair_str.endswith("USDC"):
        return pair_str[:-4]
    # Fallback if format is different
    return pair_str

base_token = parse_base_token(full_pair)

# ------------------------------------------------------------------------------
# 3. SIGNING HELPER FOR BINANCE
# ------------------------------------------------------------------------------
def sign_query(query: str) -> str:
    return hmac.new(SECRET_KEY.encode(), query.encode(), hashlib.sha256).hexdigest()

# ------------------------------------------------------------------------------
# 4. GET CROSS MARGIN ACCOUNT INFO
# ------------------------------------------------------------------------------
def get_cross_margin_account_info():
    """
    Fetch cross margin account info which shows net assets for each coin.
    """
    try:
        timestamp = int(time.time() * 1000)
        query_string = f"timestamp={timestamp}"
        signature = sign_query(query_string)
        query_string += f"&signature={signature}"

        headers = {"X-MBX-APIKEY": API_KEY}
        url = f"{BASE_URL}/sapi/v1/margin/account"
        resp = requests.get(url, headers=headers, params=query_string)

        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"Error (cross margin): {resp.status_code}, {resp.text}")
            return None
    except Exception as e:
        print(f"Error fetching cross margin info: {e}")
        return None

# ------------------------------------------------------------------------------
# 5. MAIN EXECUTION
# ------------------------------------------------------------------------------
def main():
    account_info = get_cross_margin_account_info()
    if not account_info:
        print("Unable to retrieve cross margin account info.")
        return

    # The cross margin info is under account_info["userAssets"], which is a list
    user_assets = account_info.get("userAssets", [])

    # We want to filter for base token (e.g., "HBAR") + "USDC"
    relevant_assets = [
        asset for asset in user_assets
        if asset["asset"] in [base_token.upper(), "USDC"]
    ]

    # --------------------------------------------------------------------------
    # Print the filtered information in JSON format (base token + USDC)
    # --------------------------------------------------------------------------
    print("\nFull Information for the Base Token and USDC:")
    print(json.dumps(relevant_assets, indent=4))

    # --------------------------------------------------------------------------
    # Print netAsset of BNB on a single line (if BNB is present)
    # --------------------------------------------------------------------------
    bnb_info = next((asset for asset in user_assets if asset["asset"] == "BNB"), None)
    if bnb_info:
        print(f"\nBNB netAsset: {bnb_info['netAsset']}")

    # --------------------------------------------------------------------------
    # Compute and print net_equity based on netAsset for USDC, with logic:
    #   - If base_token_net_asset < 1 => net_equity = net_asset_usdc
    #   - Else => net_equity = round(net_asset_usdc / leverage)
    # --------------------------------------------------------------------------
    usdc_info = next((asset for asset in relevant_assets if asset["asset"] == "USDC"), None)
    base_token_info = next((asset for asset in relevant_assets if asset["asset"] == base_token.upper()), None)

    if usdc_info:
        try:
            net_asset_usdc = abs(float(usdc_info["netAsset"]))
            base_token_net_asset = 0.0  # Default if not found

            if base_token_info:
                base_token_net_asset = abs(float(base_token_info["netAsset"]))

            # Decide how to compute net_equity
            if base_token_net_asset < 1:
                net_equity = net_asset_usdc
            else:
                net_equity = round(net_asset_usdc / leverage)

            print(f"\nThe estimated net equity is: ${net_equity}")

            # Write net_equity to file
            with open(outfile, 'w') as f:
                f.write(str(net_equity) + "\n")

        except (ValueError, KeyError, TypeError) as err:
            print(f"\nCould not calculate estimated net equity for USDC: {err}")
    else:
        print("\nNo USDC asset found in the account info to calculate net equity.")

# ------------------------------------------------------------------------------
# 6. EXECUTE MAIN IF RUN DIRECTLY
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    main()
