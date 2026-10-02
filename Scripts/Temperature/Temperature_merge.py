#!/usr/bin/env python3
"""
Merge daily AHT20 temperature/humidity logs (aht20-DD-MM-YYYY.csv) into one clean CSV,
and also produce a version with the missing timestamps filled in.

Input files (written by the Node-RED flow) have the columns:
    Timestamp, Temperature_C, Humidity
Because the flow writes the header only once per Node-RED start, a file may have a
header at the top, in the middle, or none at all. All of these are handled.

Outputs (saved next to this script):
    aht20_merged.csv  - cleaned and de-duplicated, original timestamps
    aht20_filled.csv  - regular time grid, missing timestamps inserted,
                        'Filled' column = 1 for inserted rows
"""

import sys
from pathlib import Path

import pandas as pd

MERGED_NAME = "aht20_merged.csv"
FILLED_NAME = "aht20_filled.csv"

COLUMNS = ["Timestamp", "Temperature_C", "Humidity"]
VALUE_COLS = COLUMNS[1:]

# AHT20 datasheet range; readings outside it are sensor/transmission glitches
TEMP_RANGE = (-40.0, 85.0)
RH_RANGE = (0.0, 100.0)

# Value written into inserted (missing) rows.
#   None -> leave blank (recommended: 0 degC / 0 %RH would be false readings)
#   0    -> write zeros
FILL_VALUE = None
INTERVAL_SECONDS = None        # None = auto-detect (about 5 s)
DISPLAY_TZ = "Asia/Dhaka"      # only used for the gap report printed on screen


def parse_ts(s: pd.Series) -> pd.Series:
    """Parse ISO-8601 timestamps to UTC; anything else (e.g. a header line) -> NaT."""
    ts = pd.to_datetime(s, errors="coerce", utc=True, format="ISO8601")
    bad = ts.isna() & s.notna()
    if bad.any():
        retry = pd.to_datetime(s[bad], errors="coerce", utc=True, format="mixed")
        ts.loc[bad] = retry
    return ts


def read_one(path: Path) -> pd.DataFrame:
    """Read one daily file, with or without header rows."""
    try:
        df = pd.read_csv(path, header=None, dtype=str, skip_blank_lines=True, on_bad_lines="skip")
    except pd.errors.EmptyDataError:
        print(f"  [skip] {path.name}: empty file")
        return pd.DataFrame(columns=COLUMNS)

    if df.shape[1] != len(COLUMNS):
        print(f"  [skip] {path.name}: {df.shape[1]} columns, expected {len(COLUMNS)}")
        return pd.DataFrame(columns=COLUMNS)

    df.columns = COLUMNS
    n_total = len(df)

    df["Timestamp"] = parse_ts(df["Timestamp"])
    for col in VALUE_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    valid = (
        df["Timestamp"].notna()
        & df["Temperature_C"].between(*TEMP_RANGE)
        & df["Humidity"].between(*RH_RANGE)
    )
    df = df.loc[valid].copy()

    print(f"  [ok]   {path.name}: {len(df)} rows ({n_total - len(df)} header/invalid rows dropped)")
    return df


def fmt_ts(s: pd.Series) -> pd.Series:
    """ISO-8601 with milliseconds and Z, same as the source files."""
    return s.dt.strftime("%Y-%m-%dT%H:%M:%S.%f").str[:-3] + "Z"


def fill_gaps(df: pd.DataFrame) -> pd.DataFrame:
    """Put rows on a regular grid and insert the missing timestamps."""
    if INTERVAL_SECONDS:
        step = int(INTERVAL_SECONDS)
    else:
        step = int(round(df["Timestamp"].diff().dt.total_seconds().median()))
    step = max(step, 1)
    print(f"\nSampling interval: {step} s")

    # Timestamps jitter by a few hundred ms, so snap them onto the grid first
    g = df.copy()
    g["Timestamp"] = g["Timestamp"].dt.round(f"{step}s")
    g = g.drop_duplicates(subset="Timestamp", keep="last").set_index("Timestamp")

    full_index = pd.date_range(g.index.min(), g.index.max(), freq=f"{step}s", name="Timestamp")
    missing = pd.Series(~full_index.isin(g.index), index=full_index)
    g = g.reindex(full_index)

    if FILL_VALUE is not None:
        g.loc[missing.values, VALUE_COLS] = FILL_VALUE
    g["Filled"] = missing.astype(int).values

    gap_id = (missing != missing.shift()).cumsum()
    gaps = (
        pd.Series(full_index, index=full_index)[missing]
        .groupby(gap_id[missing])
        .agg(start="first", end="last", samples="count")
    )
    gaps["minutes"] = (gaps["samples"] * step / 60).round(1)
    print(f"Inserted {int(missing.sum())} rows in {len(gaps)} gap(s) "
          f"({missing.mean() * 100:.2f}% of the time range).")
    if len(gaps):
        top = gaps.sort_values("samples", ascending=False).head(10).copy()
        top["start"] = top["start"].dt.tz_convert(DISPLAY_TZ).dt.strftime("%Y-%m-%d %H:%M:%S")
        top["end"] = top["end"].dt.tz_convert(DISPLAY_TZ).dt.strftime("%Y-%m-%d %H:%M:%S")
        print(f"Longest gaps ({DISPLAY_TZ} time):")
        print(top.to_string(index=False))

    return g.reset_index()


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    merged_path = script_dir / MERGED_NAME
    filled_path = script_dir / FILLED_NAME

    folder_in = input("Enter the folder path containing the AHT20 CSV files: ").strip().strip('"').strip("'")
    folder = Path(folder_in).expanduser()
    if not folder.is_dir():
        sys.exit(f"Folder not found: {folder}")

    skip = {merged_path, filled_path}
    files = sorted(p for p in folder.glob("*.csv") if p.resolve() not in skip)
    if not files:
        sys.exit("No CSV files found in that folder.")

    print(f"Found {len(files)} CSV file(s).")
    frames = [read_one(p) for p in files]
    frames = [f for f in frames if not f.empty]
    if not frames:
        sys.exit("No valid data found.")

    merged = pd.concat(frames, ignore_index=True)
    total = len(merged)

    # exact duplicates, then repeated timestamps (keep the last record)
    merged = merged.drop_duplicates()
    merged = merged.drop_duplicates(subset="Timestamp", keep="last")
    merged = merged.sort_values("Timestamp").reset_index(drop=True)

    out = merged.copy()
    out["Timestamp"] = fmt_ts(out["Timestamp"])
    out.to_csv(merged_path, index=False)
    print(f"\nRows read: {total} | after cleanup: {len(merged)} | removed: {total - len(merged)}")
    print(f"Saved: {merged_path}")

    filled = fill_gaps(merged)
    filled["Timestamp"] = fmt_ts(filled["Timestamp"])
    filled.to_csv(filled_path, index=False)
    print(f"\nSaved: {filled_path}")


if __name__ == "__main__":
    main()