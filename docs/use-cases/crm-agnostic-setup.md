# Use case: the same playbook on Zoho CRM, GoHighLevel or HubSpot

**Persona:** an agency or ops lead who has to set this up for teams on different CRMs.
**Uses:** [`crm/README.md`](../../crm/README.md) (mapping table) · [`crm/ownership-rules.md`](../../crm/ownership-rules.md) · [`playbooks/96-step-journey/96-step-journey.csv`](../../playbooks/96-step-journey/96-step-journey.csv)

## The story
Rules that live in one tool's vocabulary die when the client uses another. These rules only need five things that every CRM has: records with an owner, a stage, notes, tasks with due dates, and tags.

## Steps
1. **Fields.** Create: lead type, preferred language, preferred channel, owner/renter, best time to call, and one opt-out flag per channel (email, SMS, WhatsApp). In GoHighLevel, channel opt-outs map to DND; in HubSpot, to communication preferences.
2. **Stages.** New → Contacted (TA-n) → Appointment set → Visited → Negotiation → Closed won/lost → Prospect Journey phase 1-4 → Long-Term Prospect / Do Not Contact.
3. **Task automation.** After a call outcome: next task in 3 days (conversation) or 5 business days (none). Zoho: workflow rule; GoHighLevel: workflow "add task"; HubSpot: workflow "create task".
4. **Two reports that run the floor.** Records with no open task; tasks overdue 3+ business days. These are the "claimable" lists from the ownership rules.
5. **Journey import.** Import the CSV as a reference sheet; build one workflow per phase with waits from `day_offset`; add `tag` on every send; check "tag already present → skip".
6. **Exit rules as triggers.** Reply received → remove from workflow + task to owner. STOP → Do Not Contact + remove from all workflows.
7. **Test with internal contacts** and read every rendered message before enrolling anyone.

## What to measure
Same KPIs on every CRM: speed to lead, records without an open task, overdue tasks, journey replies. If two CRMs can't produce the same report, the setup isn't done.
