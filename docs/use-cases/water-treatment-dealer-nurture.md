# Use case: a water-treatment dealer stops losing the homeowners who said "not now"

**Persona:** an independent water-treatment dealer. Two field specialists, one office person, a CRM full of homeowners who had a free in-home water analysis and didn't buy.
**Uses:** [`crm/cadences.md`](../../crm/cadences.md) · [`playbooks/96-step-journey/`](../../playbooks/96-step-journey/) · [`training/curriculum/call-objections.md`](../../training/curriculum/call-objections.md)

## The story
Most of the dealer's demos end the same way: "We need to think about it." The specialist promises to follow up, a busy week happens, and the homeowner hears from a competitor first. The dealer doesn't need more leads. They need a system for the ones they already paid for.

## Steps
1. **Log the visit properly.** Same day: outcome, the real monthly cost the homeowner is paying today (`{Monthly_Cost_Current}`), the quote (`{Quote_Amount}`), and notes from the visit (`{Visit_Notes}`). These are the merge fields the journey uses.
2. **Run the post-appointment cadence.** A follow-up task every 2-3 days up to at least FU-6 (reschedule, negotiation, financing). Each touch is a numbered note.
3. **Negotiation series (NEG-1 to NEG-6).** The JSON ships six steps that use the visit math: what they really spend today, break-even, local social proof, and so on.
4. **No close after NEG-6 → Day 1 of the 96-step journey.** Phase 1 (days 1-90) stays on water: health and family, then money and savings, then a final push.
5. **Exit rules on.** Any reply pauses everything and creates a task for a human. STOP ends every sequence and the contact is never re-enrolled automatically.
6. **Phases 2-4.** If the dealer has partners (or sells other products), the journey moves to the next big-ticket need as the year goes on. If not, end at step 24 and loop Phase 1 with new angles.

## What to measure
Replies per 100 enrolled · appointments rebooked from the journey · STOP rate per step (a step with high STOP gets rewritten) · records with an open task (should be 100%).

## Watch
[The 96-Step CRM Journey That Sells All Year](https://www.youtube.com/watch?v=fA0oPEkFEo4) · [Lead Follow-Up System: the 3-Day / 5-Day Cadence](https://www.youtube.com/watch?v=Kh7rtd2DobQ)
