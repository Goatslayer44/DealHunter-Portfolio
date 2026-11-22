"""Offline unit tests for Public-Records Domain Security Checkup (synthetic .example fixtures only)."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from domain_security_check import (
    PUBLIC_RECORDS_DISCLAIMER,
    evaluate_public_records,
    format_plain_report,
    validate_domain,
)


ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT / "samples"


class TestDomainSecurityCheck(unittest.TestCase):
    def test_strong_example_domain_passes_baseline(self) -> None:
        snapshot = json.loads((SAMPLES / "sample_strong.example.json").read_text(encoding="utf-8"))
        result = evaluate_public_records(snapshot)
        self.assertEqual(result["overall_status"], "STRONG_PUBLIC_BASELINE")
        self.assertEqual(result["checks"]["spf"]["status"], "PASS")
        self.assertEqual(result["checks"]["dmarc"]["status"], "PASS")
        self.assertEqual(result["checks"]["https"]["status"], "PASS")
        self.assertEqual(result["findings"], [])

    def test_weak_example_domain_flags_missing_spf_dmarc_and_expiring_cert(self) -> None:
        snapshot = json.loads((SAMPLES / "sample_weak.example.json").read_text(encoding="utf-8"))
        result = evaluate_public_records(snapshot)
        self.assertEqual(result["overall_status"], "ACTION_RECOMMENDED")
        codes = {f["code"] for f in result["findings"]}
        self.assertIn("spf_missing", codes)
        self.assertIn("dmarc_missing", codes)
        self.assertIn("tls_cert_expiring_soon", codes)
        self.assertIn("missing_hsts", codes)
        report = format_plain_report(result)
        self.assertIn("No port scanning", report)
        self.assertIn(PUBLIC_RECORDS_DISCLAIMER, report)

    def test_duplicate_spf_and_monitor_only_dmarc_flagged(self) -> None:
        snapshot = {
            "domain": "shop.example.org",
            "spf_txt_records": [
                "v=spf1 include:_spf.example.org ~all",
                "v=spf1 include:mail.example.net -all",
            ],
            "dmarc_txt_records": ["v=DMARC1; p=none; rua=mailto:dmarc@shop.example.org"],
            "https": {
                "reachable": True,
                "cert_days_remaining": 60,
                "headers": {
                    "Strict-Transport-Security": "max-age=31536000",
                    "X-Content-Type-Options": "nosniff",
                },
            },
        }
        result = evaluate_public_records(snapshot)
        codes = {f["code"] for f in result["findings"]}
        self.assertEqual(result["overall_status"], "ACTION_RECOMMENDED")
        self.assertIn("spf_multiple_records", codes)
        self.assertIn("dmarc_monitor_only", codes)

    def test_permissive_plus_all_spf_flagged_high(self) -> None:
        snapshot = {
            "domain": "open.example.com",
            "spf_txt_records": ["v=spf1 +all"],
            "dmarc_txt_records": ["v=DMARC1; p=reject"],
            "https": {"reachable": True, "cert_days_remaining": 90, "headers": {}},
        }
        result = evaluate_public_records(snapshot)
        self.assertEqual(result["checks"]["spf"]["status"], "OVERLY_PERMISSIVE")
        self.assertIn("spf_plus_all", {f["code"] for f in result["findings"]})

    def test_missing_lookup_data_stays_unknown_never_pass(self) -> None:
        snapshot = {"domain": "unknown.example.net"}
        result = evaluate_public_records(snapshot)
        self.assertEqual(result["overall_status"], "NEEDS_REVIEW")
        self.assertEqual(result["checks"]["spf"]["status"], "UNKNOWN")
        self.assertEqual(result["checks"]["dmarc"]["status"], "UNKNOWN")
        self.assertEqual(result["checks"]["https"]["status"], "UNKNOWN")

    def test_invalid_and_injection_domains_are_rejected(self) -> None:
        for bad in ("", "not_a_domain", "198.51.100.1", "https://shop.example.com", "shop.example.com; calc.exe"):
            with self.assertRaises(ValueError):
                validate_domain(bad)

    def test_cli_offline_json_and_plain_text(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "domain_security_check.py"), "--input", str(SAMPLES / "sample_weak.example.json"), "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        parsed = json.loads(proc.stdout)
        self.assertEqual(parsed["overall_status"], "ACTION_RECOMMENDED")
        self.assertIn("No port scanning", parsed["disclaimer"])


if __name__ == "__main__":
    unittest.main()
