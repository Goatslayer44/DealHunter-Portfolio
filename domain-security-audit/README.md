# Public Email & Website Check (v1.1)

Offline-by-default, zero-dependency Python tool that checks **public DNS TXT records** (`SPF` and `DMARC` using the complete **RFC 9989 DNS Tree Walk**) and a **narrow standard HTTPS connection** (hostname, check time, TLS certificate validation, and redirect destination if present).

## Scope & Honesty Guardrails
- **Public-records check only, NOT a scan:** Performs **no port scanning, no vulnerability probing, and no access to internal systems.**
- **Sending path is always `UNVERIFIED`:** Presence of an SPF or DMARC record (even with `-all` or `p=reject`) is reported as `RECORD_FOUND` plus any syntax findings—never as a sending-path `PASS`. Every report states that the domain a business's invoices or emails actually send from may differ and has not been confirmed.
- **Complete RFC 9989 DMARC tree walk:** Walks upward to find inherited organizational-domain policies and names **both** the email domain checked and the domain where the applicable policy was found. Any timeout or incomplete walk is reported as `UNVERIFIED`, never `MISSING`. `p=none` is reported as a published monitoring policy, not missing.
- **Fictional samples only:** All files in `samples/` use RFC 2606 `.example` domains and are explicitly labeled fictional.

## Usage (Windows PowerShell)

```powershell
# Fictional acceptance fixture (inherited DMARC + SPF timeout -> UNVERIFIED + valid HTTPS)
python domain_security_check.py --input samples\sample_fictional_shop.example.json

# Other fictional samples
python domain_security_check.py --input samples\sample_strong.example.json
python domain_security_check.py --input samples\sample_weak.example.json

# Structured JSON output
python domain_security_check.py --input samples\sample_fictional_shop.example.json --json

# Explicit live public-records check (public DNS TXT + standard HTTPS only)
python domain_security_check.py --live example.com
```

## Run Offline Tests

```powershell
python -B -m unittest -v test_domain_security_check
```
