#!/usr/bin/env python3
"""
Fill missing timestamps in the merged meter dataset.

- Puts every row on a regular time grid (interval auto-detected, ~5 s)
- Inserts a row for every missing timestamp (e.g. load shedding / logger gaps)
- Missing rows get V, I, P, PF = 0
- DayE (daily energy, cumulative) is carried forward within each local day by
  default, because it does not drop to zero during an outage. Set
  DAYE_MODE = "zero" below if you really want zeros there too.
- Adds a 'Filled' column: 1 = inserted row, 0 = original measurement
- Output is saved next to this script
"""

import sys
from pathlib import Path

import pandas as pd

INPUT_DEFAULT = "merged_dataset.csv"   # produced by the merge script
OUTPUT_NAME = "merged_filled.csv"
DAYE_MODE = "ffill"                    # "ffill" or "zero"
TZ_NAME = "Asia/Dhaka"                 # used only to decide where each day starts
INTERVAL_SECONDS = None                # None = auto-detect from the data


def main() -> None:
    script_dir = Path(__file__).resolve().parent

    entered = input(f"Path to merged CSV [Enter = {script_dir / INPUT_DEFAULT}]: ").strip().strip('"').strip("'")
    in_path = Path(entered).expanduser() if entered else script_dir / INPUT_DEFAULT
    if not in_path.is_file():
        sys.exit(f"File not found: {in_path}")

    df = pd.read_csv(in_path)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce", utc=True)
    df = df.dropna(subset=["Timestamp"]).sort_values("Timestamp")

    # Sampling interval
    if INTERVAL_SECONDS:
        step = int(INTERVAL_SECONDS)
    else:
        step = int(round(df["Timestamp"].diff().dt.total_seconds().median()))
    step = max(step, 1)
    print(f"Sampling interval: {step} s")

    # Snap timestamps (they jitter by a few hundred ms) onto a regular grid
    df["Timestamp"] = df["Timestamp"].dt.round(f"{step}s")
    df = df.drop_duplicates(subset="Timestamp", keep="last").set_index("Timestamp")

    full_index = pd.date_range(df.index.min(), df.index.max(), freq=f"{step}s", name="Timestamp")
    missing = ~full_index.isin(df.index)
    df = df.reindex(full_index)

    value_cols = [c for c in df.columns if not c.startswith("DayE")]
    daye_cols = [c for c in df.columns if c.startswith("DayE")]

    df.loc[missing, value_cols] = 0

    if daye_cols:
        if DAYE_MODE == "ffill":
            local_day = df.index.tz_convert(TZ_NAME).date
            df[daye_cols] = df.groupby(local_day)[daye_cols].ffill()
        df.loc[missing, daye_cols] = df.loc[missing, daye_cols].fillna(0)

    df["Filled"] = missing.astype(int)

    # Report the biggest gaps
    gap_id = (pd.Series(missing, index=full_index) != pd.Series(missing, index=full_index).shift()).cumsum()
    gaps = (
        pd.Series(full_index, index=full_index)[missing]
        .groupby(gap_id[missing])
        .agg(start="first", end="last", samples="count")
    )
    gaps["minutes"] = (gaps["samples"] * step / 60).round(1)
    print(f"\nInserted {int(missing.sum())} rows in {len(gaps)} gap(s) "
          f"({missing.mean() * 100:.2f}% of the time range).")
    if len(gaps):
        print("Longest gaps:")
        print(gaps.sort_values("samples", ascending=False).head(10).to_string(index=False))

    out = df.reset_index()
    out["Timestamp"] = out["Timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S.%f").str[:-3] + "Z"
    out_path = script_dir / OUTPUT_NAME
    out.to_csv(out_path, index=False)
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()