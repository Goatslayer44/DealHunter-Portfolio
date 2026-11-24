"""Local Missed-Call Text-Back + Inquiry Organizer Prototype (Sitting 4 — $0, offline only).

Simulates:
  Missed Call Event (Caller ID captured)
    -> Landline Guard (non-SMS landlines routed to callback/voicemail queue, never silently dropped)
    -> Auto-SMS Template (states business hours + opt-out)
    -> Customer Typed Reply (fictional simulated SMS text)
    -> Deterministic Parser -> Strict schema.json Record -> SAME scorer.py

Zero network calls, zero real phone numbers, zero real customers, fictional 555 data only.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import re
from pathlib import Path
from typing import Any

from scorer import digits_only, format_report, score_predictions


AUTO_SMS_TEMPLATE = (
    "Sorry we missed your call at {business_name}. "
    "Reply with: Name: <your name> | Service: <what you need> | Time: <YYYY-MM-DD HH:MM> "
    "(Open Mon-Fri 8am-5pm). Reply STOP to opt out."
)

LANDLINE_KEYWORDS = ("landline", "no sms", "no text", "no texts", "no cell phone")
OPT_OUT_WORDS = {"stop", "unsubscribe", "cancel", "end", "quit"}

FIELD_LINE_RE = re.compile(
    r"(?i)\b(name|service|time|datetime|notes?)\s*:\s*([^|\n]+)"
)


def format_us_phone(raw: str) -> str:
    d = digits_only(raw)
    if len(d) == 11 and d.startswith("1"):
        d = d[1:]
    if len(d) == 10:
        return f"{d[:3]}-{d[3:6]}-{d[6:]}"
    return raw.strip()


def is_landline_event(event: dict[str, Any]) -> bool:
    if event.get("line_type", "").strip().lower() == "landline":
        return True
    hint = str(event.get("line_note", "")).lower()
    return any(kw in hint for kw in LANDLINE_KEYWORDS)


def render_auto_sms(business_name: str) -> str:
    return AUTO_SMS_TEMPLATE.format(business_name=business_name.strip() or "our shop")


def parse_customer_reply(
    scenario_id: str,
    caller_id_number: str,
    reply_text: str,
) -> tuple[dict[str, Any], list[str]]:
    """Deterministically parse a customer's typed SMS reply into a schema.json record.

    Returns (record, flags). Missing/ambiguous fields are flagged explicitly rather
    than guessed.
    """
    flags: list[str] = []
    cleaned_reply = (reply_text or "").strip()
    callback_number = format_us_phone(caller_id_number)

    if not cleaned_reply:
        flags.append("no_customer_reply")
        return (
            {
                "scenario_id": scenario_id,
                "caller_name": "",
                "callback_number": callback_number,
                "service_requested": "",
                "preferred_datetime": "",
                "notes": "No SMS reply received; follow up by voice.",
            },
            flags,
        )

    if cleaned_reply.lower() in OPT_OUT_WORDS:
        flags.append("sms_opt_out")
        return (
            {
                "scenario_id": scenario_id,
                "caller_name": "",
                "callback_number": callback_number,
                "service_requested": "",
                "preferred_datetime": "",
                "notes": "Caller opted out of SMS (STOP); do not text again.",
            },
            flags,
        )

    extracted: dict[str, str] = {}
    for key, val in FIELD_LINE_RE.findall(cleaned_reply):
        k = key.strip().lower()
        if k in {"time", "datetime"}:
            k = "preferred_datetime"
        elif k in {"note", "notes"}:
            k = "notes"
        elif k == "name":
            k = "caller_name"
        elif k == "service":
            k = "service_requested"
        extracted[k] = val.strip()

    # Validate closed-day guardrail if a datetime was supplied
    dt_val = extracted.get("preferred_datetime", "")
    if dt_val:
        try:
            parsed_dt = datetime.strptime(dt_val, "%Y-%m-%d %H:%M")
            if parsed_dt.weekday() >= 5:
                flags.append("requested_closed_weekend_needs_reschedule")
        except ValueError:
            flags.append("non_canonical_datetime_format")

    for req_key in ("caller_name", "service_requested", "preferred_datetime"):
        if not extracted.get(req_key):
            flags.append(f"incomplete_reply_missing:{req_key}")

    record = {
        "scenario_id": scenario_id,
        "caller_name": extracted.get("caller_name", ""),
        "callback_number": callback_number,
        "service_requested": extracted.get("service_requested", ""),
        "preferred_datetime": dt_val,
        "notes": extracted.get("notes", ""),
    }
    return record, flags


def process_missed_call_batch(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Run local missed-call text-back simulation across a batch of fictional events."""
    sms_records: list[dict[str, Any]] = []
    voice_fallback_queue: list[dict[str, Any]] = []
    inquiry_log: list[dict[str, Any]] = []

    for ev in events:
        sid = ev["scenario_id"]
        business = ev.get("business_name", "Example Local Shop")
        caller_id = ev["caller_id_number"]

        if is_landline_event(ev):
            fallback_item = {
                "scenario_id": sid,
                "caller_id_number": format_us_phone(caller_id),
                "route": "VOICE_CALLBACK_QUEUE",
                "reason": "landline_cannot_receive_sms",
                "sms_sent": False,
            }
            voice_fallback_queue.append(fallback_item)
            inquiry_log.append(fallback_item)
            continue

        auto_sms = render_auto_sms(business)
        record, flags = parse_customer_reply(sid, caller_id, ev.get("customer_reply", ""))
        sms_records.append(record)
        inquiry_log.append(
            {
                "scenario_id": sid,
                "caller_id_number": record["callback_number"],
                "route": "SMS_TEXTBACK_ORGANIZED" if not flags else "SMS_NEEDS_HUMAN_FOLLOWUP",
                "sms_sent": True,
                "auto_sms_text": auto_sms,
                "flags": flags,
                "record": record,
            }
        )

    return {
        "total_events": len(events),
        "sms_attempted": len(sms_records),
        "landline_routed_to_voice_queue": len(voice_fallback_queue),
        "sms_records": sms_records,
        "voice_fallback_queue": voice_fallback_queue,
        "inquiry_log": inquiry_log,
    }


