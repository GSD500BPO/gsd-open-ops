# Prequal assessment: English + Sales + Typing test

The test every candidate takes after the WhatsApp welcome.

| File | What |
|---|---|
| `prequal-test.json` | 10 English questions, 6 sales-judgement questions, a typing sample and the scoring rules |
| `index.html` | Stand-alone test page. Set `INTAKE` to your `intake_server.py` URL; results are POSTed as JSON |
| `prequalTests.ts` | The same questions as a React/TypeScript module for your own site |

**Scoring** (from the JSON): `composite = 0.45 × english + 0.35 × sales + 0.20 × typing`. Pass = composite ≥ 65 **and** English ≥ 70. Tiers: 1 (< 65), 2 (≥ 65), 3 (≥ 85).

## How to use
Host `index.html` + `prequal-test.json` on any static host (same folder), point `INTAKE` at your intake server, and put the link in the WhatsApp template.

## How to adapt
Write sales questions about your own calls ("the prospect says send me an email..."). Keep the questions in English if the job is in English. Change weights in the JSON and in `talent.py` together.
