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

## Metadata and access

Full dataset metadata and download are available in the TalTech Data Repository:

- Record: <https://data.taltech.ee/records/0c2kg-tp589?preview=1>
- DOI: <https://doi.org/10.48726/0c2kg-tp589>

## Citation

If you use this dataset, please cite it as follows.

**APA**

> Hasan, S., Ahmed, S. M. M., & Vinnikov, D. (2026). *Room-Level Electricity Consumption Dataset of a Bangladeshi Household* [Data set]. TalTech Data Repository. https://doi.org/10.48726/0c2kg-tp589

**Harvard**

> Hasan, S., Ahmed, S.M.M. and Vinnikov, D. (2026) "Room-Level Electricity Consumption Dataset of a Bangladeshi Household". TalTech Data Repository. doi:10.48726/0c2kg-tp589.

**IEEE**

> S. Hasan, S. M. M. Ahmed and D. Vinnikov, "Room-Level Electricity Consumption Dataset of a Bangladeshi Household". TalTech Data Repository, Aug. 19, 2026. doi: 10.48726/0c2kg-tp589.
