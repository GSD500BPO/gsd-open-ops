# Role map: who's what and who's where

## The flow

```
Lead comes in ─► First contact ─► CRM record + task ─► Appointment booked ─► Team alert ─► Follow-up / nurture ─► Close ─► Commission
   (ads, web,      (setter,           (setter)           (setter, with         (chat         (setter + closer)       (closer)
   events, mail)   ≤ 5-15 min)                            both decision makers) channel)
```

Hiring runs in parallel: **Recruiter + Ramón** fill the setter seats, **Trainer** graduates them (3-3-3), **QA** keeps them sharp.

## Roles

| Role | Owns | KPIs | Where in the flow | Hands off to |
|---|---|---|---|---|
| **Ramón (bot)** | Candidate intake, WhatsApp steps, speaking score, test gate, reminders | Time to first message < 2 min; no candidate gets > 4 automated messages a day | Hiring, before any human | Recruiter (only passers) |
| **Recruiter** | Interviews, offers, onboarding paperwork, ATS hygiene | Interviews booked within 24 h of a pass; show rate; 30-day retention of hires | Hiring | Trainer |
| **Trainer / team lead** | Academy, 3-3-3 graduation, coaching | Graduation in ≤ 2 weeks; QA average of the cohort | Day 1 → graduation | Ops coordinator |
| **Appointment setter (SDR/BDR)** | First contact, discovery, booking, CRM notes and tasks, reschedules of their own bookings | 4+ qualified appointments a week (floor), 70% show rate, 90% of new leads called in ≤ 5 min | First contact → appointment → follow-up | Closer (appointment card + recording) |
| **Closer / field specialist** | The in-home visit or demo, the proposal, the close | Close rate, average ticket, outcome logged the same day | Appointment → close | Setter (follow-up tasks), account manager |
| **Ops coordinator / Scrum master** | Daily standup, the board, blockers, EOD report | Standups 5/5, no card without owner, blocked cards cleared in 2 h | Every day, every role | Manager |
| **QA supervisor** | Call scoring (100-point scorecard), pre-send checks on every email/SMS/WhatsApp | 25+ calls graded a week, every "Ugly" escalated the same day, 100% of sends checked | After every call and before every send | Trainer (coaching), manager (Ugly) |
| **CRM admin** | Fields, layouts, workflow rules, cadences, dedupe, opt-out lists | Records complete ≥ 95%, zero sends to opted-out contacts | Under the whole flow | Everyone |
| **Account manager** | The client relationship, weekly report, scope changes | Client retention, report on time | Around the flow | Manager |
| **Manager** | Approvals (nothing goes out without an explicit "send"), pricing, hiring decisions | Margin, client results | Gatekeeper of every external send | — |

## Ownership rules that keep the map honest

- The setter who booked the appointment **owns the reschedule**.
- Every lead and deal always has **one open task**. No open task = anyone may claim it.
- A task **overdue 3 business days** = the record can be claimed (only by someone who works it now) or reassigned.
- **Speed to lead**: the assigned owner has 15 minutes for first contact; after that the next person in rotation may call, with the team lead's OK.
- Two people who agree to work a lead together **share the credit**.

Details and examples: [`../crm/ownership-rules.md`](../crm/ownership-rules.md).
