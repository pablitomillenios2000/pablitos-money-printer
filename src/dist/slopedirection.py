import os
from datetime import datetime

# This file writes to direction.txt and groups in upwards 5000 
# and downwards 4000

# --- ADJUSTMENT VARIABLES ---
# Slope threshold to consider a value positive
considered_positive = 0.000025

# Number of consecutive points needed for the first confirmed direction change.
stable_count_initial = 300
# Number of consecutive points needed for subsequent changes once direction is established.
stable_count_steady = 700
# Whether to apply multi-stage hysteresis filtering
apply_hysteresis = True
# ---------------------------

# File paths
slope_file = "../view/output/simple_ma_slope.txt"
#slope_file_micro = "../view/output/ema_slopes_micro.txt"
direction_file = "../view/output/direction.txt"

def parse_ema_slopes(file_path):
    """
    Parses the EMA slopes file.
    Expects lines in the format:
    timestamp,slope,datetime (datetime can be ignored)

    Returns:
        list of tuples: [(timestamp, slope), ...]
    """
    data = []
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return data

    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            if line:
                parts = line.split(",")
                # Expect at least timestamp, slope
                if len(parts) < 2:
                    print(f"Skipping invalid line: {line}")
                    continue
                try:
                    timestamp = parts[0]
                    value = float(parts[1])
                    data.append((timestamp, value))
                except ValueError:
                    print(f"Skipping invalid line: {line}")
    return data

def multi_stage_hysteresis_filter(directions, stable_count_initial, stable_count_steady):
    """
    Applies a multi-stage hysteresis filter to direction values.
    - Initially, to confirm the first direction change from the starting point,
      we use stable_count_initial consecutive points.
    - After the first change is confirmed (direction established), any subsequent
      changes require stable_count_steady consecutive points to switch.

    Args:
        directions (list of int): Direction values, e.g. [4000, 5000, 4000, ...]
        stable_count_initial (int): Number of consecutive points needed for the first direction change.
        stable_count_steady (int): Number of consecutive points needed for subsequent direction changes once established.

    Returns:
        list of int: Filtered direction values.
    """
    if not directions:
        return directions

    filtered = [directions[0]]
    current_val = directions[0]

    direction_established = False
    pending_val = current_val
    consecutive_count = 0

    for i in range(1, len(directions)):
        next_val = directions[i]
        if next_val == current_val:
            # Same direction as current, reset pending info
            pending_val = current_val
            consecutive_count = 0
        else:
            # Potential direction change
            if next_val == pending_val:
                # Continuing the potential change
                consecutive_count += 1
                required_count = stable_count_steady if direction_established else stable_count_initial

                # If we have enough consecutive points of the new value, commit to change
                if consecutive_count >= required_count:
                    current_val = pending_val
                    consecutive_count = 0
                    direction_established = True
            else:
                # The direction changed from what was pending to another new value
                pending_val = next_val
                consecutive_count = 1

        filtered.append(current_val)

    return filtered

def write_direction_file(slope_data, output_file):
    """
    Writes the direction file based on EMA slopes.
    If slope > considered_positive, direction = 5000
    If slope <= considered_positive, direction = 4000

    Applies multi-stage hysteresis filtering if enabled.

    Args:
        slope_data (list of tuples): [(timestamp, slope), ...]
        output_file (str): Path to the direction file.
    """
    # Convert slopes to directions
    timestamps = [ts for ts, _ in slope_data]
    directions = [5000 if slope > considered_positive else 4000 for _, slope in slope_data]

    # Apply multi-stage hysteresis if desired
    if apply_hysteresis:
        directions = multi_stage_hysteresis_filter(directions, stable_count_initial, stable_count_steady)

    # Write the direction file
    with open(output_file, 'w') as file:
        for ts, dir_val in zip(timestamps, directions):
            file.write(f"{ts},{dir_val}\n")

if __name__ == "__main__":
    # Parse EMA slopes file
    ema_slopes = parse_ema_slopes(slope_file)

    # Write direction file
    write_direction_file(ema_slopes, direction_file)

    print(f"Direction file written to: {direction_file}")
