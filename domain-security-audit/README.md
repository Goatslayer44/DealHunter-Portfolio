# Public-Records Email & Website Checkup Tool

A zero-dependency Python tool that evaluates a domain's **public DNS TXT records** (SPF, DMARC) and a **standard HTTPS connection** (TLS certificate expiry + common response headers) and outputs a plain-English 1-page checkup report.

## Scope & Guardrails (Read First)
- **Public-records check only, NOT a security scan:** Reads public DNS TXT records and makes one standard HTTPS connection. **No port scanning, no vulnerability probing, and no access to internal systems.**
- **Offline by default:** `--input <fixture.json>` runs 100% offline with zero network traffic. Live public-records lookup runs only when `--live <domain>` is explicitly passed.
- **Honest unknowns:** Unavailable DNS or HTTPS checks stay `UNKNOWN` (`NEEDS_REVIEW`), never assumed `PASS`. Passing public-records checks does not guarantee overall security.
- **Synthetic samples only:** All files in `samples/` use RFC 2606 reserved `.example` domains.

## Usage (Windows PowerShell)

```powershell
# Offline plain-English report on a synthetic .example fixture
python domain_security_check.py --input samples\sample_weak.example.json

# Offline structured JSON output
python domain_security_check.py --input samples\sample_strong.example.json --json

# Explicit live public-records check (public DNS TXT + standard HTTPS only)
python domain_security_check.py --live example.com
```

## Run Offline Tests

```powershell
python -B -m unittest -v test_domain_security_check
```
