# 60-Second Demo Script & Outline — Missed-Call Text-Back Pilot (Sitting 5)

**Scope:** Fictional demo only (`Oakridge Heating.example`, fictional callers, `555` numbers). Claims ONLY what Sittings 1–4 verified offline. See `CANT-CLAIM.md` for hard boundaries.

---

## Spoken Script (~60 seconds | ~140 words)

> If you run a local shop and miss a call on a job, you can lose the lead or get stuck playing phone tag. I'm Colton, a cybersecurity student at Bevill State, and I'm building an early pilot for Jasper-area small businesses: a simple missed-call text-back and inquiry organizer.
>
> Here is our offline prototype using fictional data. When a fake caller—Marek Kowalski at 205-555-0114—calls Oakridge Heating.example and misses the desk, it sends a template text asking for their name, needed service, and preferred time. Because they type it themselves, spelled names and phone digits come back cleanly.
>
> In our local 40-call test on a strict zero-silent-pass scorer, all 37 fictional mobile calls scored 100 percent exact with zero normalized fixes, and the 3 fictional landlines—like 205-555-0123—routed straight to a callback queue.
>
> It's an early pilot. Message 205 Digital Help to see how it works.

---

## Visual / Screen Outline (4 Beats)

1. **0:00–0:15 (Problem + Intro):** Plain-English title card (`205 Digital Help — Missed-Call Text-Back Pilot`). Calm voiceover introducing who you are and the missed-call problem.
2. **0:15–0:35 (Fictional Walkthrough):** Show one fictional missed call (`Marek Kowalski`, `205-555-0114`, `Oakridge Heating.example`) -> template SMS -> organized structured record. Label clearly: `FICTIONAL DEMO DATA`.
3. **0:35–0:52 (Offline Proof):** Show the terminal output from `missed_call_textback.py`: `37/37` fictional mobile calls at `100.00%` exact (`0` normalized) and `3` fictional landlines (`CALL-23`, `CALL-30`, `CALL-40`) routed to `VOICE_CALLBACK_QUEUE`.
4. **0:52–1:00 (Honest Close):** Show `205 Digital Help & Research` contact info and `Early Pilot — Offline Prototype`. No guarantees, no hype.
