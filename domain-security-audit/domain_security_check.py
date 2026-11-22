"""Public Email & Website Check (v1.1) — Public-records checkup tool.

Checks ONLY public DNS TXT records (SPF, DMARC via RFC 9989 DNS Tree Walk) and
a standard HTTPS/TLS connection (hostname, check time, certificate validation,
and redirect destination if any). Performs NO port scanning, NO vulnerability
probing, and NO access to internal systems.

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

REPORT_TITLE = "Public Email & Website Check"

PUBLIC_RECORDS_DISCLAIMER = (
    "Public-records check only (public DNS TXT records + standard HTTPS connection). "
    "No port scanning, no vulnerability probing, and no access to internal systems."
)

CUSTOMER_FOOTER = (
    "This check is free. If you'd like help with a finding, 205 Digital Help can "
    "confirm it with your provider, give you a written price before any change, "
    "and show you how we checked the result."
)


def validate_domain(raw: str) -> str:
    if not isinstance(raw, str):
        raise ValueError("Domain must be a string.")
    cleaned = raw.strip().lower().rstrip(".")
    if not cleaned or not DOMAIN_RE.match(cleaned):
        raise ValueError(f"Invalid domain name: {raw!r}")
    return cleaned


def rfc9989_tree_walk_domains(domain: str) -> list[str]:
    """Return ordered DNS Tree Walk domains per RFC 9989 (DMARCbis).

    Always checks the exact domain first, then walks upward label by label
    toward the organizational domain (stopping before the single-label TLD).
    Per RFC 9989 Section 5.8, if the domain has more than 5 labels, after
    checking the exact domain the walk jumps to the 5-label suffix and walks
    down to 2 labels.
    """
    clean = validate_domain(domain)
    labels = clean.split(".")
    targets: list[str] = [clean]
    if len(labels) <= 2:
        return targets

    start_idx = max(1, len(labels) - 5)
    for idx in range(start_idx, len(labels) - 1):
        candidate = ".".join(labels[idx:])
        if candidate not in targets:
            targets.append(candidate)
    return targets


def _parse_dmarc_tags(record: str) -> dict[str, str]:
    tags: dict[str, str] = {}
    for part in record.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            tags[k.strip().lower()] = v.strip()
    return tags


def _resolve_dmarc_tree_walk(domain: str, snapshot: dict[str, Any]) -> dict[str, Any]:
    """Evaluate DMARC across the full RFC 9989 DNS Tree Walk."""
    expected_walk = rfc9989_tree_walk_domains(domain)

    # Support explicit dmarc_tree_walk list or legacy single-node dmarc_txt_records
    raw_walk = snapshot.get("dmarc_tree_walk")
    walk_by_domain: dict[str, dict[str, Any]] = {}
    if isinstance(raw_walk, list):
        for step in raw_walk:
            if isinstance(step, dict) and isinstance(step.get("query_domain"), str):
                qdom = validate_domain(step["query_domain"])
                walk_by_domain[qdom] = step
    elif "dmarc_txt_records" in snapshot:
        txts = snapshot.get("dmarc_txt_records")
        walk_by_domain[domain] = {
            "query_domain": domain,
            "status": "ok" if isinstance(txts, list) else "error",
            "txt_records": txts if isinstance(txts, list) else None,
        }

    queried_path: list[str] = []
    for qdom in expected_walk:
        queried_path.append(qdom)
        step = walk_by_domain.get(qdom)
        if not isinstance(step, dict):
            return {
                "email_domain_checked": domain,
                "policy_domain_found": None,
                "inherited": False,
                "walk_path": queried_path,
                "walk_complete": False,
                "status": "UNVERIFIED",
                "reason": f"DMARC tree walk incomplete: no lookup result for _dmarc.{qdom}.",
                "record": None,
                "policy": None,
                "subdomain_policy": None,
            }

        step_status = str(step.get("status", "ok")).strip().lower()
        txts = step.get("txt_records")
        if step_status in {"timeout", "error", "unknown"} or txts is None:
            return {
                "email_domain_checked": domain,
                "policy_domain_found": None,
                "inherited": False,
                "walk_path": queried_path,
                "walk_complete": False,
                "status": "UNVERIFIED",
                "reason": f"DMARC lookup at _dmarc.{qdom} returned '{step_status}'.",
                "record": None,
                "policy": None,
                "subdomain_policy": None,
            }

        matches = [r.strip() for r in txts if isinstance(r, str) and r.strip().lower().startswith("v=dmarc1")]
        if len(matches) > 1:
            return {
                "email_domain_checked": domain,
                "policy_domain_found": qdom,
                "inherited": qdom != domain,
                "walk_path": queried_path,
                "walk_complete": True,
                "status": "INVALID_MULTIPLE",
                "reason": f"Found {len(matches)} v=DMARC1 records at _dmarc.{qdom}.",
                "record": " | ".join(matches),
                "policy": None,
                "subdomain_policy": None,
            }
        if len(matches) == 1:
            rec = matches[0]
            tags = _parse_dmarc_tags(rec)
            p_val = tags.get("p", "").lower() or None
            sp_val = tags.get("sp", "").lower() or None
            inherited = qdom != domain
            effective_policy = (sp_val if (inherited and sp_val) else p_val)
            if effective_policy in {"quarantine", "reject"}:
                status = "RECORD_FOUND"
            elif effective_policy == "none":
                status = "PUBLISHED_MONITORING_POLICY"
            else:
                status = "INVALID_POLICY"
            return {
                "email_domain_checked": domain,
                "policy_domain_found": qdom,
                "inherited": inherited,
                "walk_path": queried_path,
                "walk_complete": True,
                "status": status,
                "reason": (
                    f"DMARC record found at _dmarc.{qdom} (inherited for {domain})."
                    if inherited
                    else f"DMARC record found at _dmarc.{qdom}."
                ),
                "record": rec,
                "policy": p_val,
                "subdomain_policy": sp_val,
                "effective_policy": effective_policy,
            }

    return {
        "email_domain_checked": domain,
        "policy_domain_found": None,
        "inherited": False,
        "walk_path": queried_path,
        "walk_complete": True,
        "status": "MISSING",
        "reason": f"Completed RFC 9989 DNS tree walk ({' -> '.join(queried_path)}) with no v=DMARC1 record found.",
        "record": None,
        "policy": None,
        "subdomain_policy": None,
    }


def evaluate_public_records(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a public-records snapshot (SPF TXT, RFC 9989 DMARC tree walk, narrow HTTPS)."""
    domain = validate_domain(snapshot.get("domain", ""))
    fictional = bool(snapshot.get("fictional", False))
    checked_utc = snapshot.get("checked_utc") or snapshot.get("collected_utc") or "UNVERIFIED"
    checked_date = snapshot.get("checked_date")
    if not checked_date:
        checked_date = str(checked_utc)[:10] if isinstance(checked_utc, str) and len(checked_utc) >= 10 and checked_utc != "UNVERIFIED" else "UNVERIFIED"

    spf_txts = snapshot.get("spf_txt_records")
    spf_query_status = str(snapshot.get("spf_query_status", "ok" if isinstance(spf_txts, list) else "unknown")).strip().lower()
    https_info = snapshot.get("https")

    findings: list[dict[str, str]] = []

    def add_finding(severity: str, category: str, code: str, title: str, detail: str, fix: str) -> None:
        findings.append(
            {
                "severity": severity,
                "category": category,
                "code": code,
                "title": title,
                "detail": detail,
                "suggested_next_step": fix,
            }
        )

    # --- 1. SPF evaluation (record presence + syntax only; sending path is ALWAYS UNVERIFIED) ---
    spf_status = "UNVERIFIED"
    spf_record = None
    if spf_query_status in {"timeout", "error", "unknown"} or spf_txts is None:
        spf_status = "UNVERIFIED"
        add_finding(
            "UNVERIFIED",
            "SPF",
            "spf_lookup_unverified",
            "SPF lookup did not complete (UNVERIFIED)",
            f"On {checked_date}, the public DNS TXT lookup for {domain} returned '{spf_query_status}'. We cannot state whether an SPF record exists.",
            f"Re-run the public DNS lookup for {domain} later or confirm the TXT records directly in your DNS provider.",
        )
    else:
        spf_matches = [r.strip() for r in spf_txts if isinstance(r, str) and r.strip().lower().startswith("v=spf1")]
        if len(spf_matches) == 0:
            spf_status = "MISSING"
            add_finding(
                "FINDING",
                "SPF",
                "spf_missing",
                f"No SPF record found at {domain}",
                f"On {checked_date}, we found no SPF record at {domain}. We haven't confirmed which domain your invoice service uses to send mail.",
                f"Confirm which domain your email and invoice services send from, then publish one v=spf1 TXT record listing only authorized senders.",
            )
        elif len(spf_matches) > 1:
            spf_status = "INVALID_MULTIPLE"
            spf_record = " | ".join(spf_matches)
            add_finding(
                "FINDING",
                "SPF",
                "spf_multiple_records",
                f"Multiple SPF records found at {domain} (RFC 7208 syntax error)",
                f"On {checked_date}, we found {len(spf_matches)} v=spf1 TXT records at {domain}. RFC 7208 allows only one SPF record per domain.",
                "Combine all authorized senders into a single v=spf1 TXT record with your DNS provider.",
            )
        else:
            spf_record = spf_matches[0]
            tokens = spf_record.lower().split()
            if "+all" in tokens or "all" in tokens:
                spf_status = "RECORD_FOUND_SYNTAX_ISSUE"
                add_finding(
                    "FINDING",
                    "SPF",
                    "spf_plus_all",
                    f"SPF record at {domain} ends with +all",
                    f"On {checked_date}, the SPF record at {domain} ('{spf_record}') includes '+all', which authorizes any IP address.",
                    "Confirm all legitimate sending services with your provider before tightening '+all' to '~all' or '-all'.",
                )
            elif "?all" in tokens:
                spf_status = "RECORD_FOUND_SYNTAX_ISSUE"
                add_finding(
                    "FINDING",
                    "SPF",
                    "spf_neutral",
                    f"SPF record at {domain} ends with neutral policy (?all)",
                    f"On {checked_date}, the SPF record at {domain} uses '?all' (neutral).",
                    "Confirm authorized senders with your provider before tightening to '~all' or '-all'.",
                )
            elif "-all" in tokens or "~all" in tokens:
                spf_status = "RECORD_FOUND"
            else:
                spf_status = "RECORD_FOUND_SYNTAX_ISSUE"
                add_finding(
                    "FINDING",
                    "SPF",
                    "spf_no_all_mechanism",
                    f"SPF record at {domain} has no explicit ~all or -all qualifier",
                    f"On {checked_date}, the SPF record at {domain} ('{spf_record}') did not include a standard '~all' or '-all' ending.",
                    "Confirm intended senders with your provider and add an explicit qualifier.",
                )

    # --- 2. DMARC evaluation (RFC 9989 complete DNS Tree Walk; sending path ALWAYS UNVERIFIED) ---
    dmarc_info = _resolve_dmarc_tree_walk(domain, snapshot)
    dmarc_status = dmarc_info["status"]
    if dmarc_status == "UNVERIFIED":
        add_finding(
            "UNVERIFIED",
            "DMARC",
            "dmarc_walk_unverified",
            f"DMARC tree walk incomplete for {domain} (UNVERIFIED)",
            f"On {checked_date}, the RFC 9989 DMARC tree walk for {domain} did not complete ({dmarc_info['reason']}). Status is UNVERIFIED, not missing.",
            f"Re-run the DMARC tree walk for {domain} or check _dmarc records directly in your DNS provider.",
        )
    elif dmarc_status == "MISSING":
        add_finding(
            "FINDING",
            "DMARC",
            "dmarc_missing",
            f"No DMARC policy found for {domain}",
            f"On {checked_date}, we completed the RFC 9989 tree walk for {domain} ({' -> '.join(dmarc_info['walk_path'])}) and found no v=DMARC1 record. We haven't confirmed which domain your invoice service uses to send mail.",
            "Confirm your sending domains with your provider, then publish a starting monitoring DMARC record (v=DMARC1; p=none; rua=mailto:...).",
        )
    elif dmarc_status == "INVALID_MULTIPLE":
        add_finding(
            "FINDING",
            "DMARC",
            "dmarc_multiple_records",
            f"Multiple DMARC records found at _dmarc.{dmarc_info['policy_domain_found']}",
            f"On {checked_date}, {dmarc_info['reason']}",
            "Keep exactly one v=DMARC1 TXT record at that DNS name.",
        )
    elif dmarc_status == "INVALID_POLICY":
        add_finding(
            "FINDING",
            "DMARC",
            "dmarc_invalid_policy",
            f"DMARC record at _dmarc.{dmarc_info['policy_domain_found']} has missing or invalid policy tag",
            f"On {checked_date}, the DMARC record found at _dmarc.{dmarc_info['policy_domain_found']} ('{dmarc_info['record']}') lacked a valid p= tag.",
            "Confirm and publish a valid p=none, p=quarantine, or p=reject policy with your provider.",
        )
    elif dmarc_status == "PUBLISHED_MONITORING_POLICY":
        where = (
            f"inherited from _dmarc.{dmarc_info['policy_domain_found']}"
            if dmarc_info["inherited"]
            else f"at _dmarc.{dmarc_info['policy_domain_found']}"
        )
        add_finding(
            "INFO",
            "DMARC",
            "dmarc_published_monitoring_policy",
            f"Published monitoring DMARC policy (p=none) {where}",
            f"On {checked_date}, we found a published monitoring DMARC policy ({dmarc_info['record']}) {where} for email domain {domain}. It is present (not missing) and set to monitoring only.",
            "Review DMARC aggregate reports with your provider before considering p=quarantine or p=reject.",
        )
    elif dmarc_status == "RECORD_FOUND" and dmarc_info["inherited"]:
        add_finding(
            "INFO",
            "DMARC",
            "dmarc_inherited_policy",
            f"Inherited DMARC policy found at _dmarc.{dmarc_info['policy_domain_found']}",
            f"On {checked_date}, no DMARC record was published directly at _dmarc.{domain}; RFC 9989 tree walk found an applicable policy at _dmarc.{dmarc_info['policy_domain_found']} ({dmarc_info['record']}). Sending-path evaluation remains UNVERIFIED.",
            "Confirm whether this subdomain is intended to inherit the organizational domain policy.",
        )

    # --- 3. Narrow HTTPS evaluation (hostname, time, cert validation, redirect named separately) ---
    https_hostname = domain
    https_time = checked_utc
    https_cert_status = "UNVERIFIED"
    https_days: int | None = None
    redirect_dest: str | None = None

    if not isinstance(https_info, dict):
        add_finding(
            "UNVERIFIED",
            "HTTPS",
            "https_unverified",
            f"HTTPS check not completed for {domain} (UNVERIFIED)",
            f"On {checked_date}, no standard HTTPS connection result was recorded for {domain}.",
            f"Verify https://{domain} directly in a browser.",
        )
    else:
        https_hostname = str(https_info.get("hostname") or domain).strip().lower()
        https_time = str(https_info.get("checked_utc") or checked_utc)
        reachable = https_info.get("reachable")
        cert_valid = https_info.get("cert_valid")
        https_days = https_info.get("cert_days_remaining")
        redirect_dest = https_info.get("redirect_destination") or None

        if reachable is False or cert_valid is False:
            https_cert_status = "FAILED"
            err = https_info.get("error", "certificate validation or HTTPS connection failed")
            add_finding(
                "FINDING",
                "HTTPS",
                "https_cert_failed",
                f"HTTPS / certificate validation failed for {https_hostname}",
                f"Checked {https_hostname} at {https_time}: {err}.",
                "Confirm the SSL/TLS certificate and hosting setup with your website provider.",
            )
        elif reachable is True:
            if isinstance(https_days, (int, float)) and https_days < 0:
                https_cert_status = "EXPIRED"
                add_finding(
                    "FINDING",
                    "HTTPS",
                    "tls_cert_expired",
                    f"HTTPS certificate expired for {https_hostname}",
                    f"Checked {https_hostname} at {https_time}: certificate expired {abs(int(https_days))} day(s) ago.",
                    "Renew the TLS certificate and confirm automatic renewal with your host.",
                )
            elif isinstance(https_days, (int, float)) and https_days < 14:
                https_cert_status = "EXPIRING_SOON"
                add_finding(
                    "FINDING",
                    "HTTPS",
                    "tls_cert_expiring_soon",
                    f"HTTPS certificate for {https_hostname} expires in under 14 days",
                    f"Checked {https_hostname} at {https_time}: certificate valid with {int(https_days)} day(s) remaining.",
                    "Confirm automatic certificate renewal is active with your website host.",
                )
            elif isinstance(https_days, (int, float)) and https_days < 30:
                https_cert_status = "EXPIRING_30D"
                add_finding(
                    "INFO",
                    "HTTPS",
                    "tls_cert_expiring_30d",
                    f"HTTPS certificate for {https_hostname} expires in under 30 days",
                    f"Checked {https_hostname} at {https_time}: certificate valid with {int(https_days)} day(s) remaining.",
                    "Verify automatic certificate renewal with your website host.",
                )
            else:
                https_cert_status = "VALID"
                add_finding(
                    "OK",
                    "HTTPS",
                    "https_cert_valid",
                    f"Valid HTTPS certificate at {https_hostname}",
                    (
                        f"Checked {https_hostname} at {https_time}: TLS certificate validated"
                        + (f" ({int(https_days)} day(s) remaining)." if isinstance(https_days, (int, float)) else ".")
                        + (f" Redirect destination observed: {redirect_dest}." if redirect_dest else "")
                    ),
                    "No immediate certificate action needed based on this check.",
                )
        else:
            https_cert_status = "UNVERIFIED"
            add_finding(
                "UNVERIFIED",
                "HTTPS",
                "https_unverified",
                f"HTTPS check status unknown for {https_hostname} (UNVERIFIED)",
                f"Checked {https_hostname} at {https_time}: reachability was not confirmed.",
                f"Verify https://{https_hostname} directly.",
            )

    actionable_findings = [f for f in findings if f["severity"] == "FINDING"]
    unverified_findings = [f for f in findings if f["severity"] == "UNVERIFIED"]
    if actionable_findings:
        overall = "Findings to review"
    elif unverified_findings:
        overall = "Needs review (some checks UNVERIFIED)"
    else:
        overall = "No issues found in what we checked"

    return {
        "title": REPORT_TITLE,
        "fictional": fictional,
        "domain_checked": domain,
        "checked_date": checked_date,
        "checked_utc": checked_utc,
        "overall_status": overall,
        "sending_path_status": "UNVERIFIED",
        "sending_domain_caveat": (
            f"The domain a business's invoices or emails actually send from may differ from {domain} "
            "and has not been confirmed."
        ),
        "disclaimer": PUBLIC_RECORDS_DISCLAIMER,
        "checks": {
            "spf": {
                "status": spf_status,
                "sending_path": "UNVERIFIED",
                "record": spf_record,
            },
            "dmarc": {
                "email_domain_checked": dmarc_info["email_domain_checked"],
                "policy_domain_found": dmarc_info["policy_domain_found"],
                "inherited": dmarc_info["inherited"],
                "walk_path": dmarc_info["walk_path"],
                "walk_complete": dmarc_info["walk_complete"],
                "status": dmarc_status,
                "sending_path": "UNVERIFIED",
                "record": dmarc_info["record"],
            },
            "https": {
                "hostname": https_hostname,
                "checked_utc": https_time,
                "cert_validation": https_cert_status,
                "cert_days_remaining": https_days,
                "redirect_destination": redirect_dest,
            },
        },
        "findings": findings,
        "footer": CUSTOMER_FOOTER,
    }


