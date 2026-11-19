# Spreadsheet Cleanup Tool

Merges a folder of messy CSV sales exports into **one clean file** — and tells you exactly what it fixed.

Built for the real-world problem every small business hits: three locations (or three months, or three employees) export the "same" spreadsheet three different ways, and nothing lines up.

## What it fixes

- Column names that don't match (`Order ID`, `order_id`, `OrderID` → `order_id`)
- Dates in mixed formats (`11/02/2026`, `2026-11-03`, `Nov 4 2026` → `2026-11-04`)
- Messy names (`  john   SMITH ` → `John Smith`)
- Money stored as text (`$1,200.00` → `1200.00`)
- Duplicate rows and repeated order IDs
- Empty rows

Anything it *can't* fix safely (like a date typed as `not-a-date`) is counted and reported in the summary instead of being silently guessed at.

## Run it

```bash
python spreadsheet_cleanup.py sample_data output
```

Outputs in the output folder:

- `clean_sales.csv` — the merged, cleaned, sorted data
- `summary.txt` — files merged, rows in/out, duplicates removed, values fixed, total sales

## Demo result (included sample data)

3 messy files, 17 rows in → **13 clean rows out**: 3 duplicates removed, 1 empty row dropped, 10 dates reformatted, 6 amounts cleaned, 1 bad date flagged for a human. Total sales: **$1,455.25**.

## Tech

Python 3 standard library only (`csv`, `datetime`, `re`) — no installs, runs anywhere.

---

*Built by Colton Thorpe — Bevill State cybersecurity student and Python builder (DealHunter resale tools). Custom cleanups and automations available for small businesses through 205 Digital Help & Research.*
