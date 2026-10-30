"""Check that ingest.py does what the examples table in rules.md says.

Run:  python3 check_rules.py
Exit code 0 means every example matched.
"""
import ingest

# (isbn, isbn13) -> expected (isbn10, isbn13, has_warning)
CASES = [
    ("1416524797", "9.78141652479e+12",  ("1416524797", "9781416524793", True)),   # 1
    ("439023483",  "9.78043902348e+12",  ("0439023483", "9780439023481", True)),   # 2
    ("0439139600", "9780439139601",      ("0439139600", "9780439139601", False)),  # 3
    ("0-450-19827-8", "9780450198274",   ("0450198278", "9780450198274", False)),  # 4
    (" 162 001 4750 ", "9781620014752",  ("1620014750", "9781620014752", False)),  # 5
    ("031200009x", "9780312000097",      ("031200009X", "9780312000097", False)),  # 6
    ("9781982147600", "",                ("1982147601", "9781982147600", True)),   # 7
    ("", "9780062398123",                ("0062398121", "9780062398123", True)),   # 8
    ("04390A3483", "",                   (None, None, True)),                      # 9
    ("15287463097", "",                  (None, None, True)),                      # 10
    ("1854433017", "",                   (None, None, True)),                      # 11
    ("1555550126", "9781555550134",      (None, None, True)),                      # 12
    ("", "",                             (None, None, True)),                      # 13
    ("", "76783609419.0",                (None, None, True)),                      # 19
    ("", "9790000000001",                (None, "9790000000001", False)),          # 20
]

failed = 0
for i, (a, b, (e10, e13, ewarn)) in enumerate(CASES, 1):
    g10, g13, warns = ingest.resolve_isbns(a, b)
    ok = (g10, g13, bool(warns)) == (e10, e13, ewarn)
    print(f"{'ok  ' if ok else 'FAIL'} {a!r:18} {b!r:20} -> {g10}, {g13}, warnings={len(warns)}")
    if not ok:
        failed += 1
        print(f"      expected {e10}, {e13}, warning={ewarn}")
print(f"\n{len(CASES) - failed}/{len(CASES)} examples match rules.md")
raise SystemExit(1 if failed else 0)
