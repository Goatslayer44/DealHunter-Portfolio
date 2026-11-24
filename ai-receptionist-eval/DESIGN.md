# Mock Pipeline Design & Cost Model (Sitting 3 — Local, $0)

**Status:** Design specification only. Zero paid API calls, zero live phone numbers, zero real calls recorded, fictional data only.

---

## 1. End-to-End Architecture: AI Voice Receptionist Path

```text
[Stage 0: PSTN / SIP Call]          <-- NOT LOCAL (requires carrier + recording disclosure)
        |  8 kHz narrowband audio + Caller ID
        v
[Stage 1: Live Voice / STT]         <-- PLUG-IN POINT: gpt-live-1.1 (v1/live/sessions)
        |  Full-duplex audio + turn-taking + barge-in -> raw transcript
        v
[Stage 2: Structured Extraction]    <-- PLUG-IN POINT: backend LLM/tool call + hours check
        |  Transcript + business-hours calendar -> candidate JSON record
        v
[Stage 3: Schema Validator]         <-- RUNS LOCALLY TODAY: schema.json + scorer.py
        |  Strict required keys, additionalProperties: false, YYYY-MM-DD HH:MM
        v
[Stage 4: Field-Level Scorer]       <-- RUNS LOCALLY TODAY: scorer.py vs gold_answers.json
           EXACT vs NORMALIZED (never silent pass) vs MISMATCH
```

### Stage-by-Stage Breakdown & Expected Break Points

| Stage | Runs Locally Today? | Where Live Model / Service Plugs In | Expected Real-World Break Points | Scenarios That Expose It |
|---|---|---|---|---|
| **0. Telephony & Consent** | No (simulated via `scenarios.json`) | Carrier DID + SIP/WebRTC bridge + mandatory upfront recording/AI disclosure | 8 kHz narrowband phone audio degrades consonants (`P/B`, `T/D`, `M/N`); dropped audio on rural cell towers; interstate all-party consent risk | `CALL-04`, `CALL-08`, `CALL-14`, `CALL-17`, `CALL-33`, `CALL-39` |
| **1. Live Voice / STT & Turn-Taking** | No (pre-written text transcripts) | `gpt-live-1.1` full-duplex voice session | Barge-in / angry callers talking over the assistant; background engines, dogs, saws, TV; Spanish-language recognition; spelled-letter spacing | `CALL-01`, `CALL-03`, `CALL-05`, `CALL-11`, `CALL-19`, `CALL-24`, `CALL-25`, `CALL-31`, `CALL-32`, `CALL-34` |
| **2. Extraction & Business-Hours Logic** | Mocked in Sitting 3 (no live LLM) | Backend LLM + tool call checking shop open hours & existing bookings | Keeping initial wrong phone or wrong spelling instead of mid-call correction; accepting impossible closed-day slots; mixing up two callers with the same name; missing "landline — no SMS" notes | `CALL-02`, `CALL-06`, `CALL-10`, `CALL-20`, `CALL-21`/`CALL-22`, `CALL-23`, `CALL-26`, `CALL-27`, `CALL-28`, `CALL-29`, `CALL-30`, `CALL-38`, `CALL-40` |
| **3. Strict Schema Gate** | **Yes** (`schema.json`, `scorer.py`) | Sits right after Stage 2 before any record is saved or sent to the shop owner | Missing fields, extra hallucinated keys, or sloppy datetime strings fail loudly (exit code `2`) | `flawed_sample.json` (`CALL-04`), `test_extra_field_fails_loudly` |
| **4. Field-Level Scorer** | **Yes** (`scorer.py`, `test_scorer.py`) | Offline benchmark against `gold_answers.json` (40 scenarios) | Catches 1-letter name errors, single transposed phone digits, wrong agreed times, and flags any normalized match as `NORMALIZED` (never silent `EXACT`) | `flawed_sample.json`, `flawed_sample_sitting2.json`, `test_normalization_never_silently_passes_as_exact` |

---

## 2. Updated Cost Model (Verified vs. `UNVERIFIED`)

**Hard rule:** Zero invented dollar estimates. Only verified official rates are priced; every unquoted component stays **`UNVERIFIED`** with the exact inputs needed for a real quote.

