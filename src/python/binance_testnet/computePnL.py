#!/usr/bin/env python3
import ast
import os
import re

# Define file paths relative to this script
order_entries_file = "../../view/output/orders.txt"
order_exits_file = "../../view/output/closes.txt"
pnl_file = "../../view/output/PnL.txt"

# Fee rate: 0.1% per leg (open and close)
FEE_RATE = 0.001

def parse_order_line(line):
    """
    Parse a single order line from orders.txt.
    It handles lines containing "Order:", "Short Order:" or "Long Order:".
    """
    if "Short Order:" in line:
        order_type = "short"
        pattern = r"Short Order:\s*(\{.*\})"
    elif "Long Order:" in line:
        order_type = "long"
        pattern = r"Long Order:\s*(\{.*\})"
    elif "Order:" in line:
        # For a generic order, determine type by the 'side' field.
        order_type = None
        pattern = r"Order:\s*(\{.*\})"
    else:
        return None

    match = re.search(pattern, line)
    if match:
        order_str = match.group(1)
        try:
            order_data = ast.literal_eval(order_str)
            if order_type is None:
                # Determine type based on side: BUY is assumed long, SELL is short.
                if order_data.get('side') == 'BUY':
                    order_type = "long"
                elif order_data.get('side') == 'SELL':
                    order_type = "short"
                else:
                    order_type = "unknown"
            return {
                'type': order_type,
                'price': float(order_data.get('avgPrice', 0)),
                'quantity': float(order_data.get('origQty', 0)),
                'timestamp': line.split(" - ")[0]
            }
        except Exception as e:
            print(f"Error parsing order line:\n{line}\nError: {e}")
            return None
    return None

def parse_orders(file_path):
    """
    Parses the orders.txt file.
    It now handles lines with "Available USDT Balance before order:" and order lines.
    The first encountered available balance is used as the starting portfolio value.
    """
    orders = []
    starting_balance = None
    if not os.path.exists(file_path):
        print(f"Orders file not found: {file_path}")
        return orders, starting_balance
    with open(file_path, "r") as f:
        for line in f:
            if "Available USDT Balance before order:" in line:
                try:
                    parts = line.split("Available USDT Balance before order:")
                    balance_str = parts[1].strip()
                    balance = float(balance_str)
                    if starting_balance is None:
                        starting_balance = balance
                except Exception as e:
                    print(f"Error parsing available balance line:\n{line}\nError: {e}")
                continue  # Skip balance lines for order parsing.
            # Process order lines
            if "Short Order:" in line or "Long Order:" in line or "Order:" in line:
                order = parse_order_line(line)
                if order:
                    orders.append(order)
    return orders, starting_balance

def parse_closes(file_path):
    """
    Parses the closes.txt file. The file contains blocks like:
    
    2025-03-07 ... - Close LONG position on BTCUSDT:
    Immediate response: {...}
    Queried order status: {...}
    
    The script uses the "Close LONG/SHORT" line to set the trade type and then
    parses the "Queried order status:" line for the actual closing data.
    """
    closes = []
    if not os.path.exists(file_path):
        print(f"Closes file not found: {file_path}")
        return closes
    current_close_type = None
    with open(file_path, "r") as f:
        for line in f:
            if "Close LONG position" in line:
                current_close_type = "long"
            elif "Close SHORT position" in line:
                current_close_type = "short"
            if "Queried order status:" in line:
                pattern = r"Queried order status:\s*(\{.*\})"
                match = re.search(pattern, line)
                if match:
                    order_str = match.group(1)
                    try:
                        order_data = ast.literal_eval(order_str)
                        close_price = float(order_data.get('avgPrice', 0))
                        quantity = float(order_data.get('executedQty', 0))
                        closes.append({
                            'type': current_close_type,
                            'price': close_price,
                            'quantity': quantity,
                            'timestamp': line.split(" - ")[0]
                        })
                    except Exception as e:
                        print(f"Error parsing close line:\n{line}\nError: {e}")
    return closes

