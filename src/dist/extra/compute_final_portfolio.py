#!/usr/bin/env python3

import os
import json5
from datetime import datetime

# File paths
API_KEY_FILE = "apikey-crypto.json"
ASSET_FILE = "../view/output/asset.txt"
TRADES_FILE = "../view/output/trades.txt"
PORTFOLIO_FILE = "../view/output/portfolio.txt"
COSTS_FILE = "../view/output/costs.txt"

def load_api_data(file_path):
    """
    Load API key data with:
      - investment
      - margin
      - annual interest rate
      - trade fee percentage
      - slippage percentage
    """
    with open(file_path, "r") as f:
        api_data = json5.load(f)
    investment = float(api_data["investment"])
    margin = float(api_data["margin"])
    annual_interest_rate = float(api_data["margin_annual_interest_percentage"]) / 100
    trade_fee_percentage = float(api_data.get("trade_fee_percentage", 0.1)) / 100
    
    # Load slippage_percent, default to 0 if not found
    slippage_percent = float(api_data.get("slippage_percent", 0.0)) / 100
    
    return investment, margin, annual_interest_rate, trade_fee_percentage, slippage_percent

def load_asset_data(file_path):
    """Load asset data as a dictionary of prices and events."""
    price_dict = {}
    asset_events = []
    with open(file_path, "r") as f:
        for line in f:
            timestamp, closing_price = map(float, line.strip().split(","))
            timestamp = int(timestamp)
            price_dict[timestamp] = closing_price
            asset_events.append((timestamp, 'price', closing_price))
    return price_dict, asset_events

def load_trade_data(file_path):
    """Load trade data as a list of trade events, ignoring additional parameters."""
    trade_events = []
    with open(file_path, "r") as f:
        for line in f:
            parts = line.strip().split(",")
            timestamp, action = int(parts[0]), parts[1]
            trade_events.append((timestamp, 'trade', action))
    return trade_events

def accrue_interest(debt, annual_interest_rate, time_diff_seconds, cash_balance):
    """
    Calculate and return:
      1) The updated debt
      2) The updated cash_balance
      3) The interest accrued in this period
    
    We deduct interest from USDC if possible. If there's not enough,
    the remainder is added to 'debt'.
    """
    if debt <= 0:
        # No debt => no interest
        return debt, cash_balance, 0.0

    # Convert annual interest rate to a per-second compounded rate
    seconds_per_year = 365 * 24 * 3600
    per_second_rate = (1 + annual_interest_rate) ** (1 / seconds_per_year) - 1

    # Calculate compound interest over the time_diff_seconds
    interest_for_period = debt * ((1 + per_second_rate) ** time_diff_seconds - 1)

    # Attempt to pay interest from USDC
    if cash_balance >= interest_for_period:
        cash_balance -= interest_for_period
    else:
        shortfall = interest_for_period - cash_balance
        cash_balance = 0.0
        debt += shortfall

    return debt, cash_balance, interest_for_period

