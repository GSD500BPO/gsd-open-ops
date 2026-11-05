# Use case: a roofing and restoration company pivots its list when the season changes

**Persona:** a home-service company that does roofing and storm restoration, plus some windows and HVAC work through partners. Busy after storms, quiet in between.
**Uses:** [`playbooks/96-step-journey/96-step-journey.json`](../../playbooks/96-step-journey/96-step-journey.json) · [`crm/cadences.md`](../../crm/cadences.md) · [`recruiting/ramon/scenarios/storm_restoration.json`](../../recruiting/ramon/scenarios/storm_restoration.json)

## The story
After a storm, every homeowner on the list is a roofing lead. Three months later the same list goes cold, and the company starts buying new leads. The homeowners didn't disappear; the offer just stopped matching their season. One list, worked all year, beats a new list every quarter.

## Steps
1. **Tag what you know.** Owner or renter, roof age if known, the trades they asked about, preferred language and channel. These fields decide which phase makes sense.
2. **Reorder the phases.** The JSON's phases are slots ("Trade A: your core product", "Trade B: the next big-ticket need"...). For this company: roofing/storm first, then windows & doors, then HVAC before the hot months, and back.
3. **Use the "Final Close & Transition" chapters.** Each phase ends with a chapter that closes the current offer and introduces the next one, so the switch doesn't feel random to the homeowner.
4. **New interest = new deal.** When a homeowner replies about a different trade, the exit rule opens a new deal for that trade and pauses the journey. A human calls.
5. **Staff for the spike.** Before storm season, run the recruiting bot with the `storm_restoration` roleplay so new setters are screened on the actual call they'll make.

## What to measure
Appointments per month across the year (flatter is better) · deals opened per trade from the same list · cost per appointment from the existing list vs. new leads.

## Watch
[If Construction Slows, Pivot to Roofing: One List, All Year](https://www.youtube.com/watch?v=DxzOIK23i7k) · [Your Lead Data Lets a Home-Service Business Pivot Any Season](https://www.youtube.com/watch?v=kcgDKAA_zLM)
