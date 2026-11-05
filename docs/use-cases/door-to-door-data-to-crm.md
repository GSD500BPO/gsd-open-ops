# Use case: door-to-door data into the CRM, so every knock keeps paying

**Persona:** a water-treatment or home-service dealer with a canvassing team that writes leads on paper sheets.
**Uses:** [`crm/cadences.md`](../../crm/cadences.md) (fields that drive automation) · [`playbooks/96-step-journey/`](../../playbooks/96-step-journey/) · [`training/curriculum/zoho-4-data-quality.md`](../../training/curriculum/zoho-4-data-quality.md)

## The story
Canvassers knock hundreds of doors a week. The sheets end up in a truck, a few hot ones get a call, and the rest are gone. Each of those doors is a homeowner who now knows your name. In the CRM, they're a list you can work for years.

## Steps
1. **One standard form** (paper or a phone form): name, address, phone, owner/renter, water source or the problem they mentioned, language, best time, consent to be contacted.
2. **Into the CRM the same day.** Use import with duplicate checks (`zoho-4-data-quality`): match on phone and address, never create a second record for the same home.
3. **Fill the fields that drive automation.** Lead type, preferred language, preferred channel, owner/renter. Set them from the conversation, not guesses.
4. **Interested now → speed-to-lead.** A setter calls within the 15-minute rule and books the in-home visit with both decision makers.
5. **Not now → the journey.** Enroll in the 96-step journey (exit rules first). The homeowner who said no in spring may need a roof in autumn.
6. **Report by street and canvasser.** Doors knocked, records created, appointments from D2D, appointments from the journey later.

## What to measure
Records created per 100 doors · duplicates rejected · % of records with language + owner/renter filled (target 90%+) · appointments from D2D records 30/90/365 days later.

## Watch
[Door-to-Door Sales Still Work. Paper Lead Sheets Don't.](https://www.youtube.com/watch?v=f3AOafUDkYc) · [6,000 Door-to-Door Leads = Local Power for Years](https://www.youtube.com/watch?v=15LUtJ5SdnI) · [The Homeowner Who Says No Buys in 3 Months](https://www.youtube.com/watch?v=Z-zg35bpQlo)
