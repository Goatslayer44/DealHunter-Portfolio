import os
import tempfile
import unittest
from pathlib import Path

from security_log_analyzer import analyzer

SAMPLE = Path(__file__).parent / "sample_auth.log"


def failed(second, user, ip):
    return f"2026-10-01 09:00:{second:02d} FAILED user={user} ip={ip}"


class TestParsing(unittest.TestCase):

    def test_valid_failed_line(self):
        event = analyzer.parse_line("2026-10-01 08:00:05 FAILED user=alice ip=192.0.2.10")
        self.assertFalse(event.success)
        self.assertEqual((event.user, event.ip), ("alice", "192.0.2.10"))

    def test_valid_success_line(self):
        event = analyzer.parse_line("2026-10-01 08:00:05 SUCCESS user=alice ip=192.0.2.10")
        self.assertTrue(event.success)

    def test_malformed_lines_return_none(self):
        bad_lines = [
            "",
            "random text",
            "2026-13-45 99:99:99 FAILED user=eve ip=192.0.2.13",   # impossible date
            "2026-10-01 12:00:00 FAILED user=eve ip=999.1.1.1",    # invalid IP
            "2026-10-01 12:00:00 MAYBE user=eve ip=192.0.2.13",    # unknown status
            "2026-10-01 12:00:00 FAILED user=bad;name ip=192.0.2.1",
            "2026-10-01 12:00:00 FAILED user=" + "a" * 600 + " ip=192.0.2.1",
        ]
        for line in bad_lines:
            self.assertIsNone(analyzer.parse_line(line), line)

    def test_parse_lines_counts_malformed_and_ignores_blank(self):
        events, malformed = analyzer.parse_lines(
            [failed(1, "a", "192.0.2.1"), "garbage", "", "   "]
        )
        self.assertEqual(len(events), 1)
        self.assertEqual(malformed, 1)


class TestAnalysis(unittest.TestCase):

    def run_lines(self, lines, threshold=5):
        events, _ = analyzer.parse_lines(lines)
        return analyzer.analyze(events, threshold)

    def test_normal_activity_has_no_findings(self):
        findings = self.run_lines([
            "2026-10-01 08:00:00 SUCCESS user=alice ip=192.0.2.10",
            failed(1, "bob", "192.0.2.11"),
            "2026-10-01 09:00:05 SUCCESS user=bob ip=192.0.2.11",
        ])
        self.assertEqual(findings["suspicious_ips"], {})
        self.assertEqual(findings["targeted_users"], {})
        self.assertEqual(findings["success_after_failures"], [])

    def test_repeated_failures_flag_ip_and_user(self):
        findings = self.run_lines([failed(i, "admin", "203.0.113.50") for i in range(5)])
        self.assertEqual(findings["suspicious_ips"], {"203.0.113.50": 5})
        self.assertEqual(findings["targeted_users"], {"admin": 5})

    def test_below_threshold_not_flagged(self):
        findings = self.run_lines([failed(i, "admin", "203.0.113.50") for i in range(4)])
        self.assertEqual(findings["suspicious_ips"], {})

    def test_success_after_multiple_failures(self):
        lines = [failed(i, "admin", "203.0.113.50") for i in range(5)]
        lines.append("2026-10-01 09:01:00 SUCCESS user=admin ip=203.0.113.50")
        findings = self.run_lines(lines)
        self.assertEqual(len(findings["success_after_failures"]), 1)
        self.assertEqual(findings["success_after_failures"][0]["prior_failures"], 5)

    def test_success_before_failures_is_not_flagged(self):
        lines = ["2026-10-01 08:00:00 SUCCESS user=admin ip=203.0.113.50"]
        lines += [failed(i, "admin", "203.0.113.50") for i in range(5)]
        self.assertEqual(self.run_lines(lines)["success_after_failures"], [])

    def test_out_of_order_lines_are_sorted_by_time(self):
        lines = ["2026-10-01 09:01:00 SUCCESS user=admin ip=203.0.113.50"]
        lines += [failed(i, "admin", "203.0.113.50") for i in range(5)]
        self.assertEqual(len(self.run_lines(lines)["success_after_failures"]), 1)

    def test_invalid_threshold_rejected(self):
        for bad in (0, -1, True, "5", 2.5):
            with self.assertRaises(ValueError):
                analyzer.analyze([], bad)


class TestFiles(unittest.TestCase):

    def test_empty_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "empty.log")
            open(path, "w").close()
            findings, malformed = analyzer.analyze_file(path)
        self.assertEqual(findings["total_events"], 0)
        self.assertEqual(malformed, 0)
        self.assertEqual(findings["suspicious_ips"], {})

    def test_sample_file(self):
        findings, malformed = analyzer.analyze_file(SAMPLE)
        self.assertEqual(malformed, 3)
        self.assertEqual(findings["suspicious_ips"], {"203.0.113.50": 6})
        self.assertEqual(findings["targeted_users"], {})
        self.assertEqual(len(findings["success_after_failures"]), 1)
        self.assertEqual(findings["success_after_failures"][0]["user"], "admin")

    def test_missing_file_returns_error_code(self):
        self.assertEqual(analyzer.main(["does_not_exist.log"]), 1)

    def test_report_mentions_review_note(self):
        findings, malformed = analyzer.analyze_file(SAMPLE)
        report = analyzer.format_report(findings, malformed, 5)
        self.assertIn("203.0.113.50", report)
        self.assertIn("not proof of an attack", report)


if __name__ == "__main__":
    unittest.main()