### A. Verified Official OpenAI `gpt-live-1.1` Voice Rates
Source: [OpenAI API Docs — gpt-live-1.1](https://developers.openai.com/api/docs/models/gpt-live-1.1) and [OpenAI Developer Announcement](https://community.openai.com/t/gpt-live-1-1-has-arrived-in-the-api/1418537).
- **Active voice session:** `$0.05 / minute`
- **Standby voice session (WebRTC idle pause, 5–60s timeout):** `$0.02 / minute`

| Monthly Active Voice Volume | Active Voice Only (`$0.05/min`) | + Illustrative 20% Standby (`$0.02/min`)* | Total Real Monthly Cost |
|---:|---:|---:|---|
| **100 active min** | `$5.00 / mo` | `$5.40 / mo` | `UNVERIFIED` (add Part B below) |
| **500 active min** | `$25.00 / mo` | `$27.00 / mo` | `UNVERIFIED` (add Part B below) |
| **1,000 active min** | `$50.00 / mo` | `$54.00 / mo` | `UNVERIFIED` (add Part B below) |

*\*20% standby is an illustrative assumption only; actual standby minutes depend on session design.*

### B. Unverified Cost Components (Required Before Any Live Pricing or Client Quote)

| Component | Current Status | What a Real Quote Requires |
|---|---|---|
| **Backend LLM / tool-call tokens** | `UNVERIFIED` | Chosen backend text model ID, exact prompt + tool-schema token count, average turns per call, and official per-1M-token pricing. |
| **Telephony / SIP & local DID number** | `UNVERIFIED` | Official carrier quote (e.g., Twilio/Telnyx) for a local Alabama number monthly rental + inbound/outbound PSTN per-minute voice rate + SIP/WebRTC bridge fees. |
| **SMS & A2P 10DLC registration** | `UNVERIFIED` | Official carrier brand/campaign registration fees, monthly campaign fee, and per-segment SMS rate for US local numbers. |
| **Hosting, webhooks & logging** | `UNVERIFIED` | Chosen server/serverless host, storage retention policy, and uptime monitoring plan. |
| **Legal / compliance review** | `UNVERIFIED` | Confirmed recording-disclosure wording (interstate all-party consent callers) and SMS opt-out/consent compliance. |

---

## 3. Comparison Baseline: Missed-Call Text-Back + Inquiry Organizer

Designed to plug into the **exact same `schema.json` and `scorer.py`** so Sitting 4 can score **Missed-Call Text-Back** head-to-head against the AI Voice path on the same 40 fictional scenarios.

```text
[Missed Call Event]
   |  Caller ID number captured automatically (no digit-dictation STT errors)
   v
[Line-Type Check / Landline Guard]
   |-- If landline (CALL-23, CALL-30, CALL-40) --> Cannot SMS! Route to Voicemail / Callback Queue
   |                                               (flagged explicitly, never silently dropped)
   |-- If SMS-capable mobile --> Send Template Text-Back:
                                 "Sorry we missed your call at <Shop>. Reply with:
                                  1) Your name, 2) What you need, 3) Preferred day/time
                                  (Open Mon-Fri 8am-5pm). Reply STOP to opt out."
                                         |
                                         v
                                 [Customer Typed Reply]
                                 (Eliminates spelled-name & background-noise STT errors)
                                         |
                                         v
                                 [Deterministic Inquiry Organizer]  <-- Built locally in Sitting 4
                                         |
                                         v
                                 [SAME schema.json Record] -> [SAME scorer.py]
```

### Why Head-to-Head Scoring Matters in Sitting 4
1. **Where Missed-Call Text-Back should win cleanly:** Spelled names (`CALL-01`, `CALL-04`, `CALL-06`, `CALL-11`, `CALL-16`, `CALL-19`, `CALL-26`, `CALL-29`), callback digits (captured from Caller ID), noisy backgrounds (`CALL-03`, `CALL-05`, `CALL-14`, `CALL-34`), angry barge-in (`CALL-24`, `CALL-32`), and lower running cost.
2. **Where Missed-Call Text-Back has REAL failure modes we must score honestly:**
   - **Landline-only callers (`CALL-23`, `CALL-30`, `CALL-40`):** SMS bounces or never delivers; must be routed to a callback/voicemail fallback and counted honestly.
   - **Incomplete or casual customer texts:** Callers who reply `"call me back"` without a time or service must produce an explicit incomplete/needs-review flag rather than a guessed appointment time.
   - **Closed-day requests (`CALL-27`, `CALL-28`, `CALL-38`):** Template text must state business hours clearly and reject/re-prompt closed days rather than silently booking Sunday.

---

## 4. Sitting 4 Readiness Contract
Sitting 4 (queued until Colton says GO) will implement a local, `$0` **Missed-Call Text-Back + Inquiry Organizer** simulator that consumes fictional missed-call events, outputs records matching `schema.json`, and scores them through `scorer.py` against `gold_answers.json` with zero changes to the scoring bar.
