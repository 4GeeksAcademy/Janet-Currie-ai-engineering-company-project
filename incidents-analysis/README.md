# HealthCore — Patient Incident Report Analyzer

Local CSV analysis utility for Priya Nair (Patient Experience). Processes incident exports offline and prints aggregate metrics. **Never** prints, logs, or exports `patient_id` (HIPAA / UK GDPR).

This folder is a **standalone CLI**, not an HTTP service. Do not put this under `services/`.

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
