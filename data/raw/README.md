# `data/raw` folder

This folder is intended for **raw data** related to the company: dumps, exports, sample files, event samples, or untransformed datasets.

- **Main purpose**: serve as a landing zone or reference for original data before pipelines process it.
- **Nightly telemetry CSVs** (`telemetry_YYYY-MM-DD.csv`) are **audit/recovery backups** of `telemetry_events`. They are not pipeline input; the clinic-supply ETL still reads PostgREST.
- **Recommendation**: document each dataset’s origin, format, expected size, privacy/PII considerations, and how it is versioned (ideally avoiding sensitive data in the repository). Generated nightly CSVs are gitignored.

> _Spanish version: [README.es.md](./README.es.md)._
