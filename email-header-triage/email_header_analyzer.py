"""Offline Email Header & Phishing Triage Analyzer (read-only, zero network calls).

Treats every email header, body, and link as untrusted data. Never fetches URLs,
never opens attachments, and never executes external content. Designed for SOC
triage practice and plain-English small-business/home email safety reviews.
"""
from __future__ import annotations

import argparse
import email
from email import policy
from email.utils import parseaddr
import ipaddress
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


URL_RE = re.compile(r"https?://[^\s<>\"'()]+", re.IGNORECASE)
EMAIL_IN_TEXT_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
AUTH_MECHANISM_RE = {
    "spf": re.compile(r"\bspf\s*=\s*([a-z0-9_-]+)", re.IGNORECASE),
    "dkim": re.compile(r"\bdkim\s*=\s*([a-z0-9_-]+)", re.IGNORECASE),
    "dmarc": re.compile(r"\bdmarc\s*=\s*([a-z0-9_-]+)", re.IGNORECASE),
}


def extract_domain(address: str) -> str:
    _, addr = parseaddr(address or "")
    if "@" not in addr:
        return ""
    return addr.rsplit("@", 1)[1].strip().lower().rstrip(".")


def base_domain(domain: str) -> str:
    parts = [p for p in domain.lower().strip(".").split(".") if p]
    if len(parts) <= 2:
        return ".".join(parts)
    return ".".join(parts[-2:])


def defang_url(url: str) -> str:
    cleaned = url.strip().rstrip(".,;:")
    defanged = re.sub(r"^https://", "hxxps://", cleaned, flags=re.IGNORECASE)
    defanged = re.sub(r"^http://", "hxxp://", defanged, flags=re.IGNORECASE)
    parsed = urlparse(cleaned)
    host = parsed.hostname or ""
    if host:
        defanged = defanged.replace(host, host.replace(".", "[.]"), 1)
    return defanged


def is_ip_host(host: str) -> bool:
    if not host:
        return False
    try:
        ipaddress.ip_address(host.strip("[]"))
        return True
    except ValueError:
        return False


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.anchors: list[tuple[str, str]] = []
        self.text_chunks: list[str] = []
        self._href: str | None = None
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            for k, v in attrs:
                if k.lower() == "href" and v:
                    self._href = v.strip()
                    self._chunks = []
                    break

    def handle_data(self, data: str) -> None:
        self.text_chunks.append(data)
        if self._href is not None:
            self._chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, "".join(self._chunks).strip()))
            self._href = None
            self._chunks = []


def _parse_auth_results(msg: email.message.EmailMessage) -> dict[str, str]:
    results = {"spf": "UNKNOWN", "dkim": "UNKNOWN", "dmarc": "UNKNOWN"}
    auth_headers = msg.get_all("Authentication-Results", [])
    combined = "\n".join(str(h) for h in auth_headers)

    for mech, rx in AUTH_MECHANISM_RE.items():
        match = rx.search(combined)
        if match:
            results[mech] = match.group(1).lower()

    if results["spf"] == "UNKNOWN":
        received_spf = msg.get_all("Received-SPF", [])
        if received_spf:
            first_token = str(received_spf[0]).strip().split(" ", 1)[0].lower()
            if first_token in {"pass", "fail", "softfail", "neutral", "none", "temperror", "permerror"}:
                results["spf"] = first_token

    return results


def _collect_bodies(msg: email.message.EmailMessage) -> tuple[str, str]:
    plain_parts: list[str] = []
    html_parts: list[str] = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                continue
            ctype = part.get_content_type()
            try:
                content = part.get_content()
            except Exception:
                continue
            if not isinstance(content, str):
                continue
            if ctype == "text/plain":
                plain_parts.append(content)
            elif ctype == "text/html":
                html_parts.append(content)
    else:
        try:
            content = msg.get_content()
        except Exception:
            content = ""
        if isinstance(content, str):
            if msg.get_content_type() == "text/html":
                html_parts.append(content)
            else:
                plain_parts.append(content)
    return "\n".join(plain_parts), "\n".join(html_parts)


