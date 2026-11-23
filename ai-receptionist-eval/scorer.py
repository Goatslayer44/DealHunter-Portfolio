"""Offline Validator & Hardened Field-Level Scorer for AI Receptionist Eval (Sitting 2).

Python stdlib only. Zero network calls.
Strict schema validation (fails loudly on missing/extra fields).
Hardened normalization with ZERO silent passes:
  - Every field reports one of: EXACT, NORMALIZED, MISMATCH.
  - A match achieved only through normalization (case, whitespace, punctuation,
    phone formatting/country-code 1, or alternate datetime format) is flagged
    explicitly as NORMALIZED and is NEVER counted as EXACT.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from difflib import SequenceMatcher
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = (
    "scenario_id",
    "caller_name",
    "callback_number",
    "service_requested",
    "preferred_datetime",
    "notes",
)
REQUIRED_SET = set(REQUIRED_FIELDS)
DATETIME_STRICT_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")

DATETIME_TOLERATED_FORMATS = (
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%m/%d/%Y %H:%M",
    "%Y-%m-%d %I:%M %p",
    "%m/%d/%Y %I:%M %p",
)


def strip_diacritics(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize_name(value: str) -> str:
    """Case-fold, strip diacritics, remove punctuation (keeping letters/digits/spaces), collapse whitespace."""
    cleaned = strip_diacritics(value).lower()
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    return " ".join(cleaned.split())


def normalize_service(value: str) -> str:
    """Case-fold, remove punctuation, collapse whitespace."""
    cleaned = strip_diacritics(value).lower()
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    return " ".join(cleaned.split())


def digits_only(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def normalize_us_phone_digits(value: str) -> tuple[str, bool]:
    """Extract digits; strip a single leading US country code '1' from 11-digit strings.

    Returns (digits, stripped_leading_one).
    """
    d = digits_only(value)
    if len(d) == 11 and d.startswith("1"):
        return d[1:], True
    return d, False


def parse_tolerated_datetime(value: str) -> tuple[str | None, str | None]:
    """Parse tolerated alternate datetime formats into canonical 'YYYY-MM-DD HH:MM'."""
    raw = " ".join(value.strip().split())
    for fmt in DATETIME_TOLERATED_FORMATS:
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.strftime("%Y-%m-%d %H:%M"), fmt
        except ValueError:
            continue
    return None, None


def fuzzy_ratio(a: str, b: str) -> float:
    return round(SequenceMatcher(None, normalize_name(a), normalize_name(b)).ratio(), 4)


def token_overlap(a: str, b: str) -> float:
    ta = set(normalize_service(a).split())
    tb = set(normalize_service(b).split())
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return round(len(ta & tb) / len(ta | tb), 4)


def validate_record_schema(record: Any) -> list[str]:
    """Return list of schema errors; non-empty means loud schema failure."""
    errors: list[str] = []
    if not isinstance(record, dict):
        return ["record_not_object: record must be a JSON object"]

    keys = set(record.keys())
    missing = sorted(REQUIRED_SET - keys)
    extra = sorted(keys - REQUIRED_SET)
    if missing:
        errors.append(f"missing_fields: {', '.join(missing)}")
    if extra:
        errors.append(f"extra_fields: {', '.join(extra)}")

    for field in REQUIRED_FIELDS:
        if field in record and not isinstance(record[field], str):
            errors.append(f"invalid_type:{field} must be string")
        elif field in record and field != "notes" and not record[field].strip():
            errors.append(f"empty_required_field:{field}")

    if "preferred_datetime" in record and isinstance(record["preferred_datetime"], str):
        if record["preferred_datetime"].strip() and not DATETIME_STRICT_RE.match(record["preferred_datetime"].strip()):
            errors.append(f"invalid_datetime_format:{record['preferred_datetime']}")

    return errors


def _compare_name(gold: str, pred: str) -> dict[str, Any]:
    if pred == gold:
        return {"status": "EXACT", "exact": True, "normalized": False, "reason": None, "fuzzy": 1.0, "gold": gold, "pred": pred}
    if normalize_name(pred) == normalize_name(gold):
        return {
            "status": "NORMALIZED",
            "exact": False,
            "normalized": True,
            "reason": "matched_after_case_whitespace_or_punctuation_normalization",
            "fuzzy": 1.0,
            "gold": gold,
            "pred": pred,
        }
    return {
        "status": "MISMATCH",
        "exact": False,
        "normalized": False,
        "reason": "name_differs",
        "fuzzy": fuzzy_ratio(pred, gold),
        "gold": gold,
        "pred": pred,
    }


def _compare_phone(gold: str, pred: str) -> dict[str, Any]:
    gold_d, _ = normalize_us_phone_digits(gold)
    pred_d, stripped_one = normalize_us_phone_digits(pred)
    if pred == gold and len(gold_d) == 10:
        return {
            "status": "EXACT",
            "exact": True,
            "normalized": False,
            "reason": None,
            "gold_digits": gold_d,
            "pred_digits": pred_d,
            "gold": gold,
            "pred": pred,
        }
    if len(gold_d) == 10 and pred_d == gold_d:
        reason = "matched_after_stripping_leading_country_code_1_and_formatting" if stripped_one else "matched_after_phone_formatting_normalization"
        return {
            "status": "NORMALIZED",
            "exact": False,
            "normalized": True,
            "reason": reason,
            "gold_digits": gold_d,
            "pred_digits": pred_d,
            "gold": gold,
            "pred": pred,
        }
    return {
        "status": "MISMATCH",
        "exact": False,
        "normalized": False,
        "reason": "phone_digits_differ",
        "gold_digits": gold_d,
        "pred_digits": pred_d,
        "gold": gold,
        "pred": pred,
    }


def _compare_service(gold: str, pred: str) -> dict[str, Any]:
    if pred == gold:
        return {"status": "EXACT", "exact": True, "normalized": False, "reason": None, "token_overlap": 1.0, "gold": gold, "pred": pred}
    if normalize_service(pred) == normalize_service(gold):
        return {
            "status": "NORMALIZED",
            "exact": False,
            "normalized": True,
            "reason": "matched_after_case_whitespace_or_punctuation_normalization",
            "token_overlap": 1.0,
            "gold": gold,
            "pred": pred,
        }
    return {
        "status": "MISMATCH",
        "exact": False,
        "normalized": False,
        "reason": "service_differs",
        "token_overlap": token_overlap(pred, gold),
        "gold": gold,
        "pred": pred,
    }


def _compare_datetime(gold: str, pred: str) -> dict[str, Any]:
    if pred == gold:
        return {"status": "EXACT", "exact": True, "normalized": False, "reason": None, "gold": gold, "pred": pred}
    if pred.strip() == gold.strip():
        return {
            "status": "NORMALIZED",
            "exact": False,
            "normalized": True,
            "reason": "matched_after_surrounding_whitespace_trim",
            "gold": gold,
            "pred": pred,
        }
    parsed_canonical, used_fmt = parse_tolerated_datetime(pred)
    if parsed_canonical is not None and parsed_canonical == gold.strip():
        return {
            "status": "NORMALIZED",
            "exact": False,
            "normalized": True,
            "reason": f"matched_after_datetime_format_normalization ({used_fmt})",
            "gold": gold,
            "pred": pred,
        }
    return {"status": "MISMATCH", "exact": False, "normalized": False, "reason": "datetime_differs", "gold": gold, "pred": pred}


def score_predictions(
    gold_records: list[dict[str, Any]],
    pred_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Score produced records against gold records with strict schema & no-silent-pass normalization."""
    gold_by_id: dict[str, dict[str, Any]] = {}
    for g in gold_records:
        sid = g["scenario_id"]
        if sid in gold_by_id:
            raise ValueError(f"Duplicate scenario_id in gold set: {sid}")
        gold_by_id[sid] = g

    pred_by_id: dict[str, dict[str, Any]] = {}
    global_schema_errors: list[str] = []
    for idx, p in enumerate(pred_records):
        if not isinstance(p, dict) or not isinstance(p.get("scenario_id"), str):
            global_schema_errors.append(f"pred[{idx}]: missing or non-string scenario_id")
            continue
        sid = p["scenario_id"]
        if sid in pred_by_id:
            global_schema_errors.append(f"duplicate_prediction:{sid}")
            continue
        if sid not in gold_by_id:
            global_schema_errors.append(f"unknown_scenario_id:{sid}")
            continue
        pred_by_id[sid] = p

    per_scenario: list[dict[str, Any]] = []
    totals = {
        "scenarios_total": len(gold_records),
        "scenarios_present": 0,
        "schema_valid_count": 0,
        "name_exact": 0,
        "name_normalized": 0,
        "name_fuzzy_sum": 0.0,
        "phone_exact": 0,
        "phone_normalized": 0,
        "service_exact": 0,
        "service_normalized": 0,
        "datetime_exact": 0,
        "datetime_normalized": 0,
        "all_core_exact": 0,
        "normalized_field_flags_total": 0,
    }

    for g in gold_records:
        sid = g["scenario_id"]
        p = pred_by_id.get(sid)
        if p is None:
            per_scenario.append(
                {
                    "scenario_id": sid,
                    "present": False,
                    "schema_valid": False,
                    "schema_errors": [f"missing_prediction_record:{sid}"],
                    "normalized_fields": [],
                    "fields": {
                        "caller_name": {"status": "MISMATCH", "exact": False, "normalized": False, "fuzzy": 0.0, "gold": g["caller_name"], "pred": None},
                        "callback_number": {"status": "MISMATCH", "exact": False, "normalized": False, "gold_digits": digits_only(g["callback_number"]), "pred_digits": "", "gold": g["callback_number"], "pred": None},
                        "service_requested": {"status": "MISMATCH", "exact": False, "normalized": False, "token_overlap": 0.0, "gold": g["service_requested"], "pred": None},
                        "preferred_datetime": {"status": "MISMATCH", "exact": False, "normalized": False, "gold": g["preferred_datetime"], "pred": None},
                    },
                    "all_core_exact": False,
                }
            )
            continue

        totals["scenarios_present"] += 1
        schema_errors = validate_record_schema(p)
        schema_valid = len(schema_errors) == 0
        if schema_valid:
            totals["schema_valid_count"] += 1

        p_name = p.get("caller_name") if isinstance(p.get("caller_name"), str) else ""
        p_phone = p.get("callback_number") if isinstance(p.get("callback_number"), str) else ""
        p_service = p.get("service_requested") if isinstance(p.get("service_requested"), str) else ""
        p_dt = p.get("preferred_datetime") if isinstance(p.get("preferred_datetime"), str) else ""

        f_name = _compare_name(g["caller_name"], p_name)
        f_phone = _compare_phone(g["callback_number"], p_phone)
        f_service = _compare_service(g["service_requested"], p_service)
        f_dt = _compare_datetime(g["preferred_datetime"], p_dt)

        fields = {
            "caller_name": f_name,
            "callback_number": f_phone,
            "service_requested": f_service,
            "preferred_datetime": f_dt,
        }
        normalized_fields = [k for k, v in fields.items() if v["normalized"]]
        totals["normalized_field_flags_total"] += len(normalized_fields)

        if f_name["exact"]:
            totals["name_exact"] += 1
        elif f_name["normalized"]:
            totals["name_normalized"] += 1
        totals["name_fuzzy_sum"] += f_name["fuzzy"]

        if f_phone["exact"]:
            totals["phone_exact"] += 1
        elif f_phone["normalized"]:
            totals["phone_normalized"] += 1

        if f_service["exact"]:
            totals["service_exact"] += 1
        elif f_service["normalized"]:
            totals["service_normalized"] += 1

        if f_dt["exact"]:
            totals["datetime_exact"] += 1
        elif f_dt["normalized"]:
            totals["datetime_normalized"] += 1

        all_exact = schema_valid and all(v["exact"] for v in fields.values())
        if all_exact:
            totals["all_core_exact"] += 1

        per_scenario.append(
            {
                "scenario_id": sid,
                "present": True,
                "schema_valid": schema_valid,
                "schema_errors": schema_errors,
                "normalized_fields": normalized_fields,
                "fields": fields,
                "all_core_exact": all_exact,
            }
        )

    n = max(1, totals["scenarios_total"])
    schema_all_valid = (len(global_schema_errors) == 0) and (totals["schema_valid_count"] == totals["scenarios_total"])
    summary = {
        "scenarios_total": totals["scenarios_total"],
        "scenarios_present": totals["scenarios_present"],
        "schema_all_valid": schema_all_valid,
        "schema_valid_pct": round(100.0 * totals["schema_valid_count"] / n, 2),
        "caller_name_exact_pct": round(100.0 * totals["name_exact"] / n, 2),
        "caller_name_normalized_count": totals["name_normalized"],
        "caller_name_avg_fuzzy": round(totals["name_fuzzy_sum"] / n, 4),
        "callback_number_exact_pct": round(100.0 * totals["phone_exact"] / n, 2),
        "callback_number_normalized_count": totals["phone_normalized"],
        "service_requested_exact_pct": round(100.0 * totals["service_exact"] / n, 2),
        "service_requested_normalized_count": totals["service_normalized"],
        "preferred_datetime_exact_pct": round(100.0 * totals["datetime_exact"] / n, 2),
        "preferred_datetime_normalized_count": totals["datetime_normalized"],
        "normalized_field_flags_total": totals["normalized_field_flags_total"],
        "all_core_fields_exact_pct": round(100.0 * totals["all_core_exact"] / n, 2),
        "global_schema_errors": global_schema_errors,
    }
    return {"summary": summary, "per_scenario": per_scenario}


