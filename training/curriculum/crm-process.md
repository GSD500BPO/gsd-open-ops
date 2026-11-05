# CRM Process and Automation (Zoho)

The CRM is the single source of truth. **If it is not in Zoho, it did not happen.** Without a log, automations misfire and someone else calls the same lead again.

## 1. Log every call
- Use **Log a Call** (or a note) on the record **as the call happens**, then update the status.
- The note carries the full handoff checklist when an appointment is booked: verified name and phone · address · date and time (lead's time zone) · who will be present · main problem · language · owner or renter · special notes.
- Create the follow-up task within 10 minutes of the call.
- Keep **Lead Status** current at all times. On some campaigns, moving a lead to *Contacted* is what stops the automatic sequence — so a missed status update means the lead keeps getting automated messages.

## 2. Duplicates: match on phone or email, never on name
- Search duplicates by the **last 10 digits of the phone number** or by **email**.
- **Never match by name.** Many people share a name; in one real cleanup, out of 130 same-name groups only 1 was a true duplicate.
- Zoho merges are **irreversible** and take at most 3 records at a time. Run de-duplicate in review mode, and if there is any doubt, ask your manager before merging.

## 3. Opt-outs the same day
- STOP / ALTO / "remove me" / "don't call" → mark **Email Opt-Out** and add the note "SMS opt-out" **that same day**.
- On a call: "Understood, I'll remove you right now." Hang up and mark do-not-contact before your next dial. No second pitch.

## 4. Do not build parallel objects
Do **not** create new rules, templates, fields or views unless asked. If your manager is editing something and sends you the link, fix **that** object. Duplicates blind the person building the system.

## 5. Field model basics
- Always filled: **Lead Source, Lead Status, Owner**, plus the master industry field that drives the views.
- Appointment fields (who set it, when, for whom) live in their own section — fill them every time.
- Language is a field, not a guess: Spanish leads get Spanish journeys and Spanish messages.

## 6. Email templates: never mix the sets
| Set | When to use |
|---|---|
| **Cold** | First outreach to someone we have never spoken to. |
| **Warm drip** | Nurture tips for leads already in a journey. |
| **Post-call ("Great connecting…")** | **Only after a real conversation.** |

Sending "great talking to you" to someone who never talked to us is a serious mistake.

## 7. Automation logic you act on (you don't operate it)
- **Attempt sequences** advance when Lead Status changes — so the status you set drives what the lead receives next.
- **Engagement scoring:** opens, clicks and replies add points. High score = call first, and mention you noticed their interest without saying how you know.
- **Hot-lead assignment** and **round-robin** routing send leads to whoever is on shift (Colombia time).
- Your job is **not** to edit these rules. Your job is to **act fast when the hot-lead notification arrives** and to **report** when something did not fire.

### Daily automation check
- A new lead should show its first (Day 0) email in the record's **Emails** tab within **5 minutes**.
- If it does not: check the rule is ACTIVE, the lead has an email, and the language/partner fields are right. Then tell your manager **with the lead's name** and what was or was not received.

## 8. Lead source is confidential
To a client or dealer you hand over only: name, phone, email, address/city/ZIP, language and call notes. **Never** the lead description, form or campaign names. If asked: "our hybrid lead engine" — and stop there.

## 9. Verify before you report
Open the record, look at the sent email, check the status yourself. Reports from AI tools or from other people are self-reports, not proof. Anything you could not check is reported as **UNVERIFIED**.
