"""Diagnose the isbn and isbn13 columns of one or more books CSVs. Read-only.

Usage: python3 diagnose_isbn.py books.csv books-batch2.csv
"""
import csv
import re
import sys
from collections import Counter, defaultdict


def isbn10_check_ok(s):
    total = sum((10 - i) * (10 if c == "X" else int(c)) for i, c in enumerate(s))
    return total % 11 == 0


def isbn13_check_ok(s):
    total = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(s))
    return total % 10 == 0


def classify10(raw):
    """Return (category, normalized_or_None)."""
    if raw is None or raw.strip() == "":
        return "empty", None
    s = raw
    if s != s.strip():
        cat_prefix = "whitespace"
    else:
        cat_prefix = None
    s = s.strip()
    if re.search(r"[\s-]", s):
        s2 = re.sub(r"[\s-]", "", s)
        return (cat_prefix or "separators"), s2.upper()
    if s.endswith("x"):
        return "lowercase_x", s.upper()
    if re.fullmatch(r"\d{9}[\dX]", s):
        return ("valid" if isbn10_check_ok(s) else "bad_checksum"), s
    if re.fullmatch(r"\d{13}", s):
        return "isbn13_in_isbn10_column", s
    if re.fullmatch(r"\d{1,9}", s):
        return "too_short_leading_zeros_lost", s.zfill(10)
    if re.fullmatch(r"\d{11,12}", s):
        return "too_long", None
    if re.search(r"[A-WYZa-wyz]", s):
        return "letter_in_digits", None
    return "other", None


def classify13(raw):
    if raw is None or raw.strip() == "":
        return "empty", None
    s = raw.strip()
    if re.fullmatch(r"\d\.\d+e\+12", s) or re.fullmatch(r"\d\.\d+E\+12", s):
        return "float_scientific_notation", str(int(float(s)))
    if re.fullmatch(r"\d{13}", s):
        return ("valid" if isbn13_check_ok(s) else "bad_checksum"), s
    if re.fullmatch(r"\d{13}\.0", s):
        return "float_trailing_point_zero", s[:-2]
    return "other", None


def main(paths):
    for path in paths:
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        print(f"\n=== {path}: {len(rows)} rows ===")
        for col, fn in (("isbn", classify10), ("isbn13", classify13)):
            cats = Counter()
            examples = defaultdict(list)
            for r in rows:
                cat, norm = fn(r[col])
                cats[cat] += 1
                if len(examples[cat]) < 3:
                    examples[cat].append((r["book_id"], repr(r[col]), norm, r["title"][:40]))
            print(f"\n-- {col} --")
            for cat, n in cats.most_common():
                print(f"{cat:32s} {n:6d}   e.g. {examples[cat]}")

        # Cross-checks
        print("\n-- cross-checks --")
        dup_ids = [k for k, v in Counter(r["book_id"] for r in rows).items() if v > 1]
        print("duplicate book_id within file:", dup_ids)
        full_dups = Counter(tuple(r.values()) for r in rows)
        print("exact duplicate rows:", sum(1 for v in full_dups.values() if v > 1))
        isbn_owner = defaultdict(set)
        for r in rows:
            _, n10 = classify10(r["isbn"])
            if n10:
                isbn_owner[n10].add((r["book_id"], r["title"][:30]))
        shared = {k: v for k, v in isbn_owner.items() if len(v) > 1}
        print("same isbn on different books:", shared)
        # isbn vs isbn13 agreement when both normalize
        mism = []
        for r in rows:
            _, n10 = classify10(r["isbn"])
            _, n13 = classify13(r["isbn13"])
            if n10 and n13 and len(n10) == 10 and len(n13) == 13:
                if n13[3:12] != n10[:9]:
                    mism.append((r["book_id"], n10, n13))
        print("isbn / isbn13 body disagree:", len(mism), mism[:5])
        both_empty = [r["book_id"] for r in rows if not r["isbn"].strip() and not r["isbn13"].strip()]
        print("rows with no ISBN at all:", len(both_empty), both_empty[:10])


if __name__ == "__main__":
    main(sys.argv[1:])
