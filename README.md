# GSD Open Ops

**How we recruit, test, train and run appointment-setting teams for water-treatment and home-service companies. Free, MIT, in English and Spanish.**

> **We give away the sauce.** Everything in this repo is what we run every day at GSD 500 BPO.
> If you'd rather have it set up, branded and running for your team, that's what we do: **[book a strategy call](https://gsd500bpo.com/strategy-call?utm_source=github&utm_medium=readme&utm_campaign=open-ops)**.

---

## What's inside

| Folder | What it is | Start here |
|---|---|---|
| [`recruiting/`](recruiting/) | **Ramón**, our WhatsApp recruiting bot: lead intake → WhatsApp screening → 1-minute English video → local speaking score (accent, clarity, fluency, grammar) → English/Sales/Typing test → voice roleplay → interview. Plus the prequal test itself | [`recruiting/README.md`](recruiting/README.md) |
| [`training/`](training/) | The setter academy: 23 modules × EN/ES (call rules, opener, gatekeeper, discovery, pitch, booking, top 10 objections, voicemail, SMS, CRM, QA, Zoho track, 3-3-3 graduation), quizzes, SOP templates, and the **role map: who's what and who's where** | [`training/role-map.md`](training/role-map.md) |
| [`crm/`](crm/) | The ownership rules (speed to lead, one open task, 3-day overdue rule), cadences (TA-1..4, FU-1..6), and the recruiting data schema | [`crm/ownership-rules.md`](crm/ownership-rules.md) |
| [`playbooks/`](playbooks/) | The **96-Step Year-Round Prospect Journey**: what to do with every lead that didn't buy (PDF + importable CSV/JSON) | [`playbooks/README.md`](playbooks/README.md) |

## Who it's for

- **Call centers and BPOs** that hire bilingual SDRs/setters and want screening that runs while they sleep.
- **Water-treatment dealers and home-service companies** (HVAC, solar, roofing, restoration) building an in-house appointment desk.
- **Anyone building careers in sales**: the academy is the same material our new hires study.

## How to use it

1. **Hire with Ramón.** `cd recruiting/ramon && cp .env.example .env && python3 tests/test_offline.py`, then follow the go-live steps in [`recruiting/README.md`](recruiting/README.md). It's dry by default: nothing is sent until you say so.
2. **Train with the academy.** Load `training/curriculum/` into Zoho Learn or any LMS (or just read it on GitHub). Graduate people with the 3-3-3 program.
3. **Run the floor with the CRM rules.** Put [`crm/ownership-rules.md`](crm/ownership-rules.md) and [`crm/cadences.md`](crm/cadences.md) into your CRM as tasks and stages.
4. **Never waste a lead.** Import the 96-step journey for every lead that didn't buy.

Search the repo for `{{` and `example.com` to find every value you need to fill in.

## Stack

Python 3 (standard library for the pipeline) · faster-whisper, wav2vec2, SpeechBrain, LanguageTool (local speaking score, no paid APIs) · WhatsApp Cloud API · Zoho Recruit, CRM, Mail, Cliq, Learn · Supabase (storage + public talent page) · plain HTML for the test and roleplay pages.

## Built by GSD 500 BPO

Bilingual appointment setting, CRM automation and back-office teams from Bogotá, Colombia. *We Get Sh\*t Done.*
**Want us to run it for you? → [Strategy call](https://gsd500bpo.com/strategy-call?utm_source=github&utm_medium=readme&utm_campaign=open-ops)**

License: [MIT](LICENSE) · Security: [SECURITY.md](SECURITY.md) · Contributing: [CONTRIBUTING.md](CONTRIBUTING.md)
