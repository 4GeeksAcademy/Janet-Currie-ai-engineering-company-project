# `data/raw` folder

This folder is intended for **raw data** related to the company: dumps, exports, sample files, event samples, or untransformed datasets.

- **Main purpose**: serve as a landing zone or reference for original data before pipelines process it.
- **`healthcore_sales.csv`** is aggregated monthly network revenue (2016–2025), not patient-level data. Used by `scripts/train_sales_forecast.py`. Do not modify it in place.
- **Nightly telemetry CSVs** (`telemetry_YYYY-MM-DD.csv`) are **audit/recovery backups** of `telemetry_events`. They are not pipeline input; the clinic-supply ETL still reads PostgREST.
- **Recommendation**: document each dataset’s origin, format, expected size, privacy/PII considerations, and how it is versioned (ideally avoiding sensitive data in the repository). Generated nightly CSVs are gitignored.

> _Spanish version: [README.es.md](./README.es.md)._
