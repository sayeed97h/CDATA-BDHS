#!/usr/bin/env python3
"""
Merge daily meter CSV files (with or without a header row) into one clean CSV.

- Asks for the folder that contains the daily CSVs
- Handles files with a header, without a header, with blank lines between rows,
  or with repeated header rows
- Removes unparseable rows, exact duplicates and duplicate timestamps
- Writes merged_dataset.csv next to this script
"""

import sys
from pathlib import Path

import pandas as pd

OUTPUT_NAME = "merged_dataset.csv"

# Expected column layout: Timestamp + 6 channels x 5 values
CHANNELS = 6
FIELDS = ["V", "I", "P", "PF", "DayE"]
COLUMNS = ["Timestamp"] + [f"{f}{c}" for c in range(1, CHANNELS + 1) for f in FIELDS]


def parse_ts(s: pd.Series) -> pd.Series:
    """Parse ISO-8601 timestamps to UTC; anything else (e.g. a header line) -> NaT.

    format="ISO8601" skips pandas' format inference, which is what raised the
    'Could not infer format' warning when a file's first line was the header text.
    """
    ts = pd.to_datetime(s, errors="coerce", utc=True, format="ISO8601")
    bad = ts.isna() & s.notna()
    if bad.any():
        # Fallback for non-ISO timestamps; header text still comes back as NaT
        retry = pd.to_datetime(s[bad], errors="coerce", utc=True, format="mixed")
        ts.loc[bad] = retry
    return ts


def read_one(path: Path) -> pd.DataFrame:
    """Read a CSV regardless of whether it has a header row."""
    # header=None so the first line is never silently swallowed as a header
    df = pd.read_csv(path, header=None, dtype=str, skip_blank_lines=True)

    if df.shape[1] != len(COLUMNS):
        print(f"  [skip] {path.name}: {df.shape[1]} columns, expected {len(COLUMNS)}")
        return pd.DataFrame(columns=COLUMNS)

    df.columns = COLUMNS

    # Header rows (or any junk) become NaT and are dropped.
    # This also removes header lines repeated in the middle of a file.
    ts = parse_ts(df["Timestamp"])
    n_bad = int(ts.isna().sum())
    df = df.loc[ts.notna()].copy()
    df["Timestamp"] = ts[ts.notna()]

    for col in COLUMNS[1:]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    print(f"  [ok]   {path.name}: {len(df)} rows ({n_bad} header/invalid rows dropped)")
    return df


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    output_path = script_dir / OUTPUT_NAME

    folder_in = input("Enter the folder path containing the CSV files: ").strip().strip('"').strip("'")
    folder = Path(folder_in).expanduser()
    if not folder.is_dir():
        sys.exit(f"Folder not found: {folder}")

    files = sorted(p for p in folder.glob("*.csv") if p.resolve() != output_path)
    if not files:
        sys.exit("No CSV files found in that folder.")

    print(f"Found {len(files)} CSV file(s).")
    frames = [read_one(p) for p in files]
    frames = [f for f in frames if not f.empty]
    if not frames:
        sys.exit("No valid data found.")

    merged = pd.concat(frames, ignore_index=True)
    total = len(merged)

    # 1) exact duplicate rows (e.g. overlapping days / same file twice)
    merged = merged.drop_duplicates()
    # 2) same timestamp appearing more than once -> keep the last record
    merged = merged.drop_duplicates(subset="Timestamp", keep="last")
    merged = merged.sort_values("Timestamp").reset_index(drop=True)

    # ISO format with milliseconds and Z, same as the source files
    merged["Timestamp"] = merged["Timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S.%f").str[:-3] + "Z"

    merged.to_csv(output_path, index=False)

    print(f"\nRows read: {total} | after cleanup: {len(merged)} | removed: {total - len(merged)}")
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()