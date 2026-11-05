# Training: the appointment-setter academy (EN + ES)

The curriculum we use to take a new hire from day 1 to running calls alone. Every module is in English (`<slug>.md`) and Spanish (`<slug>.es.md`). Built from reviewing real recorded calls: the rules and objection answers are the ones that worked.

| Path | What |
|---|---|
| `curriculum/` | 23 modules × 2 languages, plus `modules.json` (order, phase, minutes, pass mark, titles EN/ES) |
| `quizzes/` | Multiple-choice quizzes per module (`_quiz-calls.json`, `_quiz-ops.json`, `_quiz-zoho.json`), with the correct answer and an explanation |
| `role-map.md` | **Who's what and who's where**: every role, what it owns, and where it sits in the lead-to-close flow |
| `sop-templates/` | Daily routine, EOD report, call QA scorecard, approval gate |

## The path

1. **Orientation**: welcome and golden rules · your role, schedule and KPIs · SCRUM board
2. **Calls (EN/ES)**: hard rules · opener · gatekeeper · discovery · value pitch · booking · top 10 objections · voicemail · SMS
3. **CRM & QA**: CRM process and automation · QA scorecard and pre-send checks
4. **Zoho track (4 weeks)**: CRM basics · records and pipelines · activities · data quality · automation · Campaigns · Flow · Bookings/SalesIQ (each module points at official Zoho videos)
5. **3-3-3 graduation**: 3 calls WITH your manager, 3 OBSERVED calls, 3 calls ALONE

Pass marks are in `modules.json` (the hard-rules module is 100%).

## Use it

- **Zoho Learn / any LMS**: one course per phase, one lesson per module, paste the markdown; import the quiz JSON as question banks.
- **A static site**: the markdown renders as is (GitHub renders it too).
- **Your own brand**: search for `GSD 500 BPO` and `{{` and replace. Placeholders like `{{CALLBACK_NUMBER}}` are yours to fill.

The scripts were written for a bilingual team selling appointment setting to **water-treatment dealers and home-service contractors**, and for setters booking **in-home water analyses** for homeowners. The same structure works for HVAC, solar, roofing and restoration: swap the discovery questions and objections.
