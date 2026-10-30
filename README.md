# Module 3 Assignment — MSAI-5523

This is my Module 3 assignment for MSAI-5523 (Language of Computation), Lipscomb University.

In this module I turn a one-time "fix the ISBNs" conversation into code that runs the same way every time: `ingest.py` validates every row of a books CSV against the rules in `rules.md`, loads the good rows into `books.db` without ever creating duplicates, and appends a run record to `ingestion-log.json` that `report.html` displays.
