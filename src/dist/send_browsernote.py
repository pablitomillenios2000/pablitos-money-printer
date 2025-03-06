#!/usr/bin/env python3

import json

# Input files
trades_file = "../view/output/trades.txt"
polyabsup_file = "../view/output/polyacc_abs_up.txt"
polyabsdown_file = "../view/output/polyacc_abs_down.txt"
notes_file = "../view/output/notes.json"


def get_max_timestamp_from_file(filename, delimiter=",", timestamp_index=0):
    """Reads the specified file, parses timestamps, and returns the maximum timestamp found."""
    max_ts = None
    with open(filename, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(delimiter)
            if len(parts) < timestamp_index + 1:
                continue  # skip invalid lines
            try:
                ts = float(parts[timestamp_index])
                # Convert float to int if you wish. 
                # But float is fine, as long as comparisons are consistent.
                if max_ts is None or ts > max_ts:
                    max_ts = ts
            except ValueError:
                pass  # skip lines that don't have a valid float in the timestamp field
    return max_ts


def main():
    # 1) Read the JSON file
    with open(notes_file, "r") as f:
        notes_data = json.load(f)

    # Extract the current known timestamps
    current_up = notes_data.get("last_polyupacc_time", 0)
    current_down = notes_data.get("last_polydownacc_time", 0)
    current_order = notes_data.get("last_order_time", 0)

    # 2) Read each text file to find the highest timestamp
    max_up = get_max_timestamp_from_file(polyabsup_file)
    max_down = get_max_timestamp_from_file(polyabsdown_file)
    # For trades.txt, the timestamp is in index 0 as well
    max_order = get_max_timestamp_from_file(trades_file)

    # 3) Compare and update if we found a newer timestamp
    updated = False

    if max_up is not None and max_up > current_up:
        print(f"Updating last_polyupacc_time from {current_up} to {max_up}")
        notes_data["last_polyupacc_time"] = max_up
        updated = True

    if max_down is not None and max_down > current_down:
        print(f"Updating last_polydownacc_time from {current_down} to {max_down}")
        notes_data["last_polydownacc_time"] = max_down
        updated = True

    if max_order is not None and max_order > current_order:
        print(f"Updating last_order_time from {current_order} to {max_order}")
        notes_data["last_order_time"] = max_order
        updated = True

    # 4) If updates were made, write the new data to the JSON
    if updated:
        with open(notes_file, "w") as f:
            json.dump(notes_data, f, indent=4)
        print("JSON file updated successfully.")
    else:
        print("No updates needed. All timestamps are up-to-date.")


if __name__ == "__main__":
    main()