def analyze_email_bytes(raw_bytes: bytes) -> dict[str, Any]:
    msg = email.message_from_bytes(raw_bytes, policy=policy.default)

    from_hdr = str(msg.get("From", "") or "")
    reply_to_hdr = str(msg.get("Reply-To", "") or "")
    return_path_hdr = str(msg.get("Return-Path", "") or "")
    subject_hdr = str(msg.get("Subject", "") or "")
    date_hdr = str(msg.get("Date", "") or "")
    message_id_hdr = str(msg.get("Message-ID", "") or "")

    from_display, from_addr = parseaddr(from_hdr)
    from_dom = extract_domain(from_hdr)
    reply_dom = extract_domain(reply_to_hdr)
    return_dom = extract_domain(return_path_hdr)

    auth = _parse_auth_results(msg)
    received_hops = [str(h).strip() for h in msg.get_all("Received", [])]

    findings: list[dict[str, str]] = []

    def add_finding(severity: str, code: str, detail: str) -> None:
        findings.append({"severity": severity, "code": code, "detail": detail})

    # 1. Authentication checks (missing stays UNKNOWN, never assumed pass)
    for mech in ("spf", "dkim", "dmarc"):
        val = auth[mech]
        if val in {"fail", "softfail", "permerror"}:
            add_finding("HIGH", f"{mech}_failed", f"{mech.upper()} reported '{val}' in header.")
        elif val in {"UNKNOWN", "none", "neutral", "temperror"}:
            add_finding(
                "MEDIUM",
                f"{mech}_unverified",
                f"{mech.upper()} is '{val}' (cannot verify authentication from headers alone).",
            )

    # 2. Identity alignment checks
    if from_dom and return_dom and base_domain(from_dom) != base_domain(return_dom):
        add_finding(
            "MEDIUM",
            "return_path_mismatch",
            f"From domain ({from_dom}) differs from Return-Path domain ({return_dom}).",
        )
    if from_dom and reply_dom and base_domain(from_dom) != base_domain(reply_dom):
        add_finding(
            "HIGH",
            "reply_to_mismatch",
            f"From domain ({from_dom}) differs from Reply-To domain ({reply_dom}) - replies go elsewhere.",
        )

    # Display-name spoofing: email address embedded inside display name points to another domain
    if from_display and from_dom:
        for embedded in EMAIL_IN_TEXT_RE.findall(from_display):
            emb_dom = embedded.rsplit("@", 1)[1].lower()
            if base_domain(emb_dom) != base_domain(from_dom):
                add_finding(
                    "HIGH",
                    "display_name_spoof",
                    f"Display name embeds '{embedded}' while actual From domain is '{from_dom}'.",
                )
                break

    # 3. Body URL extraction & defanging
    plain_body, html_body = _collect_bodies(msg)
    raw_urls: list[str] = []
    seen: set[str] = set()
    for url in URL_RE.findall(plain_body):
        cleaned = url.rstrip(".,;:")
        if cleaned not in seen:
            seen.add(cleaned)
            raw_urls.append(cleaned)

    anchor_parser = _AnchorParser()
    if html_body:
        anchor_parser.feed(html_body)
        for url in URL_RE.findall("\n".join(anchor_parser.text_chunks)):
            cleaned = url.rstrip(".,;:")
            if cleaned not in seen:
                seen.add(cleaned)
                raw_urls.append(cleaned)
        for href, label in anchor_parser.anchors:
            if href.lower().startswith(("http://", "https://")):
                cleaned = href.rstrip(".,;:")
                if cleaned not in seen:
                    seen.add(cleaned)
                    raw_urls.append(cleaned)
                # Detect misleading link text showing a different domain than href
                href_host = (urlparse(cleaned).hostname or "").lower()
                for label_url in URL_RE.findall(label):
                    label_host = (urlparse(label_url).hostname or "").lower()
                    if href_host and label_host and base_domain(href_host) != base_domain(label_host):
                        add_finding(
                            "HIGH",
                            "mismatched_anchor_url",
                            f"Link text shows '{label_host}' but actual destination is '{href_host}'.",
                        )

    url_reports: list[dict[str, Any]] = []
    for url in raw_urls:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        flags: list[str] = []
        if is_ip_host(host):
            flags.append("raw_ip_host")
            add_finding("HIGH", "raw_ip_url", f"Link points directly to an IP address: {defang_url(url)}")
        if "xn--" in host:
            flags.append("punycode_domain")
            add_finding("HIGH", "punycode_url", f"Link uses punycode/IDN domain: {defang_url(url)}")
        if "@" in (parsed.netloc or ""):
            flags.append("at_sign_in_netloc")
            add_finding("HIGH", "at_sign_url", f"Link contains '@' credential/redirect trick: {defang_url(url)}")
        if parsed.scheme.lower() == "http":
            flags.append("unencrypted_http")
        url_reports.append({"defanged": defang_url(url), "host": host, "flags": flags})

    high_count = sum(1 for f in findings if f["severity"] == "HIGH")
    med_count = sum(1 for f in findings if f["severity"] == "MEDIUM")
    if high_count > 0:
        triage = "HIGH_RISK_SIGNALS"
    elif med_count > 0:
        triage = "NEEDS_REVIEW"
    else:
        triage = "LOW_RISK_SIGNALS"

    return {
        "triage": triage,
        "summary_caveat": (
            "Static offline header/link triage only. Passing headers do not guarantee an email is safe "
            "(compromised accounts pass SPF/DKIM/DMARC), and Authentication-Results is only trustworthy "
            "when added by your own receiving mail server."
        ),
        "headers": {
            "from": from_hdr,
            "from_address": from_addr,
            "from_domain": from_dom,
            "reply_to": reply_to_hdr,
            "reply_to_domain": reply_dom,
            "return_path": return_path_hdr,
            "return_path_domain": return_dom,
            "subject": subject_hdr,
            "date": date_hdr,
            "message_id": message_id_hdr,
            "received_hop_count": len(received_hops),
        },
        "authentication": auth,
        "findings": findings,
        "urls_defanged": url_reports,
    }


