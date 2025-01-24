import os
import json5
from datetime import datetime, timezone
from tqdm import tqdm

# Define paths
config_file = "apikey-crypto.json"
output_file = "../view/output/asset.txt"

# Ensure the output directory exists
os.makedirs(os.path.dirname(output_file), exist_ok=True)

# Read the JSON configuration file
with open(config_file, "r") as json_file:
    config = json5.load(json_file)
    input_file = config.get("input_file")  # Extract the input file from the JSON
    start_date = config.get("start_date")  # Extract the start date
    end_date = config.get("end_date")      # Extract the end date

# Check if the input file and date range are specified
if not input_file:
    raise ValueError("Input file is not specified in the JSON configuration.")
if not start_date or not end_date:
    raise ValueError("Start and/or end dates are not specified in the JSON configuration.")

# Convert start_date and end_date to timezone-aware datetime objects
start_date = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
end_date = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)

# Initialize a counter for the number of lines written
lines_written = 0

# Count the total lines in the input file for progress bar initialization
with open(input_file, "r") as infile:
    total_lines = sum(1 for _ in infile)

# Process the data from the input file
with open(input_file, "r") as infile, open(output_file, "w") as outfile:
    for line in tqdm(infile, total=total_lines, desc="Processing lines", unit="lines"):
        # Split the line by the pipe character
        parts = line.strip().split("|")
        
        # Extract the timestamp (first column) and closing price (4th column)
        if len(parts) >= 4:
            try:
                # Convert the Unix epoch timestamp to a timezone-aware datetime object
                line_date = datetime.fromtimestamp(int(parts[0]), tz=timezone.utc)
            except ValueError:
                # Skip lines with invalid timestamps
                continue
            
            # Check if the date falls within the specified range
            if start_date <= line_date <= end_date:
                closing_price = parts[3]  # 4th column is index 3
                # Write the filtered data to the output file in Unix epoch time
                outfile.write(f"{parts[0]},{closing_price}\n")
                lines_written += 1

print(f"Filtered data has been processed and saved to {output_file}. Total lines written: {lines_written}")
