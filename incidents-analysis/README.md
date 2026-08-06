# HealthCore — Patient Incident Report Analyzer

Local CSV analysis utility for Priya Nair (Patient Experience). Processes incident exports offline and prints aggregate metrics. **Never** prints, logs, or exports `patient_id` (HIPAA / UK GDPR).

This folder is a **standalone CLI** and the shared validation library for Phase 2. HTTP endpoints live under [`services/api/`](../services/api/) and import these modules — do not duplicate HealthCore field rules there.

## Context

See [CONTEXT-healthcore.md](CONTEXT-healthcore.md).

## Run

```bash
cd incidents-analysis
python3 analyze.py incidents-healthcore.csv
```

Non-interactive options:

```bash
python3 analyze.py incidents-healthcore.csv --no-export
python3 analyze.py incidents-healthcore.csv --export metrics.csv
```

## Platform integration (Phase 2)

1. Start API: see [`services/api/README.md`](../services/api/README.md) (port 8000).
2. Start backoffice: `npm run dev:backoffice` (port 3001).
3. Open http://localhost:3001/incidents and upload `incidents-healthcore.csv`.

## Test

```bash
cd incidents-analysis
python3 -m unittest discover -s tests -v
```

## Layout

```text
incidents-analysis/
├── CONTEXT-healthcore.md
├── README.md
├── analyze.py
├── requirements.txt
├── incidents-healthcore.csv   # graded sample (100 rows; synthetic IDs)
├── src/
│   ├── constants.py
│   ├── models.py
│   ├── load.py
│   ├── validate.py
│   ├── summarize.py
│   ├── report.py
│   └── export.py
└── tests/
    └── test_analyze.py
```

## Compliance

- Process files only on a machine authorized for HealthCore data.
- Do not upload incident CSVs to external AI tools.
- Console and export outputs contain metrics only — never patient identifiers.