def process_events(
    events, 
    price_dict, 
    investment, 
    margin, 
    annual_interest_rate, 
    trade_fee_percentage,
    slippage_percent
):
    """
    Simulate trades (buy/sell) and margin interest, then produce portfolio values,
    now with fees deducted from USDC (or added to debt if USDC is insufficient).
    
    Steps:
      - 'buy': use up to (cash_balance + margin * cash_balance) to buy.
               pay fee from USDC balance.
               if not enough USDC to pay fee, add shortfall to debt.
      - 'sell': sell all shares, pay fee from proceeds.
               if proceeds don't cover fee, add shortfall to debt.
      - interest: on each price or trade event, we accrue interest on 'debt'.
    """
    number_of_shares = 0.0
    cash_balance = investment
    debt = 0.0

    portfolio_data = []
    total_interest_cost = 0.0
    total_fees_cost = 0.0

    # Keep track of last event timestamp for accruing interest
    last_timestamp = None
    last_net_value = investment

    for timestamp, event_type, data in events:
        # First, accrue interest since the last event (if any)
        if last_timestamp is not None:
            time_diff = timestamp - last_timestamp
            debt, cash_balance, interest_accrued = accrue_interest(
                debt, 
                annual_interest_rate, 
                time_diff, 
                cash_balance
            )
            total_interest_cost += interest_accrued

        if event_type == 'price':
            # Update net portfolio value based on current price
            current_price = data
            net_value = number_of_shares * current_price + cash_balance - debt
            last_net_value = net_value
            portfolio_data.append((timestamp, net_value))

        elif event_type == 'trade':
            current_price = price_dict[timestamp]

            if data == 'buy':
                # Slippage: buy at a slightly higher price
                buy_price = current_price * (1 + slippage_percent)

                # The maximum total funds (cash + borrowed)
                max_funds_for_buy = cash_balance * (1 + margin)

                # The fee is a percentage of the *total amount we are about to deploy*
                fee_in_usdc = max_funds_for_buy * trade_fee_percentage
                total_fees_cost += fee_in_usdc  # track for reporting

                # Pay that fee from cash if possible
                if cash_balance >= fee_in_usdc:
                    cash_balance -= fee_in_usdc
                else:
                    shortfall = fee_in_usdc - cash_balance
                    cash_balance = 0.0
                    debt += shortfall

                # Now that we've paid the fee, the actual funds left to buy with:
                actual_funds_for_buy = max_funds_for_buy - fee_in_usdc

                # Borrowed portion is whatever we used beyond our new cash_balance
                # But be careful, we just subtracted some fee from cash_balance, so:
                #   borrowed = (actual_funds_for_buy) - (cash_balance before paying fee).
                # It's simpler to just say:
                borrowed = actual_funds_for_buy - (cash_balance)
                if borrowed < 0:
                    borrowed = 0.0  # means we didn't need to borrow

                debt += borrowed

                # Buy shares
                shares_to_buy = 0.0
                if buy_price > 0:
                    shares_to_buy = actual_funds_for_buy / buy_price
                number_of_shares += shares_to_buy

                # We used all available funds to buy
                cash_balance = 0.0

            elif data == 'sell':
                # Slippage: sell at a slightly lower price
                sell_price = current_price * (1 - slippage_percent)

                # Sell all shares
                proceeds = number_of_shares * sell_price

                # Fee is a percentage of the total proceeds
                fee_in_usdc = proceeds * trade_fee_percentage
                total_fees_cost += fee_in_usdc

                # Reset shares
                number_of_shares = 0.0

                if proceeds >= fee_in_usdc:
                    net_after_fee = proceeds - fee_in_usdc
                else:
                    # Not enough to cover fee => shortfall goes to debt
                    shortfall = fee_in_usdc - proceeds
                    net_after_fee = 0.0
                    debt += shortfall

                # Use net proceeds to pay down debt first
                if net_after_fee >= debt:
                    cash_balance += (net_after_fee - debt)
                    debt = 0.0
                else:
                    debt -= net_after_fee
                    cash_balance += 0.0

            # Recompute net value
            net_value = number_of_shares * current_price + cash_balance - debt
            last_net_value = net_value
            portfolio_data.append((timestamp, net_value))

        else:
            # If it's not a price or trade event, just keep the last known value
            portfolio_data.append((timestamp, last_net_value))

        last_timestamp = timestamp

    return portfolio_data, total_interest_cost, total_fees_cost

def save_portfolio_data(portfolio_data, file_path):
    """Save portfolio values to a file."""
    with open(file_path, "w") as f:
        for timestamp, value in portfolio_data:
            f.write(f"{timestamp},{value:.2f}\n")

def format_with_upticks(value, currency="$usdc"):
    """
    Convert a float to a string with 2 decimal places and 
    use upticks `'` for thousands separators, then append a currency unit.
    """
    base_formatted = "{:,.2f}".format(value)
    with_upticks = base_formatted.replace(",", "'")
    return f"{with_upticks} {currency}"

def save_costs_data(
    total_interest_cost, 
    total_fees_cost, 
    final_portfolio_value, 
    portfolio_including_fees, 
    file_path
):
    """
    Save cost variables to a file, with upticks and currency appended.
    """
    with open(file_path, "w") as f:
        f.write(f"total_interest_cost,{format_with_upticks(total_interest_cost, '$usdc')}\n")
        f.write(f"total_fees_cost,{format_with_upticks(total_fees_cost, '$usdc')}\n")
        f.write(f"final_portfolio,{format_with_upticks(final_portfolio_value, '$usdc')}\n")
        f.write(f"portfolio_including_fees,{format_with_upticks(portfolio_including_fees, '$usdc')}\n")

def main():
    os.makedirs(os.path.dirname(PORTFOLIO_FILE), exist_ok=True)

    # Load config
    (
        investment, 
        margin, 
        annual_interest_rate, 
        trade_fee_percentage, 
        slippage_percent
    ) = load_api_data(API_KEY_FILE)
     
    # Load data
    price_dict, asset_events = load_asset_data(ASSET_FILE)
    trade_events = load_trade_data(TRADES_FILE)

    # Merge all events by timestamp
    events = sorted(asset_events + trade_events, key=lambda x: x[0])

    # Run the simulation
    portfolio_data, total_interest_cost, total_fees_cost = process_events(
        events, 
        price_dict, 
        investment, 
        margin, 
        annual_interest_rate, 
        trade_fee_percentage,
        slippage_percent
    )

    # Final portfolio value
    final_portfolio_value = portfolio_data[-1][1] if portfolio_data else 0.0

    # A convenience metric: final minus total_fees, if you want to see
    # the effect of fees netted out of the final
    portfolio_including_fees = final_portfolio_value  # Because we already deducted fees

    # Save portfolio results
    save_portfolio_data(portfolio_data, PORTFOLIO_FILE)
    print(f"Portfolio data saved to {PORTFOLIO_FILE}")

    # Save cost results
    save_costs_data(
        total_interest_cost, 
        total_fees_cost,
        final_portfolio_value,
        portfolio_including_fees,
        COSTS_FILE
    )
    print(f"Costs data saved to {COSTS_FILE}")

if __name__ == "__main__":
    main()
