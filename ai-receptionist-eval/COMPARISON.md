# Comparison One-Pager — AI Voice Receptionist vs. Missed-Call Text-Back

**Question:** For a small local business (plumber, HVAC, auto shop, lawn service), should 205 Digital Help try to sell an **AI Voice Receptionist** or a **Missed-Call Text-Back + Inquiry Organizer** first?

| Factor | AI Voice Receptionist (`gpt-live-1.1` + telephony) | Missed-Call Text-Back + Inquiry Organizer |
|---|---|---|
| **How it works** | AI answers the phone live, talks to the caller, captures name/phone/service/time over audio. | When the owner misses a call, an automatic SMS replies in seconds with a simple text/form asking name, issue, and preferred time; replies land in one clean list. |
| **Setup complexity & cost** | High: telephony SIP/WebRTC bridge, voice model prompts, tool calls, recording disclosure, extensive audio testing. | Low: standard SMS/missed-call trigger + clean inquiry sheet/log (or simple mobile form). |
| **Monthly running cost (estimated)** | `$5–$54+/mo` OpenAI voice minutes **plus** backend LLM/tool tokens **plus** telephony/number fees (total `UNVERIFIED` until quoted). | Low carrier SMS + phone number fees (typically a few dollars/month for low-volume local shops; exact carrier quote `UNVERIFIED` until configured). |
| **Name & phone accuracy risk** | **High risk:** Background noise, accents, spelled last names, and transposed digits silently break callbacks. | **Very low risk:** Caller ID already captures the phone number automatically, and the customer **types** their own name and issue. |
| **Privacy / recording risk** | Must handle call-recording disclosure (including interstate all-party consent callers) and voice-audio retention. | No call audio recorded; standard SMS opt-out/consent rules apply (much simpler to manage cleanly). |
| **What it needs to go live** | Verified accuracy on real narrowband phone audio across noisy/accented callers, telephony bridge, fallback-to-voicemail guard, legal disclosure check. | Carrier SMS registration (A2P 10DLC in the US), business phone forwarding/missed-call trigger, and a 10-minute owner test. |
| **Can be sold honestly sooner?** | **NO** — not until live audio accuracy on names, digits, and mid-call corrections is proven far higher than current error-prone voice demos. | **YES** — solves the exact same "missed job while on a ladder/under a hood" pain point with far higher reliability and zero awkward robot-voice hang-ups. |

## Bottom-Line Recommendation
- **Test AI voice honesty first** (Sittings 1–3) before ever pitching an AI phone receptionist to a paying client.
- **Build and sell Missed-Call Text-Back + Inquiry Organizer first** (prototyped locally in Sitting 4) — it is cheaper, vastly more reliable on names and callback numbers, and genuinely defensible to a local Walker County business owner.
