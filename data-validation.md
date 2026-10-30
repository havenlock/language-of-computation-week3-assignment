# Data validation: ISBNs in `books.csv` and `books-batch2.csv`

Diagnosis only. Neither file was changed and nothing was fixed. Produced by
`diagnose_isbn.py`, which reads the two `isbn` / `isbn13` columns row by row.

## What a valid ISBN is (what the checks below test)

Two kinds of ISBN exist:

| | ISBN-10 | ISBN-13 |
|---|---|---|
| Length | 10 characters | 13 digits |
| Allowed characters | digits; the **last** may be `X` (= 10) | digits only |
| Prefix | none | `978` or `979` (the "Bookland" EAN prefix) |
| Check digit | weighted sum (10,9,…,2) + check ≡ 0 mod 11 | alternating weights 1,3,1,3… ; sum ≡ 0 mod 10 |
| Status | issued until 2006; still printed on older books | the only kind issued since 2007 |

The last character of both is a **check digit**: it is computed from the other digits, so a single wrong digit or two swapped digits makes the checksum fail. A 10-digit ISBN converts to a 13-digit one deterministically: prepend `978`, drop the old check digit, recompute the new one. The reverse only works for the `978` prefix (a `979-` ISBN has no ISBN-10 form).

"Valid" below means: right length, right characters, and the check digit agrees with the other digits. A value can pass that test and still belong to the wrong book (see problem 9); the checksum proves the string is well-formed, not that it is true.

## File 1 — `books.csv` (10,000 rows, Goodbooks-10k)

### `isbn` column

| # | Problem | Rows | Example (book_id) | What it is | Information still there? |
|---|---|---:|---|---|---|
| 1 | Leading zeros lost | 6,601 | `439023483` (1, The Hunger Games) | 9 digits (sometimes fewer) that become a valid ISBN-10 when left-padded with zeros. 6,587 of 6,601 pass the checksum after padding. | **Yes** — the zeros are implied by the length; padding restores the original exactly. |
| 2 | Empty | 700 | `''` (106, Bossypants) | No value at all. | **No.** |
| 3 | Bad checksum, right shape | 9 | `9380658797` (1443) | Ten characters, but the check digit disagrees with the others — a typo somewhere in the string. | **Partly.** The string is there, but you cannot tell which digit is wrong without an outside source. |
| — | Valid as-is | 2,690 | `1416524797` (9, Angels & Demons) | | |

Across the whole file, 565 rows have neither an `isbn` nor an `isbn13`.

**Probable cause of #1:** the file passed through a spreadsheet or a numeric parser. A column of ISBNs that happens to contain only digits is read as integers, and integers do not keep leading zeros. (A 9-digit value means exactly one zero was dropped — ISBN-10s starting with `0` are the English-language block, which is why so many are affected.)

### `isbn13` column

| # | Problem | Rows | Example (book_id) | What it is | Information still there? |
|---|---|---:|---|---|---|
| 4 | Float in scientific notation | 9,407 | `9.78043902348e+12` (1) | The 13-digit number was stored as a floating-point value and written back with 12 significant digits. Reading it back gives `9780439023480` — the **last digit is always 0** and the 12th digit has been **rounded**. The true value for this row is `9780439023481`. Only 957 of the 9,407 (10%) happen to pass the ISBN-13 checksum, and most of those are coincidence. | **No, not from this column.** The check digit is gone and the 12th digit may be off by one (4,217 rows). It *is* recoverable from the `isbn` column when that is valid: 9,251 of the 9,407 rows have a usable ISBN-10 from which the exact ISBN-13 can be derived. |
| 5 | Empty | 585 | `''` (106) | | **No.** |
| 6 | Other numeric garbage | 8 | `76783609419.0` (958), `6.45573003012e+11` (2894) | Values with the wrong magnitude — 11 digits, or `e+11`. These were never 13-digit ISBNs; they look like UPC/EAN barcodes or already-broken values that went through the same float conversion. | **No.** |

**Probable cause of #4:** the same spreadsheet round trip as #1, one step worse. A 13-digit integer exceeds what a spreadsheet's default display (and Python's `repr` of a float at 12 significant figures) will show without switching to exponent form. Once written as `9.78e+12` text, the dropped digits are gone for good.

**Consistency check:** for the 9,251 rows where the ISBN-10 is usable, deriving the ISBN-13 from it and comparing with the float value agrees in only 929 cases; in 4,217 cases even the 12th digit differs. The two columns in this file were originally consistent — the disagreement is entirely float damage, not two different ISBNs for the same book.

## File 2 — `books-batch2.csv` (31 rows, same supplier, one week later)

A much smaller delivery, but it contains **every** problem from file 1 plus seven new ones. Fifteen of its 31 rows are books already present in `books.csv` (same `book_id`); sixteen are new titles.

### `isbn` column