def format_report(result: dict[str, Any]) -> str:
    s = result["summary"]
    lines = [
        "=== AI RECEPTIONIST EVAL SCORER (SITTING 2) ===",
        f"Scenarios:          {s['scenarios_present']} / {s['scenarios_total']} present",
        f"Schema valid:       {s['schema_valid_pct']:.2f}% (all valid: {s['schema_all_valid']})",
        f"Name exact / norm:  {s['caller_name_exact_pct']:.2f}% exact | {s['caller_name_normalized_count']} normalized | avg fuzzy {s['caller_name_avg_fuzzy']:.4f}",
        f"Phone exact / norm: {s['callback_number_exact_pct']:.2f}% exact | {s['callback_number_normalized_count']} normalized",
        f"Service exact/norm: {s['service_requested_exact_pct']:.2f}% exact | {s['service_requested_normalized_count']} normalized",
        f"Datetime exact/nrm: {s['preferred_datetime_exact_pct']:.2f}% exact | {s['preferred_datetime_normalized_count']} normalized",
        f"Normalized flags:   {s['normalized_field_flags_total']} total (never counted as exact)",
        f"ALL core exact:     {s['all_core_fields_exact_pct']:.2f}%",
    ]
    if s["global_schema_errors"]:
        lines.append("")
        lines.append("GLOBAL SCHEMA ERRORS:")
        for err in s["global_schema_errors"]:
            lines.append(f"  - {err}")

    lines.append("")
    lines.append("Per-Scenario Results:")
    for item in result["per_scenario"]:
        f = item["fields"]
        if item["all_core_exact"]:
            tag = "EXACT"
        elif item["schema_valid"] and all(v["status"] in {"EXACT", "NORMALIZED"} for v in f.values()):
            tag = "NORMALIZED"
        else:
            tag = "FAIL"
        lines.append(
            f"  [{tag}] {item['scenario_id']} | schema={item['schema_valid']} | "
            f"name={f['caller_name']['status']} ({f['caller_name']['fuzzy']:.2f}) | "
            f"phone={f['callback_number']['status']} | "
            f"service={f['service_requested']['status']} | "
            f"dt={f['preferred_datetime']['status']}"
        )
        if item["schema_errors"]:
            lines.append(f"      SCHEMA ERRORS: {'; '.join(item['schema_errors'])}")
        for fname in ("caller_name", "callback_number", "service_requested", "preferred_datetime"):
            fv = f[fname]
            if fv["status"] == "NORMALIZED":
                lines.append(f"      NORMALIZED ({fname}): {fv['reason']} | gold={fv['gold']!r} pred={fv['pred']!r}")
            elif fv["status"] == "MISMATCH":
                lines.append(f"      MISMATCH ({fname}): gold={fv['gold']!r} pred={fv['pred']!r}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and score AI receptionist call records against gold set.")
    parser.add_argument("--gold", type=Path, required=True, help="Path to gold_answers.json")
    parser.add_argument("--pred", type=Path, required=True, help="Path to produced predictions JSON")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Print JSON output")
    parser.add_argument("--fail-on-schema-error", action="store_true", help="Exit non-zero if any schema error exists")
    args = parser.parse_args()

    gold = json.loads(args.gold.read_text(encoding="utf-8"))
    pred = json.loads(args.pred.read_text(encoding="utf-8"))
    result = score_predictions(gold, pred)

    if args.as_json:
        print(json.dumps(result, indent=2))
    else:
        print(format_report(result))

    if args.fail_on_schema_error and not result["summary"]["schema_all_valid"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
