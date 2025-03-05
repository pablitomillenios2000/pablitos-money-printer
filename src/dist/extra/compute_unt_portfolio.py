import os
import json5

# Define file paths
api_key_file = "apikey-crypto.json"
asset_file = "../view/output/asset.txt"
portfolio_file = "../view/output/untouched_portfolio.txt"  # Updated filename

# Ensure the output directory exists
os.makedirs(os.path.dirname(portfolio_file), exist_ok=True)

# Read the API key JSON file to extract investment
with open(api_key_file, "r") as f:
    api_data = json5.load(f)
    investment = float(api_data["investment"])  # Total investment amount

# Read asset data and calculate portfolio value
portfolio_data = []
with open(asset_file, "r") as f:
    asset_lines = f.readlines()

# Get the initial price to compute number of shares
initial_line = asset_lines[0]
initial_timestamp, initial_closing_price = initial_line.strip().split(",")
initial_closing_price = float(initial_closing_price)
number_of_shares = investment / initial_closing_price

# Now process each line
for line in asset_lines:
    timestamp, closing_price = line.strip().split(",")
    closing_price = float(closing_price)
    
    # Portfolio value is number_of_shares * current closing_price
    portfolio_value = number_of_shares * closing_price
    
    # Store the timestamp and portfolio value
    portfolio_data.append((timestamp, portfolio_value))

# Write the portfolio data to the output file
with open(portfolio_file, "w") as f:
    for timestamp, value in portfolio_data:
        f.write(f"{timestamp},{value:.2f}\n")

print(f"Portfolio data has been processed and saved to {portfolio_file}")