def match_trades(opens, closes):
    """
    Pairs open and close orders by type (long/short) in chronological order.
    Only pairs as many orders as exist in both lists.
    """
    long_opens = [o for o in opens if o['type'] == 'long']
    short_opens = [o for o in opens if o['type'] == 'short']
    long_closes = [c for c in closes if c['type'] == 'long']
    short_closes = [c for c in closes if c['type'] == 'short']

    trades = []
    # Pair long orders
    for open_order, close_order in zip(long_opens, long_closes):
        trade = {
            'type': 'long',
            'open_price': open_order['price'],
            'close_price': close_order['price'],
            'quantity': open_order['quantity']
        }
        trades.append(trade)
    # Pair short orders
    for open_order, close_order in zip(short_opens, short_closes):
        trade = {
            'type': 'short',
            'open_price': open_order['price'],
            'close_price': close_order['price'],
            'quantity': open_order['quantity']
        }
        trades.append(trade)
    return trades

def compute_pnl(trades, starting_balance):
    """
    Computes the total PnL, deducts fees, and calculates percentage PnL
    based on the starting portfolio value (available USDT balance).
    
    For long trades: pnl = (close_price - open_price) * quantity
    For short trades: pnl = (open_price - close_price) * quantity
    Fees are computed on both legs as: fee = FEE_RATE * (open_price * quantity + close_price * quantity)
    
    Final portfolio value = starting_balance + net_pnl.
    """
    total_pnl = 0.0
    total_fees = 0.0
    for trade in trades:
        open_price = trade['open_price']
        close_price = trade['close_price']
        qty = trade['quantity']
        if trade['type'] == 'long':
            pnl = (close_price - open_price) * qty
        elif trade['type'] == 'short':
            pnl = (open_price - close_price) * qty
        else:
            pnl = 0.0
        fees = FEE_RATE * ((open_price * qty) + (close_price * qty))
        total_pnl += pnl
        total_fees += fees

    net_pnl = total_pnl - total_fees
    pct_pnl = (net_pnl / starting_balance * 100) if starting_balance != 0 else 0.0
    final_portfolio = starting_balance + net_pnl
    return total_pnl, total_fees, net_pnl, pct_pnl, starting_balance, final_portfolio

def output_results(file_path, total_pnl, total_fees, net_pnl, pct_pnl, initial_portfolio, final_portfolio):
    output_lines = []
    output_lines.append("----- PnL Report -----")
    output_lines.append(f"Initial Portfolio Value: {initial_portfolio:.2f}")
    output_lines.append(f"Final Portfolio Value:   {final_portfolio:.2f}")
    output_lines.append(f"Total Raw PnL:           {total_pnl:.2f}")
    output_lines.append(f"Total Fees Deducted:     {total_fees:.2f}")
    output_lines.append(f"Net PnL after fees:      {net_pnl:.2f}")
    output_lines.append(f"Percentage PnL:          {pct_pnl:.2f}%")
    report = "\n".join(output_lines)

    # Write to file
    try:
        with open(file_path, "w") as f:
            f.write(report)
    except Exception as e:
        print(f"Error writing to file {file_path}: {e}")

    # Output to terminal
    print(report)

def main():
    orders, starting_balance = parse_orders(order_entries_file)
    closes = parse_closes(order_exits_file)
    
    if starting_balance is None:
        print("Starting USDT balance not found in orders file.")
        return
    if not orders:
        print("No orders found.")
        return
    if not closes:
        print("No closes found.")
        return

    trades = match_trades(orders, closes)
    total_pnl, total_fees, net_pnl, pct_pnl, initial_portfolio, final_portfolio = compute_pnl(trades, starting_balance)
    output_results(pnl_file, total_pnl, total_fees, net_pnl, pct_pnl, initial_portfolio, final_portfolio)

if __name__ == "__main__":
    main()
