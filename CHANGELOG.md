# DealHunter Portfolio — Release Notes

*Plain-English changelog for this portfolio, generated from the full commit history through November 24, 2026.*

---

## November 24, 2026 — The AI receptionist evaluation is complete

- **Missed-call text-back prototype finished and tested.** A local simulator for the text-back pilot was added, along with the system design document that maps how a real version would work. In the scored head-to-head test, all 37 fictional mobile callers were captured exactly, and the 3 landline callers were routed to a voice-callback list instead of being lost — because landlines can't receive texts. *(Commit `0bdf523`)*
- **A 60-second demo script, with honest limits.** The project now includes a short demo script (144 spoken words, fictional business only) and a “What this can't claim yet” page that lists, in writing, what the test does *not* prove — no real-world reply rates, no live texting costs, no real customers yet. *(Commit `f49c313`)*
- **A proper introduction.** The front page now says who's behind the work — Colton Thorpe, Bevill State cybersecurity student and owner of 205 Digital Help & Research in Jasper, Alabama — and marks the five-part receptionist evaluation as complete. *(Commit `9ef9726`)*

## November 23, 2026 — Safety hardening

- **The repo was hardened against accidental leaks.** File-ignore rules now block credentials, secret files, price logs, databases, and photos from ever being committed by accident — while keeping the four fictional demo spreadsheets that are supposed to be public. This followed a full credential audit that found zero exposed secrets. *(Commit `262083e`)*

## November 22, 2026 — Three new tools in one day

- **AI Receptionist Feasibility Eval — first release.** An offline test harness that scores whether an AI phone assistant can reliably take down names, callback numbers, services, and appointment times across 40 fictional call scenarios — with a strict scorer that never silently passes a wrong answer. Early finding, published in the repo: a simple missed-call text-back beats voice AI. *(Commit `1160940`)*
- **Public Email & Website Check — upgraded to v1.1.** The domain security checkup tool got stricter and more honest: it no longer labels anything a “pass” it can't verify, its DMARC check now follows the full standard lookup path, and its wording was tightened so a customer reading the report can't be misled. 9 of 9 tests passing. *(Commit `95066a6`)*
- **Public Email & Website Check — first release.** A checkup tool that reads a business's public email-security records (SPF and DMARC) and confirms its website answers securely over HTTPS. No port scanning, no probing — public records only. *(Commit `e7392ca`)*
- **Email Header & Phishing Triage Analyzer.** A tool that reads a suspicious email's hidden headers and flags the classic phishing signs — mismatched sender addresses, spoofed display names, and disguised links. Works fully offline on fictional sample emails. 6 of 6 tests passing. *(Commit `b531ad4`)*

## November 19, 2026 — Spreadsheet Cleanup Tool

- **Spreadsheet Cleanup Tool demo added.** A Python tool that cleans up messy Excel/CSV files and merges them into one tidy report — the same kind of cleanup offered to small businesses drowning in scattered spreadsheets. *(Commit `ee0ed8b`)*

## October 18, 2026 — Where it started

- **Security Log Analyzer.** A cybersecurity learning project that reads fictional login logs and flags repeated failed logins, suspicious addresses, and logins that succeed right after a string of failures. *(Commit `583aa54`)*
- **Portfolio quality pass.** Input validation, an automated test suite, continuous-integration checks on every push, and a proper README. *(Commit `22da1c3`)*
- **Initial DealHunter project.** The first version: a small Python program that identifies products from their titles, estimates resale profit, and stores results in a database. *(Commit `b8b029f`)*

---

*Every tool in this portfolio runs on fictional or public data only. Test counts above are the counts reported in each commit. If a tool can't claim something yet, the repo says so — that's deliberate.*