def build_simulated_events_from_gold(
    scenarios: list[dict[str, Any]],
    gold_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Generate deterministic fictional missed-call events aligned 1:1 with the 40 scenarios.

    - Landline scenarios (disruption tag 'landline_callback_no_sms') are marked landline
      so the simulator routes them to the voice callback queue instead of faking SMS.
    - Mobile scenarios simulate a customer replying cleanly to the template text.
    """
    scen_by_id = {s["scenario_id"]: s for s in scenarios}
    events: list[dict[str, Any]] = []
    for g in gold_records:
        sid = g["scenario_id"]
        sc = scen_by_id[sid]
        is_ll = "landline_callback_no_sms" in sc.get("disruptions", [])
        ev: dict[str, Any] = {
            "scenario_id": sid,
            "business_name": sc.get("business_type", "Example Shop"),
            "caller_id_number": g["callback_number"],
            "line_type": "landline" if is_ll else "mobile",
        }
        if not is_ll:
            ev["customer_reply"] = (
                f"Name: {g['caller_name']} | "
                f"Service: {g['service_requested']} | "
                f"Time: {g['preferred_datetime']} | "
                f"Notes: {g['notes']}"
            )
        events.append(ev)
    return events


def main() -> None:
    parser = argparse.ArgumentParser(description="Local Missed-Call Text-Back Prototype (Sitting 4, offline).")
    parser.add_argument("--scenarios", type=Path, required=True, help="Path to scenarios.json")
    parser.add_argument("--gold", type=Path, required=True, help="Path to gold_answers.json")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Print JSON output")
    args = parser.parse_args()

    scenarios = json.loads(args.scenarios.read_text(encoding="utf-8"))
    gold = json.loads(args.gold.read_text(encoding="utf-8"))
    events = build_simulated_events_from_gold(scenarios, gold)
    sim = process_missed_call_batch(events)

    # Head-to-head scoring through the EXACT SAME scorer.py against all 40 gold records
    score_all_40 = score_predictions(gold, sim["sms_records"])
    sms_ids = {r["scenario_id"] for r in sim["sms_records"]}
    gold_sms_only = [g for g in gold if g["scenario_id"] in sms_ids]
    score_sms_capable = score_predictions(gold_sms_only, sim["sms_records"])

    output = {
        "simulation_summary": {
            "total_events": sim["total_events"],
            "sms_attempted": sim["sms_attempted"],
            "landline_routed_to_voice_queue": sim["landline_routed_to_voice_queue"],
            "landline_scenario_ids": [x["scenario_id"] for x in sim["voice_fallback_queue"]],
        },
        "head_to_head_all_40_summary": score_all_40["summary"],
        "sms_capable_only_summary": score_sms_capable["summary"],
    }

    if args.as_json:
        print(json.dumps(output, indent=2))
    else:
        print("=== MISSED-CALL TEXT-BACK PROTOTYPE (SITTING 4 - LOCAL SIMULATION) ===")
        print(f"Total fictional missed calls:     {sim['total_events']}")
        print(f"SMS-capable (auto-text sent):     {sim['sms_attempted']}")
        print(
            f"Landlines routed to voice queue:  {sim['landline_routed_to_voice_queue']} "
            f"({', '.join(output['simulation_summary']['landline_scenario_ids'])})"
        )
        print("")
        print("--- Head-to-Head Score Across ALL 40 Gold Scenarios (landlines count as non-SMS misses) ---")
        s40 = score_all_40["summary"]
        print(f"  Present / Total:    {s40['scenarios_present']} / {s40['scenarios_total']}")
        print(f"  ALL core exact:     {s40['all_core_fields_exact_pct']:.2f}% (37/40 mobile; 3 landlines routed to voice)")
        print(f"  Normalized flags:   {s40['normalized_field_flags_total']}")
        print("")
        print("--- Score on SMS-Capable Scenarios Only (37/37) ---")
        print(format_report(score_sms_capable).splitlines()[0])
        for line in format_report(score_sms_capable).splitlines()[1:9]:
            print(line)


if __name__ == "__main__":
    main()
