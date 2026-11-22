"""Public-Records Small-Business Email & Website Checkup Tool.

Checks ONLY public DNS TXT records (SPF, DMARC) and a standard HTTPS/TLS
connection (certificate validity + common response headers). Performs NO port
scanning, NO vulnerability probing, and NO access to internal systems.

Offline by default (--input fixture.json). Live public-records lookup runs only
when --live is explicitly passed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
import socket
import ssl
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$",
    re.IGNORECASE,
)

PUBLIC_RECORDS_DISCLAIMER = (
    "Public-records check only (public DNS TXT records + standard HTTPS connection). "
    "No port scanning, no vulnerability probing, and no access to internal systems."
)


def validate_domain(raw: str) -> str:
    if not isinstance(raw, str):
        raise ValueError("Domain must be a string.")
    cleaned = raw.strip().lower().rstrip(".")
    if not cleaned or not DOMAIN_RE.match(cleaned):
        raise ValueError(f"Invalid domain name: {raw!r}")
    return cleaned


def _parse_dmarc_tags(record: str) -> dict[str, str]:
    tags: dict[str, str] = {}
    for part in record.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            tags[k.strip().lower()] = v.strip()
    return tags


def evaluate_public_records(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a public-records snapshot (SPF TXT, DMARC TXT, HTTPS/TLS metadata)."""
    domain = validate_domain(snapshot.get("domain", ""))
    spf_txts = snapshot.get("spf_txt_records")
    dmarc_txts = snapshot.get("dmarc_txt_records")
    https_info = snapshot.get("https")

    findings: list[dict[str, str]] = []

    def add_finding(severity: str, code: str, title: str, detail: str, fix: str) -> None:
        findings.append(
            {
                "severity": severity,
                "code": code,
                "title": title,
                "detail": detail,
                "plain_english_fix": fix,
            }
        )

    # --- 1. SPF evaluation ---
    spf_status = "UNKNOWN"
    spf_record = None
    if spf_txts is None:
        add_finding(
            "MEDIUM",
            "spf_lookup_unavailable",
            "SPF record unverified",
            "Public DNS TXT records were not available for SPF evaluation.",
            "Re-run when DNS lookup succeeds; never assume SPF is configured.",
        )
    else:
        spf_matches = [r.strip() for r in spf_txts if isinstance(r, str) and r.strip().lower().startswith("v=spf1")]
        if len(spf_matches) == 0:
            spf_status = "MISSING"
            add_finding(
                "HIGH",
                "spf_missing",
                "Missing SPF email record",
                f"No v=spf1 TXT record found for {domain}. Scammers can more easily spoof this domain, and real quotes/invoices may hit spam.",
                "Publish one v=spf1 TXT record listing only your authorized mail provider (e.g., Google Workspace or Microsoft 365).",
            )
        elif len(spf_matches) > 1:
            spf_status = "INVALID_MULTIPLE"
            spf_record = " | ".join(spf_matches)
            add_finding(
                "HIGH",
                "spf_multiple_records",
                "Multiple SPF records published (RFC 7208 error)",
                f"Found {len(spf_matches)} v=spf1 records. Receiving mail servers treat multiple SPF records as a permanent error.",
                "Merge authorized senders into a single v=spf1 TXT record.",
            )
        else:
            spf_record = spf_matches[0]
            tokens = spf_record.lower().split()
            if "+all" in tokens or "all" in tokens:
                spf_status = "OVERLY_PERMISSIVE"
                add_finding(
                    "HIGH",
                    "spf_plus_all",
                    "SPF allows any server (+all)",
                    f"SPF record '{spf_record}' authorizes every server on the internet to send as {domain}.",
                    "Replace +all with ~all (softfail) or -all (hardfail) after confirming all legitimate senders.",
                )
            elif "?all" in tokens:
                spf_status = "NEUTRAL"
                add_finding(
                    "MEDIUM",
                    "spf_neutral",
                    "SPF uses neutral policy (?all)",
                    "Neutral SPF provides no spoofing protection.",
                    "Confirm authorized senders and tighten to ~all or -all.",
                )
            elif "-all" in tokens or "~all" in tokens:
                spf_status = "PASS"
            else:
                spf_status = "INCOMPLETE"
                add_finding(
                    "MEDIUM",
                    "spf_no_all_mechanism",
                    "SPF missing explicit all qualifier",
                    f"SPF record '{spf_record}' does not end with ~all or -all.",
                    "Add ~all or -all at the end of your SPF record.",
                )

    # --- 2. DMARC evaluation ---
    dmarc_status = "UNKNOWN"
    dmarc_record = None
    if dmarc_txts is None:
        add_finding(
            "MEDIUM",
            "dmarc_lookup_unavailable",
            "DMARC record unverified",
            f"Public DNS TXT records were not available for _dmarc.{domain}.",
            "Re-run when DNS lookup succeeds; never assume DMARC is configured.",
        )
    else:
        dmarc_matches = [
            r.strip() for r in dmarc_txts if isinstance(r, str) and r.strip().lower().startswith("v=dmarc1")
        ]
        if len(dmarc_matches) == 0:
            dmarc_status = "MISSING"
            add_finding(
                "HIGH",
                "dmarc_missing",
                "Missing DMARC email policy",
                f"No v=DMARC1 TXT record found at _dmarc.{domain}. Mail servers have no domain-owner instruction on handling spoofed mail.",
                "Start with a monitoring DMARC record (v=DMARC1; p=none; rua=mailto:...) and move to p=quarantine or p=reject after verifying senders.",
            )
        elif len(dmarc_matches) > 1:
            dmarc_status = "INVALID_MULTIPLE"
            dmarc_record = " | ".join(dmarc_matches)
            add_finding(
                "HIGH",
                "dmarc_multiple_records",
                "Multiple DMARC records published",
                f"Found {len(dmarc_matches)} v=DMARC1 records at _dmarc.{domain}.",
                "Keep exactly one v=DMARC1 TXT record.",
            )
        else:
            dmarc_record = dmarc_matches[0]
            tags = _parse_dmarc_tags(dmarc_record)
            policy_val = tags.get("p", "").lower()
            if policy_val in {"quarantine", "reject"}:
                dmarc_status = "PASS"
            elif policy_val == "none":
                dmarc_status = "MONITOR_ONLY"
                add_finding(
                    "MEDIUM",
                    "dmarc_monitor_only",
                    "DMARC is monitor-only (p=none)",
                    "DMARC is present but does not tell receiving servers to quarantine or reject spoofed emails yet.",
                    "Review DMARC reports to confirm legitimate mail aligns, then upgrade to p=quarantine or p=reject.",
                )
            else:
                dmarc_status = "INVALID_POLICY"
                add_finding(
                    "HIGH",
                    "dmarc_missing_policy",
                    "DMARC policy tag (p=) missing or invalid",
                    f"DMARC record '{dmarc_record}' lacks a valid p= policy.",
                    "Set p=none (initial monitoring), p=quarantine, or p=reject.",
                )

    # --- 3. HTTPS / TLS public connection evaluation ---
    https_status = "UNKNOWN"
    cert_days_remaining: int | None = None
    if not isinstance(https_info, dict):
        add_finding(
            "MEDIUM",
            "https_unverified",
            "HTTPS status unverified",
            "No standard HTTPS connection metadata was supplied.",
            "Verify the website loads cleanly over https:// with a valid certificate.",
        )
    else:
        reachable = https_info.get("reachable")
        cert_days_remaining = https_info.get("cert_days_remaining")
        headers = {k.lower(): v for k, v in (https_info.get("headers") or {}).items()}
        if reachable is False:
            https_status = "UNREACHABLE"
            add_finding(
                "HIGH",
                "https_unreachable",
                "Website HTTPS connection failed",
                f"Standard HTTPS connection to https://{domain} did not succeed ({https_info.get('error', 'unknown error')}).",
                "Check web hosting and SSL/TLS certificate configuration so customers do not see browser security warnings.",
            )
        elif reachable is True:
            https_status = "PASS"
            if isinstance(cert_days_remaining, (int, float)):
                if cert_days_remaining < 0:
                    https_status = "CERT_EXPIRED"
                    add_finding(
                        "HIGH",
                        "tls_cert_expired",
                        "HTTPS certificate is expired",
                        f"Certificate expired {abs(int(cert_days_remaining))} day(s) ago.",
                        "Renew the SSL/TLS certificate immediately and enable automatic renewal.",
                    )
                elif cert_days_remaining < 14:
                    https_status = "CERT_EXPIRING_SOON"
                    add_finding(
                        "HIGH",
                        "tls_cert_expiring_soon",
                        "HTTPS certificate expires in under 14 days",
                        f"Only {int(cert_days_remaining)} day(s) remaining on the TLS certificate.",
                        "Confirm auto-renewal is working or renew the certificate before it expires.",
                    )
                elif cert_days_remaining < 30:
                    add_finding(
                        "MEDIUM",
                        "tls_cert_expiring_30d",
                        "HTTPS certificate expires in under 30 days",
                        f"{int(cert_days_remaining)} day(s) remaining on the TLS certificate.",
                        "Verify automatic certificate renewal is active.",
                    )
            if "strict-transport-security" not in headers:
                add_finding(
                    "INFO",
                    "missing_hsts",
                    "HSTS header not observed",
                    "Strict-Transport-Security header was not present on the HTTPS response.",
                    "Optional hardening: enable HSTS once HTTPS works reliably across all subdomains.",
                )
            if "x-content-type-options" not in headers:
                add_finding(
                    "INFO",
                    "missing_x_content_type_options",
                    "X-Content-Type-Options header not observed",
                    "X-Content-Type-Options: nosniff header was not present.",
                    "Optional hardening: add 'X-Content-Type-Options: nosniff' on your web host.",
                )

    high_count = sum(1 for f in findings if f["severity"] == "HIGH")
    med_count = sum(1 for f in findings if f["severity"] == "MEDIUM")
    if high_count > 0:
        overall = "ACTION_RECOMMENDED"
    elif med_count > 0:
        overall = "NEEDS_REVIEW"
    else:
        overall = "STRONG_PUBLIC_BASELINE"

    return {
        "domain": domain,
        "overall_status": overall,
        "disclaimer": PUBLIC_RECORDS_DISCLAIMER,
        "checks": {
            "spf": {"status": spf_status, "record": spf_record},
            "dmarc": {"status": dmarc_status, "record": dmarc_record},
            "https": {"status": https_status, "cert_days_remaining": cert_days_remaining},
        },
        "findings": findings,
    }


