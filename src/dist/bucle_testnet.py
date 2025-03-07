#!/usr/bin/env python3

import time
import subprocess
import sys

# ANSI escape codes for coloring
PINK = "\033[95m"
RESET = "\033[0m"

while True:
    # Execute recompute.py using python3
    subprocess.run(["python3", "recompute.py"])

    # Execute execute_orders.py using python3
    subprocess.run(["python3", "execute_orders_testnet.py"])

    # Display a progress bar for 25 seconds
    total_time = 25
    for elapsed in range(total_time + 1):
        # Calculate progress
        progress = elapsed / total_time
        bar_length = 25  # Length of the progress bar
        filled_length = int(bar_length * progress)

        # Create the bar string
        bar = "=" * filled_length + " " * (bar_length - filled_length)

        # Print the progress bar in pink
        # Using '\r' to overwrite the same line and flush to ensure it updates in place
        sys.stdout.write(f"\r{PINK}[{bar}] {elapsed}/{total_time}s{RESET}")
        sys.stdout.flush()

        # Wait 1 second between updates
        time.sleep(1)

    # After the loop, move to the next line
    print()