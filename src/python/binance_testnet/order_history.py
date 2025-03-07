import os
import json5
from datetime import datetime, timezone
from binance.client import Client
from tqdm import tqdm
from collections import defaultdict

# Define paths
config_file = "../../dist/apikey-crypto.json"
output_file = "../../view/output/history_summary.txt"

# Ensure the output directory exists
os.makedirs(os.path.dirname(output_file), exist_ok=True)

# Read the JSON configuration file
with open(config_file, "r") as json_file:
    config = json5.load(json_file)
    start_date_str = config.get("start_date")  
    end_date_str = config.get("end_date")      
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

    # Group trades by order ID
    order_summary = defaultdict(lambda: {"symbol": "", "total_qty": 0, "total_price": 0, "fees": 0, "side": "", "prices": []})

    for trade in tqdm(orders, desc="Processing orders"):
        order_id = trade["orderId"]
        qty = float(trade["qty"])
        price = float(trade["price"])
        fee = float(trade["commission"])
        side = "BUY" if trade["buyer"] else "SELL"
        symbol = trade["symbol"]

        # Update grouped summary
        order_summary[order_id]["symbol"] = symbol
        order_summary[order_id]["total_qty"] += qty
        order_summary[order_id]["total_price"] += price * qty
        order_summary[order_id]["fees"] += fee
        order_summary[order_id]["side"] = side
        order_summary[order_id]["prices"].append(price)

    # Select one real order (first in the list)
    if order_summary:
        first_order_id, summary = next(iter(order_summary.items()))

        # Compute average entry price
        avg_entry_price = summary["total_price"] / summary["total_qty"] if summary["total_qty"] > 0 else 0

        # Fetch latest market price for PNL calculation
        symbol = summary["symbol"]
        market_price = float(client.futures_symbol_ticker(symbol=symbol)["price"])

        # Compute PNL
        if summary["side"] == "BUY":
            pnl = (market_price - avg_entry_price) * summary["total_qty"]
        else:  # SELL order
            pnl = (avg_entry_price - market_price) * summary["total_qty"]

        # Net PNL after fees
        net_pnl = pnl - summary["fees"]

        # Format the output
        order_data = {
            "Order ID": first_order_id,
            "Symbol": symbol,
            "Total Quantity": round(summary["total_qty"], 4),
            "Average Entry Price": round(avg_entry_price, 4),
            "Market Price": round(market_price, 4),
            "Total Fees": round(summary["fees"], 4),
            "Gross PNL": round(pnl, 4),
            "Net PNL": round(net_pnl, 4),
            "Side": summary["side"],
        }

        # Save the summary to a file
        with open(output_file, "w") as f:
            f.write(json5.dumps(order_data, indent=4))

        print(f"Order summary saved to {output_file}")

    else:
        print("No orders found in the given date range.")

except Exception as e:
    print(f"Error fetching trade history: {e}")
