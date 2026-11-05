# SCRUM and the Trello Board

You are the **human Scrum Master** of the team board. Your job: keep cards moving, unblock the team (people and AI agents) and protect your manager's time. **your manager closes deals.** Only escalate what only your manager can decide.

> North star: **"Is this making us money?"** Priority is ordered by revenue impact.

## Access (your manager does this, not you)
Your manager invites you to Trello as a normal member, creates your Zoho user (a paid seat — their decision), gives you phone-system access and a work email. Day 1: accept invites → turn on 2FA in Trello and Zoho → store everything in the password manager. **Never paste tokens or passwords into cards, comments or chats.**

## The flow

```
Backlog → Sprint (current week) → Doing → Review → We Get Sh*t Done!
                        ↘ Blocked (with written reason) ↗
```

- **Backlog:** every new, unscheduled piece of work lands here.
- **Doing:** max **2 cards per person or agent**.
- **Review:** waits for your manager's approval before anything goes to production.
- **Blocked:** always with the reason written on the card.
- If the board has no sprint list yet, propose one to your manager; until then, tag sprint cards with a "Planning" label.
- Never delete labels or lists on your own — propose cleanups to your manager.

## Card template

Title: `[Brand] Verb + concrete result` — e.g. `[GSD] Confirm this week's 3 appointments`.

```
## Objective (1 line, in money/client terms)
## Definition of Done (checklist)
- [ ] ...
- [ ] Evidence attached (link, screenshot, Zoho record ID)
- [ ] Reviewed by: ____
## Next action  <what, who, when>
## Blockers     <none | description + escalated to + date>
## Notes        <date — short update>
```

**Required on every card:** owner (label + assigned member), honest stars, value ($, $$, $$$), due date, brand.

### Star scale (do not inflate)
| Stars | Meaning | Example |
|---|---|---|
| 1 | Trivial: text or setting change | Fix a typo in a template |
| 2 | Small: one change or fix | Edit the text of a welcome PDF |
| 3 | Medium: several pieces, some integration | New Zoho view + weekly report |
| 4 | Large: new system, several components | Rebuild a full capture form |
| 5 | Major: core infrastructure, high revenue impact | Launch a new territory |

Before giving 5 stars ask: **"Is this really 5-star work?"**

## Ceremonies

| Ceremony | When | Length | Output |
|---|---|---|---|
| **Daily standup** | Mon–Fri 8:00 a.m. COT | 15 min max | Written summary |
| **Sprint planning** | Monday 8:15–8:45 | 30 min | 5–12 committed cards, ordered by $$$ |
| **Backlog grooming** | Wednesday 5:15–5:45 | 30 min | Every card has owner, stars, next action |
| **Sprint review** | Friday 4:30–5:00 | 30 min | What finished (with evidence), what waits in Review |
| **Retro** | Friday 5:00–5:15 | 15 min | 1 keep, 1 stop, 1 start |

### Standup template
```
STANDUP <date>
Yesterday: <cards moved to Done/Review>
Today: <max 2 per person/agent in Doing>
Blockers: <card → reason → who unblocks → since when>
Appointments: week __/4 min.
Manager-only: <decisions ONLY your manager can make, or "none">
```

## Rules of the game
- **Max 2 cards per person or agent in Doing.**
- **2-hour rule:** if a card in Doing shows no progress in 2 h, step in — ask, split it, or move it to Blocked with the reason.
- **Anti-loop:** do not repeat the same info or retry an approach that already failed. Change approach or escalate.
- **Review is mandatory** before production. Your manager approves.
- **Everything external needs your manager:** sends, posts, ads, payments, contracts, phone credits, account creation.
- When a card finishes it goes to Review → you pull the next sprint card.
- **AI agents** are addressed only through the team's agent dashboard, never through side channels.

## Definition of Done
A card moves to **We Get Sh\*t Done!** only if:
1. The whole checklist is ticked.
2. **Evidence** is attached (link, screenshot, Zoho ID, log). "It's done" is not evidence.
3. Someone other than the author **verified it live**. AI self-reports alone do not count.
4. Anything external has your manager's **explicit approval** recorded on the card (date + text of the OK).
5. The CRM is updated (status, note) if the task touches leads or clients.
6. Stars and value were re-checked at close.
7. Anything left over became a new Backlog card, linked.

## Your first 2 weeks
| Day | Task |
|---|---|
| Day 1 | Accept invites. Read this module and the CRM and QA modules. Observe the board without moving anything. |
| Day 2 | First standup. Inventory the Blocked list: card, owner, reason, age. |
| Day 3 | Propose to your manager **in one message**: what to archive, what to revive, what needs his decision. |
| Day 4 | Apply what was approved. Make sure every Backlog card has owner, stars and $. |
| Day 5 | First sprint review + retro. Propose the sprint list and duplicate-label cleanup. |
| Week 2 | Repeat the full cycle. Extend grooming to client boards (one per day). |
