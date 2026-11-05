# CRM: sales cadence templates, ownership rules and schema

The rules that keep leads from going cold on a small sales floor: speed to lead, one open task per record, the 3-day / 5-business-day follow-up cadence, numbered contact attempts (TA-1..TA-4), post-appointment follow-ups (FU-1..FU-6) and who owns what.

Written for Zoho CRM (and Zoho Recruit for hiring), but every rule maps to HubSpot, GoHighLevel or Salesforce: you need tasks with due dates and owners, a stage field, notes, and tags.

| File | What |
|---|---|
| `ownership-rules.md` | The team rules: speed to lead, one open task, 3-day overdue rule, who reschedules, shared credit |
| `cadences.md` | First-contact attempts (TA-1..TA-4), the 3-day / 5-business-day cadence, post-appointment FU-1..FU-6, nurture, required fields |
| `talent-data-schema.md` | Recruiting data: ATS statuses and tags, pipeline state, and the Supabase tables behind the public talent page |

## How to use it

1. Read [`ownership-rules.md`](ownership-rules.md) with your team and agree on it out loud. The rules only work if everyone logs every touch.
2. Build the fields first: lead type, preferred language, preferred channel, owner/renter, best time to call, opt-outs per channel.
3. Turn [`cadences.md`](cadences.md) into automation: a workflow rule that creates the next task (3 days after a conversation, 5 business days without one), a report of records with **no open task**, and a report of tasks **overdue 3+ business days**.
4. Audit weekly per record: numbered notes present · next task dated and owned · stage matches the last note · required fields filled.

## How it maps to other CRMs

| Concept | Zoho CRM | GoHighLevel | HubSpot |
|---|---|---|---|
| Numbered attempt (TA-1...) | Note | Note | Note / logged call |
| Next task + reminder | Task with reminder | Task | Task with reminder |
| Stage | Lead Status / Deal Stage | Pipeline stage | Lifecycle / Deal stage |
| Automation | Workflow rules, Blueprint | Workflows | Workflows / Sequences |
| Journey enrolment marker | Tag | Tag | List / property |
| Opt-out per channel | Checkbox fields | DND per channel | Communication preferences |

Use case: [CRM-agnostic setup](../docs/use-cases/crm-agnostic-setup.md).
