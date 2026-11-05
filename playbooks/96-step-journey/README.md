# 96-Step Year-Round Prospect Journey (free CRM journey template)

A 365-day email + SMS nurture for every lead that saw your offer and didn't buy. 4 phases (one per season / trade) × 3 chapters × 8 steps = 96 steps.

| Phase | Days | Trade (example) | Chapters |
|---|---|---|---|
| 1 | 1-90 | Water treatment (your core product) | Health & Family · Money & Savings · Re-Engagement & Final Push |
| 2 | 91-180 | Roofing, solar & storm restoration | Energy Bills & Solar · Roof Protection & Storm Restoration · Final Close & Transition |
| 3 | 181-270 | Windows & doors | Comfort & Energy · Home Value & Security · Final Close & Transition |
| 4 | 271-365 | HVAC & indoor air | Air Quality & Health · Efficiency & Savings · Final Push & Long-Term Loop |

Day 1 = the day after the last negotiation touch (NEG-6) with no close. The JSON also contains the 6-step negotiation series that comes before it.

| File | Use |
|---|---|
| `GSD-96-Step-Year-Round-Prospect-Journey.pdf` | Read and share (11 pages) |
| `96-step-journey.csv` | Import: `step, step_id, phase, phase_trade, chapter, chapter_name, day_offset, channel, subject_or_theme, angle, goal, tag` |
| `96-step-journey.json` | Automation: steps + `negotiation_series`, `merge_fields`, `phases`, `exit_rules` |

Video walkthrough: [The 96-Step CRM Journey That Sells All Year](https://www.youtube.com/watch?v=fA0oPEkFEo4).

## How to use
1. **Exit rules first** (in the JSON): STOP/unsubscribe ends everything and sets Do Not Contact; any reply pauses the journey and goes to a live rep; interest in a new trade opens a new deal; no mobile = skip SMS; step tag present = skip.
2. Create the merge fields: `{First_Name} {City} {Zip} {Rep_Name} {Company} {Visit_Notes} {Monthly_Cost_Current} {Annual_Cost} {Quote_Amount}`.
3. Write each step's message from its `subject_or_theme` + `angle` (the file gives the brief, you write the copy in your voice).
4. Build it as a scheduled workflow keyed on `day_offset`; tag every send with `tag` so nothing repeats.
5. Test on internal contacts before enrolling a single real lead.

## How to adapt
Swap phase trades for your partners or your own product lines; keep the 8-step chapter rhythm (educate → connect → engage → offer).
