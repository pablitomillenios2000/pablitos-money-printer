import os
import json5

# File paths
json_file = "apikey-crypto.json"
ASSET_FILE = "../view/output/pairname.txt"

try:
    # Load the JSON file
    with open(json_file, 'r') as file:
        config = json5.load(file)

    # Get the 'pair' from the JSON configuration
    pair = config.get("pair")
    exchange = config.get("exchange")
    if not pair:
        raise ValueError("Key 'pair' not found in the JSON file.")

    # Ensure the output directory exists
    os.makedirs(os.path.dirname(ASSET_FILE), exist_ok=True)

    # Write the pair to the file
    with open(ASSET_FILE, 'w') as file:
        file.write(pair+' '+exchange)

    #print(f"Pair '{pair}' has been successfully written to {ASSET_FILE}")

except FileNotFoundError:
    print(f"Error: The file '{json_file}' does not exist.")
except ValueError as e:
    print(f"Error: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