def _query_dns_txt(name: str, timeout_sec: float = 10.0) -> tuple[str, list[str] | None]:
    """Read public DNS TXT records via nslookup (shell=False, validated name only)."""
    try:
        proc = subprocess.run(
            ["nslookup", "-type=txt", name],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return ("timeout", None)
    except Exception:
        return ("error", None)
    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    if "timed out" in combined.lower() or "timeout" in combined.lower():
        return ("timeout", None)
    if proc.returncode != 0 and not proc.stdout:
        return ("error", None)
    records = [match for match in re.findall(r'"([^"]+)"', proc.stdout or "")]
    return ("ok", records)


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


def _check_https_live(domain: str, timeout_sec: float = 10.0) -> dict[str, Any]:
    """Perform a single standard HTTPS connection + cert check and record any redirect separately."""
    now_utc = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    info: dict[str, Any] = {
        "hostname": domain,
        "checked_utc": now_utc,
        "reachable": False,
        "cert_valid": False,
        "cert_days_remaining": None,
        "redirect_destination": None,
    }
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((domain, 443), timeout=timeout_sec) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                info["cert_valid"] = True
                not_after = cert.get("notAfter") if cert else None
                if not_after:
                    exp_dt = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
                    info["cert_days_remaining"] = int((exp_dt - datetime.now(timezone.utc)).days)
        opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ctx),
            _NoRedirectHandler(),
        )
        req = urllib.request.Request(
            f"https://{domain}/",
            method="HEAD",
            headers={"User-Agent": "205-Public-Email-Website-Check/1.1"},
        )
        try:
            with opener.open(req, timeout=timeout_sec):
                info["reachable"] = True
        except urllib.error.HTTPError as exc:
            info["reachable"] = True
            if exc.code in {301, 302, 303, 307, 308} and exc.headers:
                info["redirect_destination"] = exc.headers.get("Location")
    except Exception as exc:
        info["error"] = f"{type(exc).__name__}: {exc}"
    return info


