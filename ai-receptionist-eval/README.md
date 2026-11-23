# AI Receptionist Feasibility Test (Phase 1 — Local, $0)

Offline evaluation harness to measure whether an AI phone assistant can reliably extract structured customer intake records (spelled names, 10-digit callback numbers, services, and agreed appointment times) under realistic call disruptions—and compare it honestly against a simpler **Missed-Call Text-Back + Inquiry Organizer**.

## Guardrails
- **100% local & offline ($0):** Zero paid API calls, zero real phone numbers, zero real calls recorded, zero customer outreach.
- **Fictional data only:** All 40 scenarios (`CALL-01`..`CALL-40`) use fictional businesses (`.example`) and fictional `555` phone numbers.

## Files (Sitting 1 + Sitting 2)
- `scenarios.json` — 40 fictional small-business call transcripts covering: spelled names, digit-by-digit phone dictation, mid-call phone/time corrections, interruptions, background noise, mumbled speech, **two distinct callers with the same name (`CALL-21`/`CALL-22`)**, **landline-only callbacks (`CALL-23`/`CALL-30`/`CALL-40`)**, **angry callers talking over the assistant (`CALL-24`/`CALL-32`)**, **Spanish-language callers (`CALL-25`/`CALL-31`)**, **misspelled-then-corrected names (`CALL-26`/`CALL-29`/`CALL-40`)**, and **impossible closed-day appointments renegotiated to an open slot (`CALL-27`/`CALL-28`/`CALL-38`)**.
- `gold_answers.json` — Exact structured gold records for all 40 scenarios (for impossible-day requests, gold captures the **actually agreed** open slot, never the rejected first request).
- `schema.json` — Strict output schema (required keys, `additionalProperties: false`, strict `YYYY-MM-DD HH:MM` datetime format).
- `flawed_sample.json` — Sitting 1 planted-error sample (misspelled name, transposed phone digits, wrong time, missing field).
- `flawed_sample_sitting2.json` — Sitting 2 planted-error sample (same-name mixup, landline misread, angry-caller misspelling, Spanish-caller wrong time, kept wrong initial spelling, impossible closed-day accepted as-is).
- `scorer.py` — Stdlib-only validator and hardened field-level scorer.
- `test_scorer.py` — Offline `unittest` suite (7 tests).
- `RESEARCH_MEMO.md` — Official-sources-only GPT-Live-1.1 pricing, cost estimates, consent risks, and failure modes.
- `COMPARISON.md` — One-pager comparing AI Voice Receptionist vs. Missed-Call Text-Back.

---

## Documented Normalization Rules (No Silent Passes)

Every core field is scored into one of three explicit states: **`EXACT`**, **`NORMALIZED`**, or **`MISMATCH`**.
**Hard rule:** Any match that required normalization is **flagged explicitly as `NORMALIZED`** in both JSON and text output and is **NEVER counted as `EXACT`** (nor counted in `ALL core exact`).

1. **`caller_name`**
   - `EXACT`: Literal string equality (`pred == gold`).
   - `NORMALIZED`: Matches only after Unicode diacritic stripping (`NFKD`), case-folding, removing punctuation (`[^a-z0-9\s]`), and collapsing repeated whitespace.
   - `MISMATCH`: Differs even after normalization (reports `SequenceMatcher` fuzzy ratio).
2. **`callback_number`**
   - `EXACT`: Literal equality (`pred == gold`) with 10 valid digits (`XXX-555-XXXX`).
   - `NORMALIZED`: Exact 10-digit match only after stripping non-digit formatting characters (`(205) 555-0114`, `205.555.0114`) and/or stripping a single leading US country code `1` from an 11-digit string (`+1 (205) 555-0114`).
   - `MISMATCH`: Any missing, extra, wrong, or transposed digit.
3. **`service_requested`**
   - `EXACT`: Literal string equality (`pred == gold`).
   - `NORMALIZED`: Matches only after diacritic stripping, case-folding, punctuation removal, and whitespace collapsing.
   - `MISMATCH`: Differs even after normalization (reports token overlap ratio).
4. **`preferred_datetime`**
   - `EXACT`: Literal equality (`pred == gold`) in canonical `YYYY-MM-DD HH:MM` 24-hour format.
   - `NORMALIZED`: Matches the exact same date & time after surrounding whitespace trim OR parsing one of the documented alternate formats (`%Y-%m-%dT%H:%M`, `%Y-%m-%dT%H:%M:%S`, `%Y-%m-%d %H:%M:%S`, `%Y/%m/%d %H:%M`, `%m/%d/%Y %H:%M`, `%Y-%m-%d %I:%M %p`, `%m/%d/%Y %I:%M %p`). Note: Non-canonical datetime formats also trigger a strict schema error (`invalid_datetime_format`).
   - `MISMATCH`: Different date/time or unparseable format.

---

## Run in PowerShell

```powershell
cd C:\Users\ColtonThorpe\DealHunter

# Run all 7 offline unit tests
.\.venv\Scripts\python.exe -B -m unittest discover -s business_tools\ai-receptionist-eval -p "test_*.py" -v

# Score gold against gold on all 40 scenarios (must be 100.00% exact, 0 normalized)
.\.venv\Scripts\python.exe business_tools\ai-receptionist-eval\scorer.py --gold business_tools\ai-receptionist-eval\gold_answers.json --pred business_tools\ai-receptionist-eval\gold_answers.json --fail-on-schema-error

# Score Sitting 2 flawed sample (catches all 6 new edge-case errors)
.\.venv\Scripts\python.exe business_tools\ai-receptionist-eval\scorer.py --gold business_tools\ai-receptionist-eval\gold_answers.json --pred business_tools\ai-receptionist-eval\flawed_sample_sitting2.json
```
