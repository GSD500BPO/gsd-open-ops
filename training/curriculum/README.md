# Curriculum: 23 appointment-setter modules (EN + ES)

Each module is one Markdown file in English (`<slug>.md`) and one in Spanish (`<slug>.es.md`). [`modules.json`](modules.json) holds the order, phase, minutes, pass mark and both titles, so you can generate an LMS course or a static site from it.

| # | Phase | Module | Minutes | Pass |
|---|---|---|---|---|
| 1 | orientation | [Welcome to GSD 500 BPO](welcome.md) · [ES](welcome.es.md) | 20 | 70% |
| 2 | orientation | [Your role, schedule & KPIs](role-and-kpis.md) · [ES](role-and-kpis.es.md) | 30 | 75% |
| 3 | orientation | [SCRUM & the Trello board](scrum-trello.md) · [ES](scrum-trello.es.md) | 30 | 75% |
| 4 | calls | [Hard rules on every call](call-rules.md) · [ES](call-rules.es.md) | 15 | 100% |
| 5 | calls | [Step 1: The opener](call-opener.md) · [ES](call-opener.es.md) | 15 | 75% |
| 6 | calls | [Step 2: Gatekeepers & call screeners](call-gatekeeper.md) · [ES](call-gatekeeper.es.md) | 15 | 75% |
| 7 | calls | [Step 3: Discovery questions](call-discovery.md) · [ES](call-discovery.es.md) | 15 | 75% |
| 8 | calls | [Step 4: The value pitch](call-pitch.md) · [ES](call-pitch.es.md) | 20 | 75% |
| 9 | calls | [Step 5: Booking the appointment](call-booking.md) · [ES](call-booking.es.md) | 20 | 80% |
| 10 | calls | [Step 6: Top objections](call-objections.md) · [ES](call-objections.es.md) | 30 | 80% |
| 11 | calls | [Step 7: Voicemail](call-voicemail.md) · [ES](call-voicemail.es.md) | 10 | 75% |
| 12 | calls | [Step 8: SMS follow-up](call-sms.md) · [ES](call-sms.es.md) | 10 | 80% |
| 13 | crm_qa | [CRM process & automation](crm-process.md) · [ES](crm-process.es.md) | 25 | 75% |
| 14 | crm_qa | [QA scorecard & pre-send checks](qa-scorecard.md) · [ES](qa-scorecard.es.md) | 25 | 80% |
| 15 | zoho | [Zoho 1: CRM basics & navigation](zoho-1-crm-basics.md) · [ES](zoho-1-crm-basics.es.md) | 80 | 80% |
| 16 | zoho | [Zoho 2: Leads, Contacts, Deals & pipelines](zoho-2-records-pipelines.md) · [ES](zoho-2-records-pipelines.es.md) | 140 | 80% |
| 17 | zoho | [Zoho 3: Activities, calls & meetings](zoho-3-activities.md) · [ES](zoho-3-activities.es.md) | 70 | 80% |
| 18 | zoho | [Zoho 4: Views, tags, import, duplicates & reports](zoho-4-data-quality.md) · [ES](zoho-4-data-quality.es.md) | 110 | 80% |
| 19 | zoho | [Zoho 5: Workflow rules, blueprints & cadences](zoho-5-automation.md) · [ES](zoho-5-automation.es.md) | 70 | 80% |
| 20 | zoho | [Zoho 6: Campaigns & email marketing](zoho-6-campaigns.md) · [ES](zoho-6-campaigns.es.md) | 90 | 80% |
| 21 | zoho | [Zoho 7: Zoho Flow](zoho-7-flow.md) · [ES](zoho-7-flow.es.md) | 75 | 80% |
| 22 | zoho | [Zoho 8: Bookings & SalesIQ](zoho-8-bookings.md) · [ES](zoho-8-bookings.es.md) | 45 | 80% |
| 23 | graduation | [3-3-3 graduation program](graduation-333.md) · [ES](graduation-333.es.md) | 90 | 85% |

Total: ~1,050 minutes (~17.5 hours). The Zoho track runs over 4 weeks next to live work; everything else fits in the first week.

## How to use
- **Read on GitHub** in order, or load into Zoho Learn / any LMS (one course per phase, one lesson per module).
- Quizzes for each module: [`../quizzes/`](../quizzes/).

## How to adapt
- Rewrite `call-discovery`, `call-pitch` and `call-objections` for your trade; keep the rest.
- Change both languages together. A module without its `.es.md` twin is incomplete.
- Add a module: new `<slug>.md` + `<slug>.es.md`, an entry in `modules.json`, 3-4 quiz questions.
