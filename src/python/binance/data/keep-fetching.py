#!/usr/bin/env python3

import argparse
import math
import time
from pathlib import Path
from datetime import date
import json5
import requests
import pandas as pd
import websocket
from tqdm import tqdm  # for progress bar

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------

# 1-minute interval
INTERVAL = "1m"
# Number of days of historical data to fetch (default 18)
DAYS_OF_DATA = 18
# Limit per Binance klines API call
LIMIT_PER_CALL = 1000

# ----------------------------------------------------------------------------
# Define CSV columns
# ----------------------------------------------------------------------------

COLUMNS = [
    "Timestamp", "Open", "High", "Low", "Close", "Volume",
    "QuoteAssetVolume", "TakerBuyBaseVolume", "TakerBuyQuoteVolume",
    "NumberOfTrades"
]

# ----------------------------------------------------------------------------
# Parse command-line arguments
# ----------------------------------------------------------------------------

parser = argparse.ArgumentParser(
    description="Fetch historical Binance klines for a given trading pair, then optionally open a WebSocket to continuously append real-time data."
)
parser.add_argument("--once", action="store_true",
                    help="If specified, only fetch historical data (Nov 29, 2024 to today) and exit. No WebSocket streaming.")
args = parser.parse_args()

# ----------------------------------------------------------------------------
# Load the trading pair from apikey-crypto.json
# ----------------------------------------------------------------------------

home_dir = Path.home()
with open(f"{home_dir}/CRYPTO-Trader/src/dist/apikey-crypto.json", "r") as file:
    config = json5.load(file)
    if "pair" not in config:
        raise ValueError("The 'pair' key is missing in apikey-crypto.json")
    symbol = config["pair"].lower()  # Convert to lowercase for Binance's WebSocket API

# ----------------------------------------------------------------------------
# Paths and URLs
# ----------------------------------------------------------------------------

WS_URL = f"wss://stream.binance.com:9443/ws/{symbol}@kline_{INTERVAL}"
CSV_FILENAME = f"../../../assets/{symbol}-realtime.csv"

# ----------------------------------------------------------------------------
# Historical Data Fetch Function
# ----------------------------------------------------------------------------

def fetch_historical_data(num_days):
    """
    Fetch num_days of 1m historical data from Binance.
    Downloads data in 1,000-point chunks until we reach the required total.
    Clears the CSV file before writing newly fetched data.
    """
    # Clear the file contents before writing
    open(CSV_FILENAME, 'w').close()

    base_url = "https://api.binance.com/api/v3/klines"

    # Calculate total points needed for the specified num_days
    total_points = num_days * 24 * 60  # minutes in a day

    # Figure out how many calls we need (each call can return up to LIMIT_PER_CALL klines)
    calls = math.ceil(total_points / LIMIT_PER_CALL)

    # Set the initial end time to 'now' in milliseconds
    end_time = int(time.time() * 1000)

    all_data = []

    progress_bar_format = "\x1b[92m{l_bar}{bar}\x1b[0m"
    print(f"Downloading ~{total_points} klines ({num_days} days).")

    for _ in tqdm(range(calls), desc="Downloading klines", bar_format=progress_bar_format):
        params = {
            "symbol": symbol.upper(),
            "interval": INTERVAL,
            "endTime": end_time,
            "limit": LIMIT_PER_CALL
        }
        response = requests.get(base_url, params=params)
        data = response.json()

        # Check for API errors
        if not isinstance(data, list):
            print(f"Error fetching historical data: {data}")
            return

        # Append this batch of data
        all_data.extend(data)

        # Update end_time for the next iteration to the oldest openTime in this batch - 1 ms
        oldest_open_time = data[0][0]
        end_time = oldest_open_time - 1

    # Convert the fetched data into a DataFrame
    df = pd.DataFrame(all_data, columns=[
        "Timestamp", "Open", "High", "Low", "Close", "Volume", "CloseTime",
        "QuoteAssetVolume", "NumberOfTrades", "TakerBuyBaseVolume",
        "TakerBuyQuoteVolume", "Ignore"
    ])

    # Keep only relevant columns
    df = df[[
        "Timestamp", "Open", "High", "Low", "Close", "Volume",
        "QuoteAssetVolume", "TakerBuyBaseVolume", "TakerBuyQuoteVolume",
        "NumberOfTrades"
    ]]

    # Convert Timestamp from milliseconds to seconds
    df["Timestamp"] = df["Timestamp"] // 1000
    df["Timestamp"] = df["Timestamp"].astype(int)

    # Convert numeric columns
    float_cols = [
        "Open", "High", "Low", "Close", "Volume",
        "QuoteAssetVolume", "TakerBuyBaseVolume", "TakerBuyQuoteVolume"
    ]
    for col in float_cols:
        df[col] = df[col].astype(float)
    df["NumberOfTrades"] = df["NumberOfTrades"].astype(int)

    # Sort the DataFrame by Timestamp ascending
    df = df.sort_values("Timestamp").reset_index(drop=True)

    # Remove duplicates if any overlap
    df = df.drop_duplicates(subset="Timestamp")

    # If there's more than total_points rows, truncate to the last total_points
    if len(df) > total_points:
        df = df.iloc[-total_points:]

    # Save to CSV with '|' as the separator and no header
    df.to_csv(CSV_FILENAME, sep='|', index=False, header=False)
    print(f"Saved {len(df)} historical data points ({num_days} days) to {CSV_FILENAME} "
          f"with '|' as the separator, no header.")

