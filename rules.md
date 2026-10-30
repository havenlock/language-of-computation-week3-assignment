# Ingestion rules for books CSV files

These rules are the only source of truth for `ingest.py`. Anything not written here is not allowed. The script may not use AI, the internet, or anything else that could make two runs of the same file differ.

## 1. What a valid ISBN is

- **ISBN-10**: exactly 10 characters, the first nine digits, the last a digit or `X`. Check: weights 10 down to 1, sum mod 11 = 0.
- **ISBN-13**: exactly 13 digits starting `978` or `979`. Check: weights alternate 1,3,1,3…, sum mod 10 = 0.
- A value is valid only if it passes its checksum. Passing the checksum means the string is well-formed; it does not prove it belongs to this book (see rule 6).

## 2. Normalization (always done first, never a repair)

Before any check, both `isbn` and `isbn13` values are normalized: strip leading/trailing whitespace, remove internal spaces and hyphens, upper-case `x`. This is formatting, not a change of value. Normalization alone is not logged.

## 3. Repairs

A repair is allowed only when the original value can be reconstructed **exactly** and the result **passes its checksum**. Every repair is logged on the row as a warning with before → after. The code repairs these, and only these:

| Problem | Repair |
|---|---|
| ISBN-10 with fewer than 10 digits (leading zeros lost by a spreadsheet) | Left-pad with zeros to 10. Keep only if the checksum passes. |
| `isbn13` written as a float (`9.78043902348e+12`, or `…0.0`) | Discard the float — its last digit is gone. Derive ISBN-13 from the valid ISBN-10 instead (`978` + first nine digits + new check digit). |
| `isbn13` empty but ISBN-10 valid | Derive ISBN-13 from the ISBN-10. |
| Valid ISBN-13 sitting in the `isbn` column with `isbn13` empty | Move it to `isbn13`. Leave `isbn` empty. |
| `isbn` empty but ISBN-13 valid and starts `978` | Derive ISBN-10 from the ISBN-13. |

**When a repair is a guess:** any repair that requires choosing a digit — fixing a bad checksum, replacing a letter, deciding which of 11 digits is extra — is a guess, even if the guess happens to pass the checksum. The code never guesses.

## 4. Unfixable ISBNs → load the row, store no ISBN, warn

If after normalization and the allowed repairs an ISBN value is still invalid, the **row is still loaded** (the book exists; its title and author are fine), the ISBN fields are stored as NULL, and a warning is logged with the original value and the reason. This covers:

- checksum fails on a 10- or 13-character value
- a letter other than a final `X` anywhere in the value
- wrong length (11 or 12 digits, or a 13-digit value not starting 978/979)
- `isbn13` that is not a 13-digit value and not a float (e.g. `76783609419.0`)
- `isbn` and `isbn13` both valid but **disagree** (the ISBN-10 converts to a different ISBN-13) — neither is trusted; both stored NULL
- both ISBN fields empty — stored NULL, warning `no ISBN`

If only one of the two values is unfixable and the other is valid, the valid one is kept and the other is derived from it (rule 3), with a warning naming the discarded value.

## 5. Identity: what makes two rows the same book

**`book_id` is the key.** Two rows with the same `book_id` are the same book, full stop. ISBN is an attribute of the book, not its identity. A row with no usable ISBN is still a book.

## 6. Rejections → row is never loaded

A row is rejected, counted, and listed in the log with its reason when:

1. **Missing `book_id` or missing/blank `title`.** Nothing to key or name the record.
2. **Exact duplicate of an earlier row in the same file** (same `book_id`, identical in every column). The first occurrence is processed; the second is rejected as `duplicate row in file`.
3. **Its valid ISBN already belongs to a different `book_id`** — either already in the database or earlier in the same file. Two books cannot share an ISBN; the checksum cannot say which one is wrong, so the newcomer is rejected as `ISBN already assigned to book <id>` and a person decides.

Nothing else is rejected. A placeholder row (`Unknown` / `Untitled Manuscript`) with a `book_id` and a title is loaded with a `no ISBN` warning, not rejected.

## 7. Re-delivery: a book already in the database arrives again

- Compare the incoming row (after normalization and repairs) with the stored row, column by column.
- **Identical → `skipped`** (already exists). Not an error.
- **Different → `updated`**: overwrite the stored columns with the incoming values and count the row as updated. The log records which columns changed.
- **Exception: an empty incoming ISBN never blanks a stored ISBN.** If the incoming row has no usable ISBN and the database has one, the stored ISBN is kept and the row is otherwise updated (or skipped if nothing else changed).
- Running the same file twice therefore produces zero inserts and zero updates the second time; every row is `skipped`.

## 8. Database

- SQLite file `books.db`, one table `books`, primary key `book_id`.
- Columns: every column from the CSV, plus `isbn10` and `isbn13` (normalized, repaired, or NULL), and `last_source_file`, `last_loaded_at`.
- The original `isbn` and `isbn13` strings from the file are kept in `isbn_raw` and `isbn13_raw` so nothing is lost.
- A UNIQUE index on `isbn13` (where not NULL) enforces rule 6.3 at the database level too.

