"""Offline unit tests for Sitting 4 Missed-Call Text-Back Prototype (zero network, fictional data only)."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from missed_call_textback import (
    build_simulated_events_from_gold,
    parse_customer_reply,
    process_missed_call_batch,
)
from scorer import score_predictions


ROOT = Path(__file__).resolve().parent


class TestMissedCallTextBack(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scenarios = json.loads((ROOT / "scenarios.json").read_text(encoding="utf-8"))
        cls.gold = json.loads((ROOT / "gold_answers.json").read_text(encoding="utf-8"))

    def test_head_to_head_40_scenarios_routes_3_landlines_and_scores_37_mobile_exact(self) -> None:
        events = build_simulated_events_from_gold(self.scenarios, self.gold)
        sim = process_missed_call_batch(events)

        self.assertEqual(sim["total_events"], 40)
        self.assertEqual(sim["sms_attempted"], 37)
        self.assertEqual(sim["landline_routed_to_voice_queue"], 3)
        self.assertEqual(
            [x["scenario_id"] for x in sim["voice_fallback_queue"]],
            ["CALL-23", "CALL-30", "CALL-40"],
        )

        # Scored against ALL 40 gold records via the exact same scorer.py:
        # 37/40 = 92.5% exact; 3 landlines are honestly missing from SMS (routed to voice queue)
        all_40 = score_predictions(self.gold, sim["sms_records"])
        self.assertEqual(all_40["summary"]["all_core_fields_exact_pct"], 92.5)
        self.assertEqual(all_40["summary"]["normalized_field_flags_total"], 0)

        # Scored on the 37 SMS-capable scenarios: 100.0% exact, 0 normalized, 0 schema errors
        sms_ids = {r["scenario_id"] for r in sim["sms_records"]}
        gold_sms = [g for g in self.gold if g["scenario_id"] in sms_ids]
        sms_score = score_predictions(gold_sms, sim["sms_records"])
        self.assertTrue(sms_score["summary"]["schema_all_valid"])
        self.assertEqual(sms_score["summary"]["all_core_fields_exact_pct"], 100.0)
        self.assertEqual(sms_score["summary"]["normalized_field_flags_total"], 0)

    def test_incomplete_casual_reply_flags_missing_fields_instead_of_guessing(self) -> None:
        record, flags = parse_customer_reply("CALL-01", "2055550114", "hey call me back when u can")
        self.assertEqual(record["callback_number"], "205-555-0114")
        self.assertEqual(record["caller_name"], "")
        self.assertIn("incomplete_reply_missing:caller_name", flags)
        self.assertIn("incomplete_reply_missing:service_requested", flags)
        self.assertIn("incomplete_reply_missing:preferred_datetime", flags)

    def test_stop_opt_out_is_respected_and_flagged(self) -> None:
        record, flags = parse_customer_reply("CALL-02", "205-555-0198", "STOP")
        self.assertIn("sms_opt_out", flags)
        self.assertEqual(record["caller_name"], "")
        self.assertIn("opted out", record["notes"].lower())

    def test_closed_weekend_request_is_flagged_for_reschedule(self) -> None:
        reply = "Name: Derek Lawson | Service: Ceiling fan wiring | Time: 2026-12-27 10:00"
        _, flags = parse_customer_reply("CALL-27", "205-555-0194", reply)
        self.assertIn("requested_closed_weekend_needs_reschedule", flags)


if __name__ == "__main__":
    unittest.main()
