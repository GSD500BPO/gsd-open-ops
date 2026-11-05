# How we built a BPO as a solopreneur with AI

GSD 500 BPO is a bilingual appointment-setting and back-office company in Bogotá, Colombia, working for US home-service businesses, mostly water-treatment dealers. For most of its life the "company" was one founder, a CRM, a laptop and a server. This is how the operating system in this repo got built: from scratch, by us, with Claude as the engineering partner and a small crew of bots doing the repetitive work.

Nothing here is a growth hack. Each chapter is a job a BPO has to do every day, written down first as a rule, then automated, then turned into training.

---

## Chapter 1. Cadences before code

The first problem wasn't technology. Leads came in and were called "when someone had time." So before any automation, we wrote the rules down, from reviewing real calls:

- A new lead gets **3 touches in 48 hours**: call → text from the registered line → second call + email the next business day. Each attempt is a numbered note (TA-1 ... TA-4).
- After a conversation, the next task is due in **3 days**. With no conversation, in **5 business days**.
- **Every lead and deal always has one open task.** No open task = anyone may claim it. A task overdue **3 business days** = claimable.
- The owner has **15 minutes** for first contact. The setter who booked the appointment owns the reschedule. Joint work = shared credit.

Those rules are [`crm/ownership-rules.md`](../crm/ownership-rules.md) and [`crm/cadences.md`](../crm/cadences.md). Every automation that came later just enforces them.

**What Claude did here:** turned rambling call reviews and voice notes into short, testable rules, and found the contradictions between them.

## Chapter 2. Data for a niche

A BPO that sells to water-treatment dealers needs to know who the dealers are. We built our own lists from **business data we're allowed to use**: our own CRM, open data, map data, and a lot of manual research, de-duplicated and loaded into a database, then into the CRM. Two rules we kept:

