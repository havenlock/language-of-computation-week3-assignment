# Module 3 Assignment — MSAI-5523

This is my Module 3 assignment for MSAI-5523 (Language of Computation), Lipscomb University.

In this module I turn a one-time "fix the ISBNs" conversation into code that runs the same way every time: `ingest.py` validates every row of a books CSV against the rules in `rules.md`, loads the good rows into `books.db` without ever creating duplicates, and appends a run record to `ingestion-log.json` that `report.html` displays.

## Running the ingestion

These commands are for a Mac. Open **Terminal** (press `⌘ Space`, type `Terminal`, press Return).

```bash
# 1. Go to the assignment folder
cd ~/workspace/language-of-computation/week3-assignment

# 2. Check that Python 3 is installed (any 3.9 or newer is fine; SQLite is built in)
python3 --version

# 3. Load the first delivery
python3 ingest.py books.csv

# 4. Load it again — every row should be "skipped", nothing duplicated
python3 ingest.py books.csv

# 5. Load the second delivery
python3 ingest.py books-batch2.csv
```

Each run prints one line of counts and appends an entry to `ingestion-log.json`. `books.db` is created on the first run.

### Opening the report

```bash
open report.html
```

(or double-click `report.html` in Finder). Click **Open ingestion-log.json** and pick the `ingestion-log.json` file in this folder. Runs are listed newest first. No server is needed — the page reads the file you choose and nothing leaves your computer.

### Starting over

```bash
rm books.db ingestion-log.json
```

then repeat steps 3–5.

### Checking the code against the rules

`check_rules.py` runs the examples table from `rules.md` through the same functions `ingest.py` uses:

```bash
python3 check_rules.py
```

## Files

| File | What it is |
|---|---|
| `data-validation.md` | Diagnosis of the ISBN columns in both deliveries, made before any ingestion |
| `diagnose_isbn.py` | The read-only script that produced the diagnosis |
| `books.csv`, `books-batch2.csv` | The two deliveries, unchanged |
| `rules.md` | The ingestion rules and the examples table — the only source of truth for the code |
| `ingest.py` | The ingestion script |
| `check_rules.py` | Verifies `ingest.py` against the examples in `rules.md` |
| `report.html` | Reads `ingestion-log.json` and shows each run |
| `books.db` | The database after the three runs above |
| `ingestion-log.json` | The log of those three runs |
