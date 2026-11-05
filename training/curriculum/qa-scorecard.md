# QA Scorecard and Pre-Send Checklists

Every active campaign (GSD outbound, client campaigns, and any other GSD campaign) gets QA. You grade calls, check data, and stop any send that is not ready.

## 1. What you QA and how often

| QA type | What you check | Frequency |
|---|---|---|
| **Calls** | A sample of recorded calls, graded with the scorecard below | Daily (min. 5 calls) |
| **CRM data** | Required fields, correct Lead Status, notes, duplicates, language, opt-outs marked | Daily (today's records) + weekly (full view) |
| **Email before send** | Spelling, language, merge tags, sender, client design, no placeholders, no unapproved links, no lead-source mention | Before **every** send or new template |
| **SMS before send** | Correct line, full STOP history, 14-day suppression, correct brand, second "go" | Before **every** bulk send |
| **Automations** | Workflows fired, webhooks OK, no duplicate sends | Daily |

## 2. Call scorecard (100 points)

| # | Criterion | Points | What we expect |
|---|---|---|---|
| 1 | Opening | 10 | Greeting, name, correct company/brand, reason for the call in under 15 s. Smile in the voice. |
| 2 | Permission and rapport | 10 | Uses the prospect's name (3 times), asks if it is a good time, matches their pace. |
| 3 | Discovery | 20 | Open questions: problem, situation, who decides, urgency. Pauses and listens. |
| 4 | Objection handling | 15 | Agree → empathize → redirect. Never argues. Uses the playbook answers. |
| 5 | Appointment close | 20 | Offers two time options, confirms date, time (lead's zone), address and who will be there. |
| 6 | Compliance and brand | 15 | Does not reveal the lead source, no unauthorized prices, respects "no", correct language, no false promises. |
| 7 | CRM logging | 10 | Full note with handoff checklist, status updated, follow-up task created in ≤ 10 min. |
| | **Total** | **100** | |

### Bands
- **Good (85–100):** the call books or advances. Save it as a training example.
- **Bad (60–84):** fixable mistakes. Write 1–2 specific things to improve.
- **Ugly (< 60 or any critical fail):** compliance, brand or client risk. **Escalate to your manager the same day.**

### Critical fails (automatic Ugly)
- Revealing where leads come from.
- Giving a price without authorization.
- Ignoring a "don't call me" or STOP.
- Lying or offering something that does not exist.
- Disrespecting the prospect.
- Booking without confirming address and time.

## 3. Pre-send checklist — email (60 seconds)
- [ ] Correct brand and client design
- [ ] Correct language (Spanish leads get Spanish)
- [ ] Correct sender name and address
- [ ] Merge tags tested against a real record; no empty `${...}`
- [ ] No placeholders left (e.g. a fake postal address in the footer)
- [ ] No new, unapproved links or domains
- [ ] No mention of where the lead came from
- [ ] Review copy sent to your manager → your manager's explicit "ok" recorded

## 4. Pre-send checklist — SMS
- [ ] Sent from the company's registered **10DLC texting line** — the other line is calls-only
- [ ] Full message history checked for every number: anyone who **ever** said STOP / ALTO / unsubscribe is removed
- [ ] Anyone texted from the registered texting line in the **last 14 days** is removed
- [ ] CRM opt-outs removed
- [ ] Brand confirmed (it must be the brand your manager named — if in doubt, ask)
- [ ] Sending window 8 a.m. – 8 p.m. in the lead's time zone
- [ ] Final list shown to your manager → **second explicit "go"** recorded

Choosing a plan ("let's go with option A") is **not** approval to send. Every send needs its own OK.

## 5. When to escalate to your manager (and when not)
**Escalate:** money decisions, contracts, any send or publication, live changes, Ugly calls, incidents with a real lead, new access or licenses.

**Don't escalate:** technical problems you can solve, moving cards, cleaning data without deleting anything, questions this academy already answers.

**How:** try to solve it first, then escalate **in one clear message** — what happened, what you already tried, and what decision you need.

**If you made a mistake:** say it first, plainly, then explain what is running now. Hiding a mistake is worse than the mistake.