| # | Problem | Rows | Example (book_id) | What it is | Information still there? |
|---|---|---:|---|---|---|
| 1 | Leading zero lost | 7 | `441773028` (10012) | As in file 1. | Yes (pad). |
| 2 | Empty | 5 | `''` (106, 10006, 10010, 25, 10005) | Three of these (106, 10010, 25) have no `isbn13` either. | No. |
| 3 | Bad checksum | 1 | `1854433017` (10007, Small Hours) | Ten digits, checksum fails; no `isbn13` to cross-check. | Partly. |
| 7 | Letter inside the digits | 1 | `04390A3483` (10008, The Glass Aviary) | An `A` where a digit should be — looks like an OCR or keying error (`A` for `4`?). Not a legal ISBN character. | Partly — nine digits are present; the tenth is a guess. |
| 8 | Wrong length (11 digits) | 1 | `15287463097` (10009, Borrowed Light) | One digit too many. Note it is book 10001's ISBN `1528746309` with a `7` appended — a keying error. | Partly — but which digit is extra is a guess. |
| 9 | ISBN-13 in the ISBN-10 column | 1 | `9781982147600` (10014) | A valid ISBN-13 placed in the wrong column; `isbn13` is empty. | Yes — the value is valid, just misfiled. |
| 10 | Lowercase check character | 1 | `031200009x` (10004, Winter Orchard) | `x` instead of `X`. Valid once upper-cased. | Yes. |
| 11 | Hyphens | 1 | `0-450-19827-8` (10002, Salt and Ember) | The human-readable hyphenated form. Valid once hyphens are removed. | Yes. |
| 12 | Spaces inside and around | 1 | `' 162 001 4750 '` (10003) | Leading/trailing and internal spaces. Valid once stripped. | Yes. |
| — | Valid as-is | 12 | | | |

### `isbn13` column

| # | Problem | Rows | Example | Information still there? |
|---|---|---:|---|---|
| 4 | Float, scientific notation | 14 | `9.78140130858e+12` (132) | No (recover from `isbn`). |
| 5 | Empty | 8 | | No. |
| — | Valid as-is | 9 | `9780439139601` (24) | |

### Problems that only show up when rows are compared to each other

| # | Problem | Rows | Example | Notes |
|---|---|---:|---|---|
| 13 | Exact duplicate row | 1 pair | book_id 10001, *The Lantern Keeper's Daughter*, appears twice, byte-for-byte identical. | Classic copy-paste or re-export. Loading both would create a duplicate. |
| 14 | Same ISBN on two different books | 1 | `1416524797` is *Angels & Demons* (9, from file 1) **and** *Paper Moons* (10013, new). | Both checksums pass. One of them is wrong, and the checksum cannot tell you which. This is the case where "valid" ≠ "true". |
| 15 | `isbn` and `isbn13` disagree, both valid | 1 | 10011, *Tides of Marrow Bay*: `1555550126` converts to `9781555550127`, but the file says `9781555550134`. | Each passes its own checksum; they are two different ISBNs. Likely a different edition's number landed in one column. |
| 16 | Re-delivered rows that changed | 15 re-deliveries | 24: ISBNs now **correct** (`0439139600` / `9780439139601`) where file 1 had them broken. 25: ISBNs now **blank** where file 1 had them. 132, 14, 13, 134: rating counts went up. 10 rows: identical. | A re-delivery can be better, worse, or just newer than what is already loaded. |
| 17 | Row with nothing to identify it | 1 | 10010, author `Unknown`, title `Untitled Manuscript`, no ISBN of either kind. | Has a `book_id` and nothing else usable. |

## What probably caused all this, in one paragraph

File 1 was exported through a spreadsheet: every all-digit ISBN column was parsed as a number, so leading zeros vanished and 13-digit values overflowed into `9.78e+12` floats that lost their last digit. File 2 came from the same supplier a week later and shows the same export damage, plus the kind of errors people make when rows are typed or pasted by hand: a letter for a digit, an extra digit, hyphens and spaces left in, a value in the wrong column, a row pasted twice, and an ISBN copied from a different book. Several rows are re-sends of books already delivered, some with updated numbers and one with its ISBNs wiped.

## How this bears on the ingestion rules (Part 3)

Three kinds of problem, three different situations:

- **Formatting damage that is fully reversible** (#1 pad zeros, #4-via-#1 derive ISBN-13 from ISBN-10, #9 misfiled column, #10 case, #11 hyphens, #12 whitespace): the original value can be reconstructed exactly, and the result can be verified by the checksum.
- **Damage where the original is gone** (#2, #5, #6, #17): nothing to repair; the row either loads without an ISBN or doesn't load.
- **Damage where a repair would be a guess** (#3, #7, #8, #14, #15): the string is there but at least one character is wrong, and the checksum can say *that* it is wrong, not *what* it should be. A guess that passes the checksum is still a guess.

And two questions the rules have to answer before any code is written: what makes two rows "the same book" (book_id? ISBN? both?), and what happens when a book that is already loaded arrives again with different data.