- **Respect the source.** Follow each site's terms of service and robots rules, keep request rates low, collect business information only (no personal data from private profiles), and honor opt-outs.
- **Fields over volume.** A record is only useful once the fields that drive automation are set: business type, language, preferred channel, and for homeowners, owner or renter. [`crm/cadences.md`](../crm/cadences.md#fields-that-drive-automation) lists them.

The **[list pipeline](../data-pipeline/)** is in this repo: clean, dedupe, enrich and export to Zoho CRM, GoHighLevel and HubSpot import files. It ships an OpenStreetMap pull (open data, allowed within its usage policy) and a manual-research template. It deliberately ships **no scraper** for sites whose terms forbid one, such as ad libraries and classifieds; for those we research by hand. [Which sources, and how](../data-pipeline/SOURCES.md).

## Chapter 3. Journeys: 24 steps, then 96

Most leads don't buy on the first visit. So we wrote a **24-step nurture** per trade, bilingual, for homeowners and renters: education first, then money, then a final push. Our setters fill the lead fields that make it work ([video: lead fields that power a 24-step nurture](https://www.youtube.com/watch?v=OEOLl2DHYuY)).

Then we noticed the same homeowner who doesn't need a water system this month will need a roof after a storm, windows before winter, or AC before summer. Four 24-step journeys chained by season became the **[96-Step Year-Round Prospect Journey](../playbooks/96-step-journey/)**: 4 phases × 3 chapters × 8 steps, with merge fields, a 6-step negotiation series before it, and exit rules. Video: [The 96-Step CRM Journey That Sells All Year](https://www.youtube.com/watch?v=fA0oPEkFEo4).

The engine that runs a 24-step journey safely is in **[`journeys/24-step/`](../journeys/24-step/)**: a JSON journey definition, plain-text templates, and a runner that is dry by default and can't send the same message twice.

**What Claude did here:** drafted step themes and angles per chapter, kept 96 steps consistent (IDs, tags, day offsets), and generated the PDF, CSV and JSON from one source so they never drift.

## Chapter 4. Alerts: speed to lead

A cadence written on paper still loses to a lead that sits overnight. The alert layer:

- **Instant first touch:** when a lead arrives, a same-day email + text goes out on Day 0, followed by a short email/SMS sequence over the next days.
- **Alert to a human:** the person who must call gets pinged with a deadline (our dealer-side alert says *call within 1 hour*; our own setters work to the 15-minute rule).
- **Lead scoring:** opens, clicks and especially replies raise a score (we weight a reply far above an open); hot leads go to a human instead of waiting for the next automated step.

The rules are in [`crm/`](../crm/); the guardrails are in [`training/sop-templates/approval-gate.md`](../training/sop-templates/approval-gate.md). The code is in **[`alerts/`](../alerts/)**: new lead and reply alerts to team chat, CRM tasks with a deadline, the score (open +5, click +10, reply +25; Hot at 70, Critical at 90) and a speed-to-lead escalation.

## Chapter 5. Smart leads to setters

Routing is where clean fields pay off. Language decides who calls (a Spanish-speaking homeowner gets a Spanish-speaking setter). Owner/renter and the stated problem decide the script. Leads rotate between setters; the 15-minute rule and the 3-day overdue rule keep anyone from sitting on them; the [role map](../training/role-map.md) says exactly who owns each step from lead to commission.

## Chapter 6. Recruiting and scoring at scale

Setters are the product, and hiring them was the bottleneck: lots of applicants, few who can hold a phone conversation with a US homeowner. So we built **Ramón**, a WhatsApp recruiting bot ([`recruiting/`](../recruiting/)):

1. Every applicant gets the steps on WhatsApp within minutes, plus an ATS record.
2. They send a **1-minute English video**. Our own server scores it: clarity (two speech recognizers must agree on the words), fluency, grammar, and a neutral-accent estimate, 0-100 plus a CEFR level. No paid AI APIs.
3. They take a **prequal test**: English, sales judgement, typing.
4. **Gate:** composite ≥ 65, English ≥ 70, video sent, speaking ≥ 60. Passers reach the recruiter with a ready card and an interview task. Everyone else is marked in the ATS, silently.
5. Optional: a 5-round voice roleplay graded against a rubric.

A pile of applications turns into a short list of people worth a 15-minute interview. A human still makes every hiring decision ([reviewer SOP](../recruiting/docs/reviewer-sop.md)).

**What Claude did here:** wrote most of the Python with us, designed the scoring formula, and wrote the offline test so we could change things without messaging real candidates.

## Chapter 7. Training

Everything above became the **setter academy** ([`training/`](../training/)): 23 modules in English and Spanish (~17.5 hours), quizzes that explain *why* each answer is right, a 100-point call QA scorecard, and the 3-3-3 graduation (3 calls with your manager, 3 observed, 3 alone). The scripts and objection answers come from real recorded calls.

## Chapter 8. What went wrong (and became a rule)

Building alone with automation means your mistakes also run automatically. Two that shaped this repo:

- **An automated follow-up re-sent the same first-day email again and again to a couple of leads.** Each step sent an email and then a text; the text provider failed, the step never advanced, and the scheduler retried the whole step every few minutes, email included. Now every sender records "sent" per channel *before* moving on, never repeats a channel already marked sent, caps messages per recipient per day in code, stops a lead after repeated failures and alerts a human, and has a kill switch. We also test the failure path (provider down, out of credits, rate-limited) before going live. Ramón has these rails (`outbound_guard.py`, state saved before each send).
- **A text went to a list that included someone who had replied STOP before.** Now STOP is permanent per channel, checked before every send, and bulk sends need an explicit "go" on the final list.

These rails live in one shared module, **[`safety/`](../safety/)**, used by every sender, with offline tests that prove a failing text never re-sends the email, STOP stops everything, and caps hold. The [15-check going-live list](../safety/README.md#going-live-checklist-15-checks) came out of the same night. These rails are not optional in the code, and [CONTRIBUTING.md](../CONTRIBUTING.md) says PRs that weaken them won't be merged.

New to all this? Start with **[GETTING-STARTED.md](GETTING-STARTED.md)**.

---

## The stack

| Layer | What we use |
|---|---|
| Engineering partner | Claude (code, rules, docs, translation, review) |
| CRM / ATS | Zoho CRM, Zoho Recruit (rules mapped to GoHighLevel and HubSpot) |
| Messaging | WhatsApp Cloud API, SMS from a registered line, email |
| Team chat + alerts | Zoho Cliq |
| Speech scoring | faster-whisper, wav2vec2, SpeechBrain accent ID, LanguageTool, all local |
| Storage + talent page | Supabase (private bucket for raw video, RLS for the public page) |
| Runtime | Python 3 standard library, systemd, cron, one small server |

## Want it run for you?

The repo is everything we know. If you'd rather have us hire, train and run the team: **[book a strategy call](https://gsd500bpo.com/strategy-call?utm_source=github&utm_medium=docs&utm_campaign=open-ops)**.
