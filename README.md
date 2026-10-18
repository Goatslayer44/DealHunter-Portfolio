# DealHunter Portfolio

![Tests](https://github.com/Goatslayer44/DealHunter-Portfolio/actions/workflows/tests.yml/badge.svg)

A small Python project that identifies products from their titles, estimates
resale profit, and stores results in a SQLite database. It is a beginner-level
portfolio project built to practice Python, SQL, input validation, and automated testing.

## Featured: Security Log Analyzer

The [`security_log_analyzer/`](security_log_analyzer/) folder contains a
cybersecurity learning project that reads fictional authentication logs and
flags repeated failed logins, suspicious IP addresses, and successful logins
that follow multiple failures. It uses only the standard library and has its
own unit tests. See its [README](security_log_analyzer/README.md) for details.

```bash
python -m security_log_analyzer.analyzer security_log_analyzer/sample_auth.log
```

## Product Matching and Profit Demo Features

- Rule-based product identification using regular expressions
- Profit calculation: resale price minus purchase price, shipping, and fees
- Input validation (rejects negative, non-numeric, NaN, and empty values)
- SQLite storage using parameterized queries, with duplicate-title detection
- Unit tests that run automatically with GitHub Actions

## Technologies

Python 3.10+, SQLite, SQL, regular expressions, `unittest`, Git and GitHub Actions.
No third-party packages are required.

## Getting Started

```bash
git clone https://github.com/Goatslayer44/DealHunter-Portfolio.git
cd DealHunter-Portfolio

python profit_calculator.py   # profit example
python product_matcher.py     # product matching examples
python database.py            # saves sample products to a local portfolio.db
```

## Running the Tests

```bash
python -m unittest discover -v
```

Tests use in-memory databases, so they do not create or change `portfolio.db`.

## Project Structure

| File | Purpose |
| --- | --- |
| `profit_calculator.py` | Validates prices and calculates profit |
| `product_matcher.py` | Validates titles and identifies model/category |
| `database.py` | Creates the SQLite table, saves and lists products |
| `test_*.py` | Unit tests for each module |
| `security_log_analyzer/` | Authentication log analyzer with sample data, docs, and tests |
| `.github/workflows/tests.yml` | Runs the tests on every push and pull request |

## Example Output

```text
Product: John Deere Z930M Mower Part
Model: Z930M
Category: LAWN MOWER PART
Expected Profit: $180.00
```

## Limitations

- All prices are fictional sample values. The project uses no live marketplace
  data (including eBay) and no AI.
- Matching only recognizes a few hard-coded examples.
- Duplicates are detected by exact title only.
- The calculated profit is an arithmetic example, not a market estimate or a guarantee.

## Security Notes

- SQL uses parameterized queries (no string-built SQL).
- Databases, `.env` files, and keys are listed in `.gitignore`.
- The repository contains no credentials or personal data.

## About

This is a standalone educational demo inspired by a larger private project,
which is maintained separately and is not part of this repository.
