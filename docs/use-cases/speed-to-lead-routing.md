# Use case: speed-to-lead alerts and smart routing to appointment setters

**Persona:** a home-service company whose inbound leads (web form, call-in, events) land in the CRM and wait hours for a call.
**Uses:** [`crm/ownership-rules.md`](../../crm/ownership-rules.md) · [`crm/cadences.md`](../../crm/cadences.md) · [`training/role-map.md`](../../training/role-map.md) · [`training/sop-templates/approval-gate.md`](../../training/sop-templates/approval-gate.md)

## The story
The lead filled the form at 7:42 p.m. The first call came the next afternoon, after a competitor had already booked them. The fix is not "call faster" on a sticky note. It's an automatic first touch, an alert to a named owner, a clock, and a rule for what happens when the clock runs out.

## Steps
1. **Instant first touch.** On lead creation: a same-minute email + text from your registered line ("got your request, {Rep_Name} will call you shortly"), inside quiet hours (8 a.m.-8 p.m. recipient time).
2. **Route to an owner.** Leads rotate between setters. Route by the fields you already have: preferred language (Spanish leads to a Spanish-speaking setter), trade, territory.
3. **Alert the owner.** Push the lead to the team chat or the setter's phone with name, need and a one-tap call link. The owner has **15 minutes** (5 is the target).
4. **Escalate.** After 15 minutes with no logged attempt, the next setter in rotation may call, with the team lead's OK. No silent waiting.
5. **Log and task.** Every attempt is a numbered note (TA-1...TA-4); 3 touches in 48 hours; the record always has one open task.
6. **Score the warm ones.** Opens, clicks and especially replies raise a lead score; above a "hot" threshold, a human gets an alert to call now instead of waiting for the next cadence step.
7. **Guardrails.** Per-recipient daily caps, the "sent" marker written before sending, a kill switch, and STOP honored on every channel.

## What to measure
Minutes from lead to first call (median and 90th percentile) · % of leads called in ≤ 5 min · leads with no open task (target 0) · contact rate on TA-1.

## Watch
[Lead Follow-Up System in Zoho CRM: The 3-Day / 5-Day Cadence](https://www.youtube.com/watch?v=Kh7rtd2DobQ) · [AI Call QA: Grading Sales Calls Against the Script](https://www.youtube.com/watch?v=KBes7gWhChM)
