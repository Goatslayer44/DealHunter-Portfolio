"""Offline unit tests for AI Receptionist Feasibility Eval harness — Sitting 2 (40 fictional scenarios)."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

from scorer import digits_only, format_report, score_predictions, validate_record_schema


ROOT = Path(__file__).resolve().parent


class TestAIReceptionistScorerSitting2(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scenarios = json.loads((ROOT / "scenarios.json").read_text(encoding="utf-8"))
        cls.gold = json.loads((ROOT / "gold_answers.json").read_text(encoding="utf-8"))
        cls.flawed_s1 = json.loads((ROOT / "flawed_sample.json").read_text(encoding="utf-8"))
        cls.flawed_s2 = json.loads((ROOT / "flawed_sample_sitting2.json").read_text(encoding="utf-8"))

    def test_forty_fictional_scenarios_and_gold_answers_align_and_use_555_numbers(self) -> None:
        self.assertEqual(len(self.scenarios), 40)
        self.assertEqual(len(self.gold), 40)
        self.assertEqual([s["scenario_id"] for s in self.scenarios], [g["scenario_id"] for g in self.gold])

        # Verify required Sitting 2 disruption categories are present
        all_tags = {tag for s in self.scenarios for tag in s["disruptions"]}
        for required_tag in (
            "same_name_as_another_caller",
            "landline_callback_no_sms",
            "angry_caller_talking_over_assistant",
            "spanish_language_caller",
            "misspelled_name_then_corrected",
            "impossible_closed_day_appointment_renegotiated",
        ):
            self.assertIn(required_tag, all_tags)

        # Verify two distinct callers share the exact same name (CALL-21 and CALL-22)
        gold_by_id = {g["scenario_id"]: g for g in self.gold}
        self.assertEqual(gold_by_id["CALL-21"]["caller_name"], gold_by_id["CALL-22"]["caller_name"])
        self.assertNotEqual(gold_by_id["CALL-21"]["callback_number"], gold_by_id["CALL-22"]["callback_number"])
        self.assertNotEqual(gold_by_id["CALL-21"]["service_requested"], gold_by_id["CALL-22"]["service_requested"])

        # All 40 gold records pass strict schema and use fictional 555 exchange
        for g in self.gold:
            self.assertEqual(validate_record_schema(g), [])
            d = digits_only(g["callback_number"])
            self.assertEqual(len(d), 10)
            self.assertEqual(d[3:6], "555", f"Expected fictional 555 exchange in {g['scenario_id']}")

    def test_gold_records_score_100_percent_exact_on_all_40(self) -> None:
        result = score_predictions(self.gold, self.gold)
        s = result["summary"]
        self.assertEqual(s["scenarios_total"], 40)
        self.assertEqual(s["scenarios_present"], 40)
        self.assertTrue(s["schema_all_valid"])
        self.assertEqual(s["schema_valid_pct"], 100.0)
        self.assertEqual(s["caller_name_exact_pct"], 100.0)
        self.assertEqual(s["callback_number_exact_pct"], 100.0)
        self.assertEqual(s["service_requested_exact_pct"], 100.0)
        self.assertEqual(s["preferred_datetime_exact_pct"], 100.0)
        self.assertEqual(s["normalized_field_flags_total"], 0)
        self.assertEqual(s["all_core_fields_exact_pct"], 100.0)

    def test_sitting1_flawed_records_catch_every_planted_error(self) -> None:
        preds = copy.deepcopy(self.gold)
        flawed_by_id = {r["scenario_id"]: r for r in self.flawed_s1}
        preds = [flawed_by_id.get(r["scenario_id"], r) for r in preds]

        result = score_predictions(self.gold, preds)
        by_id = {item["scenario_id"]: item for item in result["per_scenario"]}

        self.assertEqual(by_id["CALL-01"]["fields"]["caller_name"]["status"], "MISMATCH")
        self.assertEqual(by_id["CALL-02"]["fields"]["callback_number"]["status"], "MISMATCH")
        self.assertEqual(by_id["CALL-03"]["fields"]["preferred_datetime"]["status"], "MISMATCH")
        self.assertFalse(by_id["CALL-04"]["schema_valid"])
        self.assertTrue(any("missing_fields: preferred_datetime" in e for e in by_id["CALL-04"]["schema_errors"]))
        self.assertEqual(result["summary"]["all_core_fields_exact_pct"], 90.0)

    def test_sitting2_flawed_records_catch_all_new_edge_case_errors(self) -> None:
        preds = copy.deepcopy(self.gold)
        flawed_by_id = {r["scenario_id"]: r for r in self.flawed_s2}
        preds = [flawed_by_id.get(r["scenario_id"], r) for r in preds]

        result = score_predictions(self.gold, preds)
        by_id = {item["scenario_id"]: item for item in result["per_scenario"]}

        # CALL-21: same-name mixup (wrong phone + wrong service)
        self.assertEqual(by_id["CALL-21"]["fields"]["callback_number"]["status"], "MISMATCH")
        self.assertEqual(by_id["CALL-21"]["fields"]["service_requested"]["status"], "MISMATCH")
        # CALL-23: landline misread
        self.assertEqual(by_id["CALL-23"]["fields"]["callback_number"]["status"], "MISMATCH")
        # CALL-24: angry caller misspelled name
        self.assertEqual(by_id["CALL-24"]["fields"]["caller_name"]["status"], "MISMATCH")
        # CALL-25: Spanish caller wrong time
        self.assertEqual(by_id["CALL-25"]["fields"]["preferred_datetime"]["status"], "MISMATCH")
        # CALL-26: kept wrong initial spelling instead of corrected spelling
        self.assertEqual(by_id["CALL-26"]["fields"]["caller_name"]["status"], "MISMATCH")
        # CALL-27: accepted impossible closed-Sunday time as-is instead of agreed Tuesday slot
        self.assertEqual(by_id["CALL-27"]["fields"]["preferred_datetime"]["status"], "MISMATCH")

        # 6 of 40 failed -> 34/40 = 85.0% exact
        self.assertEqual(result["summary"]["all_core_fields_exact_pct"], 85.0)

    def test_normalization_never_silently_passes_as_exact(self) -> None:
        preds = copy.deepcopy(self.gold)
        # Apply recoverable formatting/case/punctuation variations on CALL-01
        preds[0]["caller_name"] = "  marek   kowalski! "
        preds[0]["callback_number"] = "+1 (205) 555-0114"
        preds[0]["service_requested"] = "furnace repair, no heat"
        preds[0]["preferred_datetime"] = "2026-11-24T09:00"

        result = score_predictions(self.gold, preds)
        s = result["summary"]
        c01 = result["per_scenario"][0]

        for field in ("caller_name", "callback_number", "service_requested", "preferred_datetime"):
            self.assertEqual(c01["fields"][field]["status"], "NORMALIZED")
            self.assertFalse(c01["fields"][field]["exact"])
            self.assertTrue(c01["fields"][field]["normalized"])

        self.assertFalse(c01["all_core_exact"])
        self.assertEqual(len(c01["normalized_fields"]), 4)
        self.assertEqual(s["normalized_field_flags_total"], 4)
        # Strict schema also flags non-canonical datetime format
        self.assertFalse(c01["schema_valid"])

        report = format_report(result)
        self.assertIn("NORMALIZED (caller_name)", report)
        self.assertIn("NORMALIZED (callback_number)", report)
        self.assertIn("NORMALIZED (preferred_datetime)", report)

    def test_extra_field_fails_loudly(self) -> None:
        bad = copy.deepcopy(self.gold[0])
        bad["unexpected_extra_key"] = "should_fail"
        errors = validate_record_schema(bad)
        self.assertTrue(any("extra_fields: unexpected_extra_key" in e for e in errors))

    def test_cli_exits_nonzero_on_schema_error(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scorer.py"),
                "--gold",
                str(ROOT / "gold_answers.json"),
                "--pred",
                str(ROOT / "flawed_sample.json"),
                "--fail-on-schema-error",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("missing_fields: preferred_datetime", proc.stdout)


if __name__ == "__main__":
    unittest.main()
