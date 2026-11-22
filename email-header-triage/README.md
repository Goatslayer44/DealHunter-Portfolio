# Email Header & Phishing Triage Analyzer

Offline, zero-dependency Python tool that parses raw `.eml` email files and produces a plain-English (or JSON) security triage report. Built for SOC analyst triage practice and practical small-business/home email safety reviews.

## What it checks (100% offline)
- **Authentication signals:** Extracts `SPF`, `DKIM`, and `DMARC` results from `Authentication-Results` and `Received-SPF` headers. Missing headers stay `UNKNOWN` (never assumed `pass`).
- **Identity alignment & spoofing:** Flags `From` vs. `Return-Path` mismatches, `From` vs. `Reply-To` mismatches (common in invoice/BEC fraud), and display-name spoofing (an email address from another domain embedded in the display name).
- **Safe link inspection:** Extracts plain-text and HTML `<a href>` links, **defangs** every URL (`hxxps://...[.]...`) so links cannot be clicked accidentally, and flags raw IP hosts, punycode (`xn--`), `@` redirect tricks, and mismatched link text vs. destination domains.

## Honest limitations
- **Static header triage only:** Passing SPF/DKIM/DMARC does **not** prove an email is safe (compromised legitimate accounts still pass authentication).
- **Header trust boundary:** `Authentication-Results` is only trustworthy when added by the recipient's own mail server.
- **No live network calls:** The tool never fetches URLs, performs DNS lookups, or opens attachments.

## Usage (Windows PowerShell)

```powershell
# Plain-English triage report
python email_header_analyzer.py samples\sample_phish.eml

# Structured JSON output
python email_header_analyzer.py samples\sample_legit.eml --json
```

## Run offline tests

```powershell
python -B -m unittest -v test_email_header_analyzer
```

All sample `.eml` files in `samples/` are synthetic fixtures using RFC 2606 reserved `.example` domains and documentation IP addresses (`198.51.100.0/24`). No real emails, secrets, or personal data are included.
