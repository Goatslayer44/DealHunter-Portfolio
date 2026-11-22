"""Offline unit tests for Public Email & Website Check v1.1 (fictional .example fixtures only)."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from domain_security_check import (
    CUSTOMER_FOOTER,
    PUBLIC_RECORDS_DISCLAIMER,
    REPORT_TITLE,
    evaluate_public_records,
    format_plain_report,
    rfc9989_tree_walk_domains,
    validate_domain,
)


ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT / "samples"


class TestDomainSecurityCheckV11(unittest.TestCase):
    def test_strong_fictional_domain_uses_record_found_not_pass_and_plain_overall_status(self) -> None:
        snapshot = json.loads((SAMPLES / "sample_strong.example.json").read_text(encoding="utf-8"))
        result = evaluate_public_records(snapshot)
        self.assertEqual(result["overall_status"], "No issues found in what we checked")
        self.assertEqual(result["checks"]["spf"]["status"], "RECORD_FOUND")
        self.assertEqual(result["checks"]["dmarc"]["status"], "RECORD_FOUND")
        self.assertEqual(result["sending_path_status"], "UNVERIFIED")
        self.assertEqual(result["checks"]["spf"]["sending_path"], "UNVERIFIED")
        self.assertEqual(result["checks"]["dmarc"]["sending_path"], "UNVERIFIED")
        self.assertEqual(result["checks"]["https"]["cert_validation"], "VALID")

        report = format_plain_report(result)
        self.assertIn(REPORT_TITLE, report)
        self.assertIn("FICTIONAL SAMPLE", report)
        self.assertIn(CUSTOMER_FOOTER, report)
        self.assertIn("may differ from localshop.example.com and has not been confirmed", report)
        self.assertNotIn("STRONG_PUBLIC_BASELINE", report)

    def test_weak_fictional_domain_uses_defensible_wording_and_names_redirect_separately(self) -> None:
        snapshot = json.loads((SAMPLES / "sample_weak.example.json").read_text(encoding="utf-8"))
        result = evaluate_public_records(snapshot)
        self.assertEqual(result["overall_status"], "Findings to review")
        codes = {f["code"] for f in result["findings"]}
        self.assertIn("spf_missing", codes)
        self.assertIn("dmarc_missing", codes)
        self.assertIn("tls_cert_expiring_soon", codes)
        self.assertEqual(result["checks"]["https"]["redirect_destination"], "https://www.needshelp.example.org/")

        report = format_plain_report(result)
        self.assertIn("On 2026-11-22, we found no SPF record at needshelp.example.org. We haven't confirmed which domain your invoice service uses to send mail.", report)
        self.assertIn("Redirect destination: https://www.needshelp.example.org/", report)
        self.assertNotIn("hit spam", report.lower())
        self.assertNotIn("scammers", report.lower())
        self.assertIn(PUBLIC_RECORDS_DISCLAIMER, report)
        self.assertIn(CUSTOMER_FOOTER, report)

    def test_fictional_shop_acceptance_fixture_three_distinct_findings(self) -> None:
        """Acceptance fixture: inherited DMARC via RFC 9989 tree walk + SPF timeout -> UNVERIFIED + valid HTTPS."""
        snapshot = json.loads((SAMPLES / "sample_fictional_shop.example.json").read_text(encoding="utf-8"))
        result = evaluate_public_records(snapshot)
        self.assertTrue(result["fictional"])
        self.assertEqual(result["overall_status"], "Needs review (some checks UNVERIFIED)")

        # 1. SPF timed out -> UNVERIFIED (never MISSING)
        self.assertEqual(result["checks"]["spf"]["status"], "UNVERIFIED")
        # 2. DMARC inherited via complete RFC 9989 tree walk (2 levels up)
        dmarc = result["checks"]["dmarc"]
        self.assertEqual(dmarc["email_domain_checked"], "mail.billing.shop.example")
        self.assertEqual(dmarc["policy_domain_found"], "shop.example")
        self.assertTrue(dmarc["inherited"])
        self.assertEqual(dmarc["walk_path"], ["mail.billing.shop.example", "billing.shop.example", "shop.example"])
        self.assertEqual(dmarc["status"], "RECORD_FOUND")
        # 3. Valid HTTPS
        self.assertEqual(result["checks"]["https"]["cert_validation"], "VALID")
        self.assertEqual(result["checks"]["https"]["hostname"], "mail.billing.shop.example")

        # Exactly 3 distinct findings across SPF, DMARC, HTTPS
        self.assertEqual(len(result["findings"]), 3)
        self.assertEqual({f["category"] for f in result["findings"]}, {"SPF", "DMARC", "HTTPS"})
        self.assertEqual({f["code"] for f in result["findings"]}, {"spf_lookup_unverified", "dmarc_inherited_policy", "https_cert_valid"})

        report = format_plain_report(result)
        self.assertIn("FICTIONAL SAMPLE", report)
        self.assertIn("Email domain checked: mail.billing.shop.example", report)
        self.assertIn("Policy domain found:  shop.example", report)
        self.assertIn(CUSTOMER_FOOTER, report)

    def test_rfc9989_tree_walk_order_and_five_label_cap(self) -> None:
        self.assertEqual(
            rfc9989_tree_walk_domains("a.b.shop.example"),
            ["a.b.shop.example", "b.shop.example", "shop.example"],
        )
        # 7-label domain jumps to 5-label suffix per RFC 9989 Section 5.8
        self.assertEqual(
            rfc9989_tree_walk_domains("x.y.a.b.c.shop.example"),
            ["x.y.a.b.c.shop.example", "a.b.c.shop.example", "b.c.shop.example", "c.shop.example", "shop.example"],
        )

    def test_incomplete_dmarc_walk_or_timeout_is_unverified_never_missing(self) -> None:
        snapshot = {
            "domain": "sub.shop.example",
            "checked_date": "2026-11-22",
            "spf_query_status": "ok",
            "spf_txt_records": ["v=spf1 include:_spf.example -all"],
            "dmarc_tree_walk": [
                {"query_domain": "sub.shop.example", "status": "ok", "txt_records": []},
                {"query_domain": "shop.example", "status": "timeout", "txt_records": None},
            ],
            "https": {"hostname": "sub.shop.example", "checked_utc": "2026-11-22T18:00:00Z", "reachable": True, "cert_valid": True, "cert_days_remaining": 45},
        }
        result = evaluate_public_records(snapshot)
        self.assertEqual(result["checks"]["dmarc"]["status"], "UNVERIFIED")
        self.assertFalse(result["checks"]["dmarc"]["walk_complete"])
        self.assertIn("dmarc_walk_unverified", {f["code"] for f in result["findings"]})

    def test_duplicate_spf_plus_all_and_published_monitoring_dmarc(self) -> None:
        snapshot = {
            "domain": "shop.example.org",
            "checked_date": "2026-11-22",
            "spf_query_status": "ok",
            "spf_txt_records": [
                "v=spf1 include:_spf.example.org ~all",
                "v=spf1 include:mail.example.net -all",
            ],
            "dmarc_tree_walk": [
                {"query_domain": "shop.example.org", "status": "ok", "txt_records": ["v=DMARC1; p=none; rua=mailto:dmarc@shop.example.org"]}
            ],
            "https": {"hostname": "shop.example.org", "checked_utc": "2026-11-22T18:00:00Z", "reachable": True, "cert_valid": True, "cert_days_remaining": 60},
        }
        result = evaluate_public_records(snapshot)
        self.assertEqual(result["checks"]["spf"]["status"], "INVALID_MULTIPLE")
        self.assertEqual(result["checks"]["dmarc"]["status"], "PUBLISHED_MONITORING_POLICY")
        codes = {f["code"] for f in result["findings"]}
        self.assertIn("spf_multiple_records", codes)
        self.assertIn("dmarc_published_monitoring_policy", codes)

    def test_permissive_plus_all_spf_flagged(self) -> None:
        snapshot = {
            "domain": "open.example.com",
            "checked_date": "2026-11-22",
            "spf_query_status": "ok",
            "spf_txt_records": ["v=spf1 +all"],
            "dmarc_tree_walk": [{"query_domain": "open.example.com", "status": "ok", "txt_records": ["v=DMARC1; p=reject"]}],
            "https": {"hostname": "open.example.com", "checked_utc": "2026-11-22T18:00:00Z", "reachable": True, "cert_valid": True, "cert_days_remaining": 90},
        }
        result = evaluate_public_records(snapshot)
        self.assertEqual(result["checks"]["spf"]["status"], "RECORD_FOUND_SYNTAX_ISSUE")
        self.assertIn("spf_plus_all", {f["code"] for f in result["findings"]})

    def test_invalid_and_injection_domains_are_rejected(self) -> None:
        for bad in ("", "not_a_domain", "198.51.100.1", "https://shop.example.com", "shop.example.com; calc.exe"):
            with self.assertRaises(ValueError):
                validate_domain(bad)

    def test_cli_offline_json_and_text_on_fictional_shop(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "domain_security_check.py"), "--input", str(SAMPLES / "sample_fictional_shop.example.json"), "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        parsed = json.loads(proc.stdout)
        self.assertEqual(parsed["title"], REPORT_TITLE)
        self.assertEqual(parsed["footer"], CUSTOMER_FOOTER)
        self.assertEqual(parsed["checks"]["dmarc"]["policy_domain_found"], "shop.example")


if __name__ == "__main__":
    unittest.main()