def collect_live_public_records(domain: str) -> dict[str, Any]:
    clean = validate_domain(domain)
    now_utc = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    spf_status, spf_records = _query_dns_txt(clean)

    dmarc_walk: list[dict[str, Any]] = []
    for qdom in rfc9989_tree_walk_domains(clean):
        qstatus, qrecords = _query_dns_txt(f"_dmarc.{qdom}")
        dmarc_walk.append({"query_domain": qdom, "status": qstatus, "txt_records": qrecords})
        if qstatus != "ok":
            break
        if qrecords and any(r.strip().lower().startswith("v=dmarc1") for r in qrecords):
            break

    return {
        "fictional": False,
        "domain": clean,
        "checked_date": now_utc[:10],
        "checked_utc": now_utc,
        "spf_query_status": spf_status,
        "spf_txt_records": spf_records,
        "dmarc_tree_walk": dmarc_walk,
        "https": _check_https_live(clean),
    }


def format_plain_report(result: dict[str, Any]) -> str:
    c = result["checks"]
    spf = c["spf"]
    dmarc = c["dmarc"]
    https = c["https"]

    lines = [f"=== {result['title']} ==="]
    if result.get("fictional"):
        lines.append("[FICTIONAL SAMPLE - NOT A REAL BUSINESS]")
    lines.extend(
        [
            f"Domain checked: {result['domain_checked']}",
            f"Checked date:   {result['checked_date']} (UTC: {result['checked_utc']})",
            f"Overall status: {result['overall_status']}",
            f"Sending path:   {result['sending_path_status']} (public DNS records alone do not verify live sending paths)",
            f"Scope:          {result['disclaimer']}",
            f"Notice:         {result['sending_domain_caveat']}",
            "",
            "Check Summary:",
            f"  1. SPF ({result['domain_checked']}): {spf['status']} | Sending path: {spf['sending_path']}"
            + (f" | Record: {spf['record']}" if spf["record"] else ""),
            f"  2. DMARC (RFC 9989 tree walk): {dmarc['status']} | Sending path: {dmarc['sending_path']}",
            f"     - Email domain checked: {dmarc['email_domain_checked']}",
            f"     - Policy domain found:  {dmarc['policy_domain_found'] or 'None'}",
            f"     - Walk path:            {' -> '.join(dmarc['walk_path'])}",
            f"  3. HTTPS ({https['hostname']}): {https['cert_validation']} (checked {https['checked_utc']})"
            + (
                f" | Cert days remaining: {https['cert_days_remaining']}"
                if https["cert_days_remaining"] is not None
                else ""
            ),
        ]
    )
    if https.get("redirect_destination"):
        lines.append(f"     - Redirect destination: {https['redirect_destination']}")

    lines.append("")
    lines.append("Findings:")
    for f in result["findings"]:
        lines.append(f"  [{f['severity']} | {f['category']}] {f['title']} ({f['code']})")
        lines.append(f"      Observed:  {f['detail']}")
        lines.append(f"      Next step: {f['suggested_next_step']}")

    lines.append("")
    lines.append(result["footer"])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Public Email & Website Check (v1.1) — offline by default."
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