## 9. The log and the report

Every run appends one entry to `ingestion-log.json` (create if missing, never overwrite earlier entries). Each entry has:

- `run_at` (ISO timestamp), `source_file`, `rows_read`
- counts: `loaded` (new), `updated`, `skipped` (already present, unchanged), `rejected`
- `rejected_rows`: every row not loaded — `book_id`, `title`, `reason`
- `warnings`: every loaded/updated row that had a repair or an unfixable ISBN — `book_id`, `title`, `field`, `before`, `after`, `reason`
- `database_totals` after the run: total books, with ISBN-13, without any ISBN

`report.html` is a single file that opens from disk with no server. It has a button to pick `ingestion-log.json` and shows runs newest first: the numbers, the rejected rows with reasons, the repairs made (before → after), warnings on loaded rows, and the database totals. The person reading it must be able to answer "did everything load, and what do I need to look at?" without opening anything else.

## 10. Examples — what the rules say should happen

| # | `isbn` | `isbn13` | Outcome |
|---|---|---|---|
| 1 | `1416524797` | `9.78141652479e+12` | Valid ISBN-10. Float discarded; ISBN-13 derived → `9781416524793`. Loaded, warning (repair). |
| 2 | `439023483` | `9.78043902348e+12` | Padded → `0439023483`, checksum OK. ISBN-13 derived → `9780439023481`. Loaded, warning (repair). |
| 3 | `0439139600` | `9780439139601` | Both valid and agree. Loaded, no warning. |
| 4 | `0-450-19827-8` | `9780450198274` | Hyphens removed → `0450198278`, valid; agrees. Loaded, no warning (normalization only). |
| 5 | ` 162 001 4750 ` | `9781620014752` | Spaces removed → `1620014750`, valid; agrees. Loaded, no warning. |
| 6 | `031200009x` | `9780312000097` | Upper-cased → `031200009X`, valid; agrees. Loaded, no warning. |
| 7 | `9781982147600` | *(empty)* | Valid ISBN-13 in wrong column → moved to `isbn13`; `isbn10` derived → `1982147601`. Loaded, warning (repair). |
| 8 | *(empty)* | `9780062398123` | ISBN-13 valid; ISBN-10 derived → `0062398121`. Loaded, warning (repair). |
| 9 | `04390A3483` | *(empty)* | Letter in digits. Unfixable. Loaded, both NULL, warning. |
| 10 | `15287463097` | *(empty)* | 11 digits. Unfixable (which digit is extra is a guess). Loaded, both NULL, warning. |
| 11 | `1854433017` | *(empty)* | Checksum fails. Loaded, both NULL, warning. |
| 12 | `1555550126` | `9781555550134` | Both valid but disagree (`1555550126` → `9781555550127`). Loaded, both NULL, warning. |
| 13 | *(empty)* | *(empty)* | No ISBN. Loaded, both NULL, warning `no ISBN`. |
| 14 | `1416524797` on book 10013 | *(empty)* | ISBN already belongs to book 9. **Rejected**: `ISBN already assigned to book 9`. |
| 15 | book 10001 row, second identical copy | | **Rejected**: `duplicate row in file`. |
| 16 | book 24 re-delivered with `0439139600` / `9780439139601` after first load had float damage | | Same derived ISBNs → other columns identical → `skipped`. |
| 17 | book 132 re-delivered with higher `ratings_count` | | `updated`; log lists `ratings_count, work_ratings_count, ratings_5`. |
| 18 | book 25 re-delivered with both ISBN fields empty | | Stored ISBNs kept; nothing else changed → `skipped`. |
| 19 | `76783609419.0` in `isbn13`, `isbn` empty | | Not a 13-digit value, not a `e+12` float. Unfixable. Loaded, both NULL, warning. |
| 20 | `9790000000001` (979 prefix) | | Valid ISBN-13 if checksum passes; no ISBN-10 can be derived; `isbn10` NULL, no warning. |

## 11. Questions asked during the build and my answers

- *Should "updated" compare the raw CSV values or the values after normalization/repair?* — After. Otherwise re-delivering a hyphenated ISBN would count as an update every time.
- *Does an exact-duplicate check compare the whole row or just book_id?* — Whole row. Two rows with the same book_id but different content are a re-delivery within one file: the second is processed under rule 7 against what the first just loaded.
- *If a 979-prefixed ISBN-13 arrives with an ISBN-10 in the other column, do they "disagree"?* — A 979 ISBN-13 has no ISBN-10 form, so the ISBN-10 cannot belong to it. Treat as disagreement (rule 4): both NULL, warning.
- *Should numeric columns like `original_publication_year` be cleaned?* — Out of scope. Store them exactly as the file gives them. Only the two ISBN columns are validated.
- *Where does `isbn13_raw` come from for a row that was moved from the `isbn` column?* — Raw columns always hold what was literally in the file under that header, unchanged.