def format_plain_report(result: dict[str, Any]) -> str:
    h = result["headers"]
    auth = result["authentication"]
    lines = [
        f"=== EMAIL TRIAGE: {result['triage']} ===",
        f"From:        {h['from'] or '(missing)'}",
        f"Reply-To:    {h['reply_to'] or '(none)'}",
        f"Return-Path: {h['return_path'] or '(none)'}",
        f"Subject:     {h['subject'] or '(none)'}",
        f"Date:        {h['date'] or '(none)'}",
        f"Hops:        {h['received_hop_count']} Received header(s)",
        f"Auth:        SPF={auth['spf']} | DKIM={auth['dkim']} | DMARC={auth['dmarc']}",
        "",
        "Findings:",
    ]
    if result["findings"]:
        for f in result["findings"]:
            lines.append(f"  [{f['severity']}] {f['code']}: {f['detail']}")
    else:
        lines.append("  None - no header/link red flags detected in static check.")

    lines.append("")
    lines.append("Defanged Links:")
    if result["urls_defanged"]:
        for u in result["urls_defanged"]:
            flag_str = f" (flags: {', '.join(u['flags'])})" if u["flags"] else ""
            lines.append(f"  - {u['defanged']}{flag_str}")
    else:
        lines.append("  None.")

    lines.append("")
    lines.append(f"Note: {result['summary_caveat']}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline Email Header & Phishing Triage Analyzer.")
    parser.add_argument("eml_path", type=Path, help="Path to a raw .eml file")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output structured JSON")
    args = parser.parse_args()

    result = analyze_email_bytes(args.eml_path.read_bytes())
    if args.as_json:
        print(json.dumps(result, indent=2))
    else:
        print(format_plain_report(result))


if __name__ == "__main__":
    main()
