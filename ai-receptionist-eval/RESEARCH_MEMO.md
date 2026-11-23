# Research Memo — AI Receptionist Feasibility & GPT-Live-1.1 (Sitting 1)

**Date:** 2026-11-22  
**Mode:** Offline research only. Zero paid API calls, zero phone numbers connected, zero real calls recorded.

---

## 1. GPT-Live-1.1 API Requirements & Verified Official Pricing

Verified directly from OpenAI's official API documentation and announcement:
- **Official model docs:** https://developers.openai.com/api/docs/models/gpt-live-1.1
- **Official announcement:** https://community.openai.com/t/gpt-live-1-1-has-arrived-in-the-api/1418537

| Item | Verified Official Detail |
|---|---|
| Model ID | `gpt-live-1.1` (full-duplex voice model; `v1/live/sessions` endpoint) |
| Active voice rate | **$0.05 / minute** |
| Standby voice rate | **$0.02 / minute** (applies to WebRTC sessions while inference is paused; idle timeout configurable 5–60s) |
| Extra API charges | **Backend model and tool usage billed separately** (exact backend token/tool cost depends on chosen text model and prompt size — `UNVERIFIED` until measured on a real workload) |
| Telephony / carrier | **NOT included** in OpenAI pricing (SIP/PSTN phone number, inbound voice minutes, and SMS fees from a carrier such as Twilio/Telnyx are separate and `UNVERIFIED` until quoted for a live line) |

---

## 2. Estimated Monthly OpenAI Voice Cost (100 / 500 / 1,000 Active Minutes)

*Voice-session billing only (`$0.05/min` active). Standby assumes an illustrative 20% idle overhead at `$0.02/min` (assumption only; actual standby ratio depends on call pattern). Backend reasoning/tool tokens and telephony/carrier fees are **excluded** and will raise the real bill.*

| Monthly Active Minutes | Active Voice Only (`$0.05/min`) | + Illustrative 20% Standby (`$0.02/min`) | Backend Model/Tool & Telephony |
|---:|---:|---:|---|
| **100 min** (~33 three-min calls) | **$5.00 / mo** | **$5.40 / mo** | Extra (`UNVERIFIED`) |
| **500 min** (~167 three-min calls) | **$25.00 / mo** | **$27.00 / mo** | Extra (`UNVERIFIED`) |
| **1,000 min** (~333 three-min calls) | **$50.00 / mo** | **$54.00 / mo** | Extra (`UNVERIFIED`) |

*(Note: If a line stays open in standby for long idle windows—e.g., an always-open kiosk—standby charges alone run `$1.20/hour`.)*

---

## 3. What This Local Harness Covers vs. What Still Needs a Live Voice Model

- **Covered locally today ($0):** Structured extraction scoring, strict schema enforcement, exact 10-digit phone checking, exact vs. fuzzy name checking, mid-call correction handling (wrong phone/time corrected later in the same transcript), and error visibility.
- **NOT covered locally (requires a live voice model + audio testing later):** Real speech-to-text acoustic errors (Southern/regional accents, muffled speakerphones, background engines/dogs), turn-taking/barge-in timing, latency over PSTN phone audio (8 kHz narrowband audio is much harder than clean web mic audio), and live caller frustration.

---

## 4. Privacy & Call-Recording Consent Risks

- **Alabama law (general overview, NOT legal advice):** Alabama is a **one-party consent state** under `Ala. Code §§ 13A-11-30, 13A-11-31`, aligned with federal `18 U.S.C. § 2511(2)(d)` (sources: [RecordingLaw](https://www.recordinglaw.com/united-states-recording-laws/one-party-consent-states/alabama-recording-laws/phone-calls/), [RecordPhoneCall](https://recordphonecall.com/legal/us/alabama/)).
- **Critical interstate risk for a business line:** Even if a business is in Jasper, Alabama, callers can be physically located in **all-party consent states** (such as Florida, California, or Illinois).
- **Mandatory safeguard before any future live test:** Play an upfront disclosure at the start of every call (*"This call is assisted by an automated system and may be recorded for scheduling"*), store no raw audio/PII longer than necessary, and confirm legal compliance before touching real customer calls.
- **Phase 1 rule:** Zero real phone numbers and zero real calls recorded.

---

## 5. Known Failure Modes

- **Task-brief benchmark note:** The task brief cites independent testing of GPT-Live-1.1 showing ~43% approved-response reproduction and continuing errors on spelled names and phone numbers. *(Primary source URL for that specific 43% benchmark was not independently verified during this offline search and is therefore marked `UNVERIFIED` here — the failure modes themselves are directly targeted by our 20-scenario harness.)*
- **High-risk failure classes for local service businesses:**
  1. **Spelled names** (`K-O-W-A-L-S-K-I`, `B-O-U-D-R-E-A-U-X`, `N-G-U-Y-E-N`) silently mangled by 1–2 letters.
  2. **Transposed or misheard phone digits** — a single wrong digit means the shop can never call the customer back.
  3. **Mid-call corrections** — model keeps the first phone number or first appointment time instead of the corrected one.
  4. **Repeated questions / awkward barge-in** — callers hang up on noisy lines before leaving their info.
