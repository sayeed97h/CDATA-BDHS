# CDATA-BDHS

**Room-Level Electricity Consumption Dataset of a Bangladeshi Household**

[![DOI](https://img.shields.io/badge/DOI-10.48726%2F0c2kg--tp589-blue)](https://doi.org/10.48726/0c2kg-tp589)

This dataset contains residential electricity consumption and indoor environmental data collected from a single-family unit in an apartment complex.

## Electrical measurements

A Refoss EM06P 6-channel smart energy meter captures electrical measurements across six circuits:

- Main grid supply
- Backup power (diesel generator)
- Four individual rooms

Each channel reports current, voltage, active power, power factor, and cumulative energy consumption. The EM06P publishes these readings over a local MQTT connection to a Raspberry Pi 4 every 5 seconds.

## Indoor environmental measurements

A temperature and humidity sensor connected directly to the Raspberry Pi 4 provides indoor environmental context, sampling at the same 5-second rate and enabling correlation between ambient conditions and electrical load.

The temperature sensor is located at the center of the house, where active cooling, such as airflow from ceiling fans, is typically less used. The measured temperature may therefore be higher than the temperature experienced in occupied zones with active air circulation. Nevertheless, these measurements provide a useful indication of baseline indoor thermal conditions and can help estimate the cooling demand required to maintain an acceptable level of thermal comfort for occupants.

## Data format

Node-RED logs both datasets on the Raspberry Pi 4 as one CSV file per day.

| Dataset | Daily file name | Merged / filled outputs(from helper scripts) |
|---|---|---|
| Power logs (energy meter) | `DD-MM-YYYY.csv` | `merged_dataset.csv`, `merged_filled.csv` |
| Temperature / humidity (AHT20) | `aht20-DD-MM-YYYY.csv` | `aht20_merged.csv`, `aht20_filled.csv` |

All timestamps are UTC (ISO 8601 with milliseconds and a trailing `Z`). Bangladesh time (Asia/Dhaka) is UTC+6, so a Dhaka day runs from 18:00 UTC to 18:00 UTC the next day.

### Power logs

One row per sample (about every 5 s) with 31 columns: a timestamp plus five measurements for each of the 6 meter channels. The channel number is the suffix of the column name (`V1` is the voltage of channel 1, `P4` is the active power of channel 4, and so on).

| Column | Unit | Description |
|---|---|---|
| `Timestamp` | UTC, ISO 8601 | Time the sample was logged. |
| `V1` ... `V6` | V | RMS voltage measured on the channel. |
| `I1` ... `I6` | A | RMS current drawn on the channel. |
| `P1` ... `P6` | W | Active (real) power on the channel. |
| `PF1` ... `PF6` | 0 to 1 (unitless) | Power factor: the ratio of active power to apparent power. |
| `DayE1` ... `DayE6` | kWh | Energy accumulated on the channel since the start of the day. It increases through the day and restarts at local midnight. |
| `Filled` | 0 / 1 | `merged_filled.csv` only. `1` marks a row inserted to fill a missing timestamp, `0` a real measurement. |

Channel mapping (the six circuits are listed under [Electrical measurements](#electrical-measurements); fill in which channel monitors which):

| Channel | Circuit |
|---|---|
| 1 | Utility Grid (total consumption including aggregated consumption from kitchen and other appliances) |
| 2 | Backup Power from DG [output routed with Utility through automatic transfer switch (ATS)] |
| 3 | Living Room 1|
| 4 | Living Room 2 (also shares common room and logger own consumption)|
| 5 | Living Room 3|
| 6 | Living Room 4|

Note: when Utility Grid and Backup are both providing power, that means the backup generator is not running; the power is coming from the utility(routed via ATS) 

### Temperature / humidity logs

One row per sample (about every 5 s) from the AHT20 sensor.

| Column | Unit | Description |
|---|---|---|
| `Timestamp` | UTC, ISO 8601 | Time the reading was logged. |
| `Temperature_C` | °C | Air temperature measured by the AHT20 (range -40 to 85 °C). |
| `Humidity` | %RH | Relative humidity measured by the AHT20 (range 0 to 100 %). |
| `Filled` | 0 / 1 | `aht20_filled.csv` only. `1` marks an inserted row (`Temperature_C` and `Humidity` are blank), `0` a real reading. |

## Helper scripts

Small Python scripts turn the raw daily logs into single, clean, analysis-ready CSV files. The raw files are not uniform: depending on when the logger was restarted, a file may have a header row at the top, in the middle, or none at all, and files may contain blank lines, repeated rows, truncated lines or glitch readings. Samples are also missing whenever the logger or the supply was down, for example during load shedding.

**Requirements:** Python 3.8 or newer and pandas 2.0 or newer (`pip install pandas`).

### `merge_datasets.py` (power logs, merge and clean)

Merges every `*.csv` in a folder into one file.

- Prompts for the folder that contains the daily CSV files.
- Reads each file without assuming a header, then assigns the 31 column names itself, so the first data row is never lost.
- Drops header rows (including ones repeated mid-file), blank lines and rows without a valid timestamp.
- Removes exact duplicate rows and duplicate timestamps (the last record is kept).
- Sorts by time and writes `merged_dataset.csv` next to the script, with the original timestamps unchanged.
- Skips any file that does not have exactly 31 columns and says which one.

### `fill_missing_timestamps.py` (power logs, gap filling)

Run after `merge_datasets.py`. Reads `merged_dataset.csv` and writes `merged_filled.csv` next to the script.

- Detects the sampling interval (about 5 s) and snaps timestamps onto a regular grid, because the originals jitter by a few hundred milliseconds. Timestamps in the output therefore end in `.000`.
- Inserts a row for every missing timestamp. In those rows `V`, `I`, `P` and `PF` are set to `0` for all channels, because a gap may be a load-shedding outage.
- `DayE` is not zeroed by default, because daily energy does not fall to zero during an outage. The last value is carried forward within each local (Dhaka) day. Set `DAYE_MODE = "zero"` to fill with zeros instead.
- Adds a `Filled` column (`1` = inserted row, `0` = real measurement).
- Prints the number of gaps and the 10 longest ones.

### `merge_aht20.py` (temperature / humidity, merge, clean and fill)

Does the merge and the gap filling for the AHT20 logs in a single run.

- Prompts for the folder that contains the `aht20-DD-MM-YYYY.csv` files.
- Applies the same header-agnostic reading and duplicate removal as the power-log merge.
- Also drops readings outside the AHT20 sensor range (-40 to 85 °C, 0 to 100 %RH), which are glitches.
- Writes `aht20_merged.csv` (cleaned, original timestamps) and `aht20_filled.csv` (regular 5 s grid with a `Filled` flag) next to the script.
- Inserted rows are left blank, not zero, since 0 °C and 0 %RH would be false readings. Set `FILL_VALUE = 0` at the top of the script if zeros are preferred.
- Prints the longest gaps in Dhaka time.

### Usage

```bash
# Power logs
python merge_datasets.py            # enter the folder containing the daily CSVs
python fill_missing_timestamps.py   # press Enter to use merged_dataset.csv

# Temperature / humidity
python merge_aht20.py               # enter the folder containing the aht20-*.csv files
```

All outputs are written to the folder containing the script.

### Notes on filled data

- Zero-filled power rows mean "no data was recorded". This may be a real outage (such as load shedding) or only a logger or network dropout. Use the `Filled` column to identify these rows and exclude them from averages if you want only measured values.
- Comparing channels helps tell the two cases apart: if the main grid channel is zero while the backup generator channel is active, the gap is load shedding.
- Keep the merged (unfilled) files if you need the exact original timestamps, because the filled files use a regular 5 s interval.

## Metadata and access

Full dataset metadata is available in the TalTech Data Repository:
- DOI: <https://doi.org/10.48726/0c2kg-tp589>

## Citation

If you use this dataset, please cite it as follows.

**APA**

> Hasan, S., Ahmed, S. M. M., & Vinnikov, D. (2026). *Room-Level Electricity Consumption Dataset of a Bangladeshi Household* [Data set]. TalTech Data Repository. https://doi.org/10.48726/0c2kg-tp589

**Harvard**

> Hasan, S., Ahmed, S.M.M. and Vinnikov, D. (2026) "Room-Level Electricity Consumption Dataset of a Bangladeshi Household". TalTech Data Repository. doi:10.48726/0c2kg-tp589.

**IEEE**

> S. Hasan, S. M. M. Ahmed and D. Vinnikov, "Room-Level Electricity Consumption Dataset of a Bangladeshi Household". TalTech Data Repository, Aug. 19, 2026. doi: 10.48726/0c2kg-tp589.

## Credits
- Remote data retrieval from the logger uses IT resources from the Power Electronics Group of TalTech
- Example merging scripts generated using Claude Sonnet 5.5 (Anthropic).
