import pandas as pd

THRESHOLD = 0.20  # Adjust as needed

POLYREG_FILE       = "../view/output/polyreg.txt"
POLYUP_FILE        = "../view/output/polyup.txt"
POLYDOWN_FILE      = "../view/output/polydown.txt"
POLYACC_FILE_UP    = "../view/output/polyacc_abs_up.txt"
POLYACC_FILE_DOWN  = "../view/output/polyacc_abs_down.txt"


def load_polyreg(polyreg_file):
    """
    Load the polyreg data into a DataFrame and compute the Acceleration column.
    Returns a DataFrame with columns: [Timestamp, LSMA, Acceleration].
    """
    df = pd.read_csv(polyreg_file, header=0, names=["Timestamp", "LSMA"])
    df = df.dropna(subset=["LSMA"])
    
    # Convert Timestamp to numeric and sort
    df["Timestamp"] = pd.to_numeric(df["Timestamp"], errors="coerce")
    df = df.dropna(subset=["Timestamp"])
    df = df.sort_values(by="Timestamp").reset_index(drop=True)
    
    # Calculate acceleration = diff(LSMA) / LSMA * 1000
    # Using shift(1) is slightly safer, so we don’t lose row alignment after diff():
    df["Acceleration"] = (df["LSMA"].diff() / df["LSMA"].shift(1)) * 1000
    
    # Drop NaN in Acceleration (the first row will be NaN)
    df = df.dropna(subset=["Acceleration"])
    
    return df


def parse_segmented_file(filepath):
    """
    Reads a file that uses lines containing '---' as segment delimiters.
    
    Each segment has:
      - One 'delimiter line' that has '---' in the second field
      - Several 'data lines' with numeric values until the next 'delimiter line'
    Returns a list of segments, where each segment is a dict:
      {
          "delimiter_timestamp": <float or str>,
          "lines": [(timestamp_float, lsma_float), (ts, val), ...]
      }
    """
    segments = []
    current_segment = {
        "delimiter_timestamp": None,
        "lines": []
    }
    
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) < 2:
                continue
            
            # If we encounter '---' in the second column => start of a new segment
            if parts[1].strip() == "---":
                # If the current segment already has a delimiter defined, 
                # it means we've encountered a new segment. Save the old one.
                if current_segment["delimiter_timestamp"] is not None or current_segment["lines"]:
                    segments.append(current_segment)
                
                # Begin a fresh segment
                current_segment = {
                    "delimiter_timestamp": parts[0].strip(),  # keep as string or float
                    "lines": []
                }
            else:
                # This is a data line in the current segment
                try:
                    ts_val = float(parts[0].strip())
                    lsma_val = float(parts[1].strip())
                    current_segment["lines"].append((ts_val, lsma_val))
                except ValueError:
                    # If parsing fails, skip that line
                    continue
    
    # If we ended with a segment that never got appended:
    if current_segment["delimiter_timestamp"] is not None or current_segment["lines"]:
        segments.append(current_segment)
    
    return segments


def filter_segments_by_acceleration(segments, df_polyreg, threshold, mode="up"):
    """
    Given a list of segments (from parse_segmented_file) and a DataFrame df_polyreg
    that has columns [Timestamp, LSMA, Acceleration], filter each segment to:
    
      - Keep at most 3 timestamps whose acceleration meets the mode’s condition:
          mode="up"   => Acceleration >= threshold
          mode="down" => Acceleration <= -threshold
      - Preserve the order of lines
      - Return the new list of filtered segments
    
    Each returned segment will keep the same delimiter_timestamp, but only 3 or fewer lines.
    """
    filtered_segments = []
    
    for seg in segments:
        delimiter_ts = seg["delimiter_timestamp"]
        data_lines   = seg["lines"]
        
        # We only allow up to 3 in this segment
        kept = []
        count = 0
        
        for (ts_val, lsma_val) in data_lines:
            # Find the row in df_polyreg for this timestamp (if multiple, take the first)
            row = df_polyreg.loc[df_polyreg["Timestamp"] == ts_val]
            if row.empty:
                # If we don’t find an exact match, skip
                continue
            
            acc_val = row["Acceleration"].values[0]
            
            if mode == "up":
                condition_met = (acc_val >= threshold)
            else:
                condition_met = (acc_val <= -threshold)
            
            if condition_met:
                kept.append((ts_val, lsma_val))
                count += 1
                if count >= 3:
                    break
        
        filtered_segments.append({
            "delimiter_timestamp": delimiter_ts,
            "lines": kept
        })
    
    return filtered_segments


def write_segments_to_file(segments, output_file):
    """
    Writes out the segments with the original delimiter line (timestamp,---),
    followed by each kept data line. All without headers or index.
    """
    with open(output_file, "w") as f:
        for seg in segments:
            delimiter_ts = seg["delimiter_timestamp"]
            data_lines   = seg["lines"]
            
            # Write the delimiter line first: e.g. 1704936480,---
            f.write(f"{delimiter_ts},---\n")
            for (ts_val, lsma_val) in data_lines:
                f.write(f"{ts_val},{lsma_val}\n")


def main():
    # 1. Load polyreg and compute acceleration
    df_polyreg = load_polyreg(POLYREG_FILE)
    
    # 2. Parse the polyup file into segments
    up_segments = parse_segmented_file(POLYUP_FILE)
    #    Filter those segments by acceleration >= THRESHOLD
    filtered_up = filter_segments_by_acceleration(up_segments, df_polyreg, THRESHOLD, mode="up")
    #    Write them out to polyacc_abs_up.txt
    write_segments_to_file(filtered_up, POLYACC_FILE_UP)
    
    print(f"Filtered up-segments written to {POLYACC_FILE_UP}")
    
    # 3. Parse the polydown file into segments
    down_segments = parse_segmented_file(POLYDOWN_FILE)
    #    Filter those segments by acceleration <= -THRESHOLD
    filtered_down = filter_segments_by_acceleration(down_segments, df_polyreg, THRESHOLD, mode="down")
    #    Write them out to polyacc_abs_down.txt
    write_segments_to_file(filtered_down, POLYACC_FILE_DOWN)
    
    print(f"Filtered down-segments written to {POLYACC_FILE_DOWN}")


if __name__ == "__main__":
    main()
