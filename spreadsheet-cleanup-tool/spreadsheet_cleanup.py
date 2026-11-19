#!/usr/bin/env python3
"""
Spreadsheet Cleanup Tool
------------------------
Merges a folder of messy CSV sales exports into ONE clean file.

What it fixes automatically:
  - Inconsistent column names ("Order ID", "order_id", "OrderID" -> order_id)
  - Mixed date formats (11/02/2026, 2026-11-03, Nov 4 2026 -> 2026-11-04)
  - Messy customer names ("  john   SMITH " -> "John Smith")
  - Amounts stored as text ("$1,200.50" -> 1200.50)
  - Exact duplicate rows and repeated order IDs
  - Completely empty rows

Usage:
    python spreadsheet_cleanup.py INPUT_FOLDER OUTPUT_FOLDER

Outputs (in OUTPUT_FOLDER):
    clean_sales.csv   - the merged, cleaned data
    summary.txt       - what was fixed, in plain numbers

No third-party packages needed - Python standard library only.
"""

import csv
import os
import re
import sys
from datetime import datetime

# Map every header spelling we have seen in the wild to one clean name.
HEADER_MAP = {
    "order id": "order_id",
    "order_id": "order_id",
    "orderid": "order_id",
    "order #": "order_id",
    "customer": "customer",
    "customer name": "customer",
    "name": "customer",
    "date": "date",
    "order date": "date",
    "sale date": "date",
    "product": "product",
    "item": "product",
    "amount": "amount",
    "total": "amount",
    "price": "amount",
    "sale amount": "amount",
}

DATE_FORMATS = [
    "%Y-%m-%d",   # 2026-11-03
    "%m/%d/%Y",   # 11/03/2026
    "%m-%d-%Y",   # 11-03-2026
    "%b %d %Y",   # Nov 3 2026
    "%B %d, %Y",  # November 3, 2026
    "%d %b %Y",   # 3 Nov 2026
]

CLEAN_COLUMNS = ["order_id", "customer", "date", "product", "amount"]


def clean_header(raw):
    return HEADER_MAP.get(raw.strip().lower())


def clean_date(value, stats):
    value = value.strip()
    if not value:
        return ""
    for fmt in DATE_FORMATS:
        try:
            parsed = datetime.strptime(value, fmt)
            iso = parsed.strftime("%Y-%m-%d")
            if iso != value:
                stats["dates_fixed"] += 1
            return iso
        except ValueError:
            continue
    stats["dates_unparsed"] += 1
    return value  # leave it, but count it so the summary is honest


def clean_amount(value, stats):
    value = value.strip()
    if not value:
        return ""
    cleaned = value.replace("$", "").replace(",", "").strip()
    try:
        number = float(cleaned)
    except ValueError:
        stats["amounts_unparsed"] += 1
        return value
    if cleaned != value:
        stats["amounts_fixed"] += 1
    return f"{number:.2f}"


def clean_name(value):
    return re.sub(r"\s+", " ", value.strip()).title()


def main():
    if len(sys.argv) != 3:
        print("Usage: python spreadsheet_cleanup.py INPUT_FOLDER OUTPUT_FOLDER")
        sys.exit(1)

    input_folder, output_folder = sys.argv[1], sys.argv[2]
    os.makedirs(output_folder, exist_ok=True)

    stats = {
        "files_read": 0,
        "rows_read": 0,
        "empty_rows_dropped": 0,
        "exact_duplicates_removed": 0,
        "duplicate_order_ids_removed": 0,
        "dates_fixed": 0,
        "dates_unparsed": 0,
        "amounts_fixed": 0,
        "amounts_unparsed": 0,
    }

    seen_rows = set()
    seen_order_ids = set()
    clean_rows = []

    csv_files = sorted(f for f in os.listdir(input_folder) if f.lower().endswith(".csv"))
    for filename in csv_files:
        path = os.path.join(input_folder, filename)
        stats["files_read"] += 1
        with open(path, newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle)
            try:
                raw_headers = next(reader)
            except StopIteration:
                continue
            column_map = {}
            for idx, header in enumerate(raw_headers):
                clean = clean_header(header)
                if clean:
                    column_map[idx] = clean

            for raw_row in reader:
                stats["rows_read"] += 1
                if not any(cell.strip() for cell in raw_row):
                    stats["empty_rows_dropped"] += 1
                    continue

                row = {col: "" for col in CLEAN_COLUMNS}
                for idx, clean in column_map.items():
                    if idx < len(raw_row):
                        row[clean] = raw_row[idx]

                row["customer"] = clean_name(row["customer"])
                row["product"] = row["product"].strip()
                row["order_id"] = row["order_id"].strip()
                row["date"] = clean_date(row["date"], stats)
                row["amount"] = clean_amount(row["amount"], stats)

                fingerprint = tuple(row[col] for col in CLEAN_COLUMNS)
                if fingerprint in seen_rows:
                    stats["exact_duplicates_removed"] += 1
                    continue
                if row["order_id"] and row["order_id"] in seen_order_ids:
                    stats["duplicate_order_ids_removed"] += 1
                    continue
                seen_rows.add(fingerprint)
                if row["order_id"]:
                    seen_order_ids.add(row["order_id"])
                clean_rows.append(row)

    clean_rows.sort(key=lambda r: (r["date"], r["order_id"]))

    out_csv = os.path.join(output_folder, "clean_sales.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CLEAN_COLUMNS)
        writer.writeheader()
        writer.writerows(clean_rows)

    total_sales = sum(float(r["amount"]) for r in clean_rows if r["amount"])
    summary_lines = [
        "SPREADSHEET CLEANUP - SUMMARY",
        "=" * 40,
        f"Files merged:                 {stats['files_read']}",
        f"Rows read in:                 {stats['rows_read']}",
        f"Empty rows dropped:           {stats['empty_rows_dropped']}",
        f"Exact duplicates removed:     {stats['exact_duplicates_removed']}",
        f"Repeat order IDs removed:     {stats['duplicate_order_ids_removed']}",
        f"Dates reformatted:            {stats['dates_fixed']}",
        f"Amounts cleaned ($, commas):  {stats['amounts_fixed']}",
        f"Dates that need a human look: {stats['dates_unparsed']}",
        f"Amounts that need a look:     {stats['amounts_unparsed']}",
        "-" * 40,
        f"Clean rows out:               {len(clean_rows)}",
        f"Total sales in clean file:    ${total_sales:,.2f}",
    ]
    summary = "\n".join(summary_lines)
    with open(os.path.join(output_folder, "summary.txt"), "w", encoding="utf-8") as handle:
        handle.write(summary + "\n")

    print(summary)
    print(f"\nClean file written to: {out_csv}")


if __name__ == "__main__":
    main()
