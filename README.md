# DealHunter Portfolio

![Tests](https://github.com/Goatslayer44/DealHunter-Portfolio/actions/workflows/tests.yml/badge.svg)

## Who's behind this

I'm Colton Thorpe, a cybersecurity student at Bevill State Community College (A.A.S., April 2027) and the owner of 205 Digital Help & Research in Jasper, Alabama. I build and test small, practical tools for local businesses — email and website security checks, spreadsheet cleanup, and a missed-call text-back pilot — and I publish the test results, including what the tools can't claim yet.

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

## Featured: Email Header & Phishing Triage Analyzer

The [`email-header-triage/`](email-header-triage/) folder contains an offline,
zero-dependency Python tool that parses raw `.eml` headers, extracts SPF/DKIM/DMARC
signals (keeping missing headers `UNKNOWN`), flags `From`/`Reply-To`/`Return-Path`
mismatches and display-name spoofing, and defangs risky links (raw IPs, punycode,
`@` tricks, mismatched HTML anchors). Uses synthetic RFC 2606 `.example` fixtures
only and includes 6 offline unit tests. See its
[README](email-header-triage/README.md) for details.

```bash
python email-header-triage/email_header_analyzer.py email-header-triage/samples/sample_phish.eml
```

## Featured: Public Email & Website Check (v1.1)

The [`domain-security-audit/`](domain-security-audit/) folder contains an offline-by-default,
zero-dependency Python tool that checks public DNS TXT records (`SPF` and `DMARC` via the
complete **RFC 9989 DNS Tree Walk**) and a narrow standard HTTPS connection (hostname,
check time, TLS certificate validation, and redirect destination if present). Performs
**no port scanning and no vulnerability probing**; sending-path verification stays
`UNVERIFIED`. Uses fictional RFC 2606 `.example` fixtures and includes 9 offline unit tests.
See its [README](domain-security-audit/README.md) for details.

```bash
python domain-security-audit/domain_security_check.py --input domain-security-audit/samples/sample_fictional_shop.example.json
```

## Featured: AI Receptionist Feasibility Eval

The [`ai-receptionist-eval/`](ai-receptionist-eval/) folder contains an offline,
zero-dependency Python evaluation harness testing whether an AI phone assistant can
reliably extract structured customer intake records (spelled names, 10-digit callback
numbers, services, and agreed appointment times) under realistic call disruptions—and
comparing it honestly against a simpler **Missed-Call Text-Back + Inquiry Organizer**.

- **Current state:** 5-sitting roadmap complete — 40 fictional call scenarios
  (`CALL-01`–`CALL-40`), strict JSON schema, hardened field-level scorer with zero
  silent passes (`EXACT` vs. `NORMALIZED` vs. `MISMATCH`), mock pipeline design &
  cost model (`DESIGN.md`), local **Missed-Call Text-Back** prototype
  (`missed_call_textback.py`, scoring `37/40` fictional mobile calls at `100%` exact
  / `0` normalized and routing `3` landlines to a voice callback queue), **11/11
  offline unit tests passing**, official-source GPT-Live-1.1 research memo,
  comparison one-pager, `DEMO-SCRIPT.md` (the 60-second pilot demo script), and
  `CANT-CLAIM.md` (the truth-boundaries doc).
- **Fictional-data rule:** 100% fictional callers, `.example` businesses, and `555`
  numbers only. Zero paid API calls, zero real phone numbers, zero recorded calls.
- **What it refuses to claim:** Does not claim live voice/audio accuracy, Spanish
  acoustic performance, or real-world telephony/backend cost quotes (all marked
  `UNVERIFIED` until measured on a real line).

See its [README](ai-receptionist-eval/README.md) for documented normalization rules and
usage.

```bash
python ai-receptionist-eval/scorer.py --gold ai-receptionist-eval/gold_answers.json --pred ai-receptionist-eval/gold_answers.json --fail-on-schema-error
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
| `email-header-triage/` | Offline `.eml` header & phishing triage analyzer with synthetic samples and tests |
| `domain-security-audit/` | Public-records SPF/DMARC/HTTPS checkup tool (no port scanning) with synthetic samples and tests |
| `ai-receptionist-eval/` | Offline 40-scenario AI receptionist feasibility harness & hardened scorer (fictional data only) |
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