# ----------------------------------------------------------------------------
# WebSocket Callbacks
# ----------------------------------------------------------------------------

def on_message(ws, message):
    data = json5.loads(message)
    kline = data['k']
    is_kline_closed = kline['x']
    if is_kline_closed:
        timestamp = int(kline['t'] // 1000)  # Convert to seconds
        open_price = float(kline['o'])
        high_price = float(kline['h'])
        low_price = float(kline['l'])
        close_price = float(kline['c'])
        volume = float(kline['v'])
        quote_asset_volume = float(kline['q'])
        taker_buy_base_volume = float(kline['V'])
        taker_buy_quote_volume = float(kline['Q'])
        number_of_trades = int(kline['n'])

        # Read the existing data from the CSV (with column names for convenience)
        df = pd.read_csv(CSV_FILENAME, sep='|', header=None, names=COLUMNS, engine='python')

        # If you want to maintain a rolling window, remove the first row:
        if len(df) > 0:
            df = df.iloc[1:]

        # Create a new DataFrame row for the new data
        new_data = pd.DataFrame([[
            timestamp, open_price, high_price, low_price, close_price, volume,
            quote_asset_volume, taker_buy_base_volume, taker_buy_quote_volume,
            number_of_trades
        ]], columns=COLUMNS)

        # Append the new data
        df = pd.concat([df, new_data], ignore_index=True)

        # Save back to the CSV file
        df.to_csv(CSV_FILENAME, sep='|', index=False, header=False)

        print(f"Appended data - Timestamp: {timestamp}, "
              f"O: {open_price}, H: {high_price}, L: {low_price}, C: {close_price}, "
              f"V: {volume}, QAV: {quote_asset_volume}, "
              f"TBBAV: {taker_buy_base_volume}, TBQAV: {taker_buy_quote_volume}, "
              f"NoT: {number_of_trades}")

def on_open(ws):
    print("WebSocket connection opened. Listening for new klines...")

def on_close(ws, close_status_code, close_msg):
    print("WebSocket connection closed")

# ----------------------------------------------------------------------------
# Main Execution
# ----------------------------------------------------------------------------

if __name__ == "__main__":
    # Default is 18 days
    days_to_fetch = DAYS_OF_DATA

    # If --once is specified, compute days from Nov 29, 2024 to today
    if args.once:
        nov_29_2024 = date(2024, 11, 29)
        today = date.today()
        diff_days = (today - nov_29_2024).days
        # If diff_days is negative (running before Nov 29, 2024), just use 1 day fallback
        if diff_days < 1:
            diff_days = 1
        
        days_to_fetch = diff_days
        print(f"Running with --once. Fetching ~{days_to_fetch} days of data from Nov 29, 2024 to today.")

    # Fetch historical data
    fetch_historical_data(days_to_fetch)

    # If --once is specified, then exit after fetching data
    if args.once:
        print("Finished fetching historical data. Exiting (because --once is set).")
        exit(0)

    # Otherwise, start the WebSocket to keep appending new 1m klines
    while True:
        ws = websocket.WebSocketApp(
            WS_URL,
            on_message=on_message,
            on_open=on_open,
            on_close=on_close
        )
        ws.run_forever()
        # Sleep 1 second before attempting a reconnect if the socket closes
        time.sleep(1)
