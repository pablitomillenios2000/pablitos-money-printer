#!/usr/bin/env python3

import os

POLYREG_FILE  = "../view/output/polyreg.txt"
POLYACC_FILE  = "../view/output/polyacc.txt"
POLYUP_FILE   = "../view/output/polyup.txt"
POLYDOWN_FILE = "../view/output/polydown.txt"

def main():
    print("Placing each timestamp into both polyup.txt and polydown.txt with placeholders if needed")

    # Make sure both files exist
    if not os.path.isfile(POLYREG_FILE):
        print(f"Error: {POLYREG_FILE} does not exist.")
        return
    if not os.path.isfile(POLYACC_FILE):
        print(f"Error: {POLYACC_FILE} does not exist.")
        return

    # 1) Read polyacc.txt into a dictionary keyed by timestamp (string),
    #    storing the numeric value (float).
    acc_dict = {}
    with open(POLYACC_FILE, 'r') as f_acc:
        for line in f_acc:
            line = line.strip()
            if not line:
                continue
            parts = line.split(',')
            if len(parts) != 2:
                # Skip malformed lines
                continue
            
            ts_str, val_str = parts
            ts_str = ts_str.strip()
            val_str = val_str.strip()
            if not ts_str or not val_str:
                continue

            try:
                acc_value = float(val_str)
            except ValueError:
                # Skip if not convertible to float
                continue
            
            acc_dict[ts_str] = acc_value

    # 2) For each line in polyreg.txt, figure out how to write to polyup and polydown
    with open(POLYREG_FILE, 'r') as f_reg, \
         open(POLYUP_FILE, 'w') as f_up, \
         open(POLYDOWN_FILE, 'w') as f_down:

        for line in f_reg:
            line_stripped = line.strip()
            if not line_stripped:
                # If empty line, skip or handle as you prefer
                continue

            parts = line_stripped.split(',')
            if len(parts) != 2:
                # Skip if line not "timestamp,value"
                continue

            ts_str = parts[0].strip()
            reg_val = parts[1].strip()

            # 3) Determine if there's a matching timestamp in acc_dict
            acc_val = acc_dict.get(ts_str, None)

            if acc_val is None:
                # If no match, put placeholders in both files
                # Using the same timestamp from polyreg, but value is '---'
                f_up.write(f"{ts_str},---\n")
                f_down.write(f"{ts_str},---\n")
            else:
                # If matched, decide which file gets the real line vs the placeholder
                if acc_val > 0:
                    # polyup: real line
                    f_up.write(line_stripped + "\n")
                    # polydown: placeholder
                    f_down.write(f"{ts_str},---\n")
                else:
                    # polydown: real line
                    f_down.write(line_stripped + "\n")
                    # polyup: placeholder
                    f_up.write(f"{ts_str},---\n")


if __name__ == "__main__":
    main()
