# Security Log Analyzer

A beginner-level Python tool that reads an authentication log and highlights
activity a security analyst might want to review. It uses **only the Python
standard library** and **fictional data only** (IP addresses come from the
reserved documentation ranges `192.0.2.0/24`, `198.51.100.0/24`, and `203.0.113.0/24`).

## What it detects

| Finding | Meaning |
| --- | --- |
| Suspicious IP addresses | An IP with at least N failed logins (default 5) |
| Usernames with repeated failures | A username that failed at least N times |
| Success after multiple failures | A successful login from an IP that had at least N earlier failures, which can indicate a guessed password |

These are leads for a human to review, not proof of an attack. Normal users
mistype passwords, and the tool does not consider time windows or geolocation.

## Log format

One event per line:

```text
2026-10-01 09:00:25 SUCCESS user=admin ip=203.0.113.50
2026-10-01 09:00:19 FAILED user=admin ip=203.0.113.50
```

Malformed lines (bad date, invalid IP, unknown status, odd characters, or very
long lines) are skipped and counted. Blank lines are ignored.

## Run it

From the repository root:

```bash
python -m security_log_analyzer.analyzer security_log_analyzer/sample_auth.log
python -m security_log_analyzer.analyzer security_log_analyzer/sample_auth.log --threshold 3
```

## Run the tests

```bash
python -m unittest security_log_analyzer.test_analyzer -v
```

Or run every test in the repository with `python -m unittest discover -v`.

## Files

- `analyzer.py` - parsing, analysis, report, and command-line interface
- `sample_auth.log` - fictional sample log, including three malformed lines
- `test_analyzer.py` - tests for normal activity, suspicious activity, malformed lines, and empty files

## Security notes

- Only reads the file path you give it; it never runs commands or makes network requests.
- Input is validated with a strict pattern, and IPs are checked with the `ipaddress` module.
- Do not add real logs to this public repository.