def _query_dns_txt(name: str, timeout_sec: float = 10.0) -> list[str] | None:
    """Read public DNS TXT records via nslookup (shell=False, validated name only)."""
    try:
        proc = subprocess.run(
            ["nslookup", "-type=txt", name],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            shell=False,
        )
    except Exception:
        return None
    if proc.returncode != 0 and not proc.stdout:
        return None
    records: list[str] = []
    for match in re.findall(r'"([^"]+)"', proc.stdout):
        records.append(match)
    return records


def _check_https_live(domain: str, timeout_sec: float = 10.0) -> dict[str, Any]:
    """Perform a single standard HTTPS connection + TLS certificate expiry check."""
    info: dict[str, Any] = {"reachable": False, "cert_days_remaining": None, "headers": {}}
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((domain, 443), timeout=timeout_sec) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                not_after = cert.get("notAfter") if cert else None
                if not_after:
                    exp_dt = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
                    info["cert_days_remaining"] = int((exp_dt - datetime.now(timezone.utc)).days)
        req = urllib.request.Request(
            f"https://{domain}/",
            method="HEAD",
            headers={"User-Agent": "205-Public-Records-Checkup/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout_sec, context=ctx) as resp:
            info["reachable"] = True
            info["http_status"] = getattr(resp, "status", 200)
            info["headers"] = dict(resp.headers.items())
    except urllib.error.HTTPError as exc:
        # Server answered over valid HTTPS even on 403/405 for HEAD
        info["reachable"] = True
        info["http_status"] = exc.code
        info["headers"] = dict(exc.headers.items()) if exc.headers else {}
    except Exception as exc:
        info["error"] = f"{type(exc).__name__}: {exc}"
    return info


def collect_live_public_records(domain: str) -> dict[str, Any]:
    clean = validate_domain(domain)
    return {
        "domain": clean,
        "collected_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "spf_txt_records": _query_dns_txt(clean),
        "dmarc_txt_records": _query_dns_txt(f"_dmarc.{clean}"),
        "https": _check_https_live(clean),
    }


def format_plain_report(result: dict[str, Any]) -> str:
    c = result["checks"]
    lines = [
        f"=== PUBLIC-RECORDS CHECKUP: {result['domain']} ===",
        f"Overall Status: {result['overall_status']}",
        f"Scope:          {result['disclaimer']}",
        "",
        "Summary:",
        f"  SPF:   {c['spf']['status']}" + (f" ({c['spf']['record']})" if c["spf"]["record"] else ""),
        f"  DMARC: {c['dmarc']['status']}" + (f" ({c['dmarc']['record']})" if c["dmarc"]["record"] else ""),
        f"  HTTPS: {c['https']['status']}"
        + (
            f" (cert days remaining: {c['https']['cert_days_remaining']})"
            if c["https"]["cert_days_remaining"] is not None
            else ""
        ),
        "",
        "Findings & Plain-English Next Steps:",
    ]
    if result["findings"]:
        for f in result["findings"]:
            lines.append(f"  [{f['severity']}] {f['title']} ({f['code']})")
            lines.append(f"      Why it matters: {f['detail']}")
            lines.append(f"      Suggested fix:  {f['plain_english_fix']}")
    else:
        lines.append("  None - public SPF, DMARC, and HTTPS baseline checks passed.")

    lines.append("")
    lines.append(
        "Note: Passing public-records checks does not guarantee overall security, and this report "
        "does not inspect internal networks, email accounts, or software vulnerabilities."
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Public-records small-business SPF/DMARC/HTTPS checkup (offline by default)."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input", type=Path, help="Offline JSON fixture containing public-records snapshot")
    group.add_argument("--live", type=str, metavar="DOMAIN", help="Run live public DNS TXT + standard HTTPS check")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Print structured JSON output")
    args = parser.parse_args()

    if args.input:
        snapshot = json.loads(args.input.read_text(encoding="utf-8"))
    else:
        snapshot = collect_live_public_records(args.live)

    result = evaluate_public_records(snapshot)
    if args.as_json:
        print(json.dumps(result, indent=2))
    else:
        print(format_plain_report(result))


if __name__ == "__main__":
    main()
