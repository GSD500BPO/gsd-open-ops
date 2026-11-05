# How to read the speaking score

When a candidate sends the 1-minute English video, `speech_score.py` listens to it on your own server (no paid APIs) and scores it. Typical time: 20-60 seconds.

A candidate reaches the team channel only if all three are true:
1. Prequal test: composite ≥ 65 and English ≥ 70 (`TALENT_PASS_COMPOSITE`, `TALENT_PASS_ENGLISH`).
2. They sent the video.
3. Speaking ≥ 60 out of 100 (`TALENT_PASS_SPEAKING`).

Below the speaking bar: the ATS status becomes "Unqualified" and the candidate gets **no** message (same as a failed test).

## What each number means (0-100)

| Score | What it measures | How to read it |
|---|---|---|
| **Speaking (overall)** | 35% clarity + 25% fluency + 25% grammar + 15% neutral accent | This one decides. 60+ passes. |
| **CEFR** | Rough level: C1 (85+), B2 (75+), B1 (60+), A2 (45+), A1 | B2/C1 = can handle U.S. customers. B1 = understandable, watch the video. |
| **Clarity** | Whether two independent speech recognizers (one trained only on native English) hear the same words | 80+ very clear. Under 50: a U.S. customer will ask them to repeat. |
| **Fluency** | Speed (ideal 110-170 words per minute), pauses, fillers (um, uh, este, pues, bueno) | Under 90 wpm = slow or stuck. Pauses over 25% = thinking a lot. |
| **Grammar** | Grammar errors per 100 words (LanguageTool) | 0-1 per 100 words = very good. 3+ = "I am work", "he don't". |
| **Accent** | Which English accent it sounds closest to, with confidence | A hint only. The model has **no Latin American class**, so it sometimes says "us" or "philippines". |
| **Neutral** | How U.S./Canada-neutral it sounds, but **never higher than clarity** | High = the customer won't notice the accent. |

**Flags**
- `too_short`: under 40 words. The score is scaled down. Ask for a longer video.
- `not_english:xx`: spoke another language. Score capped at 25.
- `grammar_unreliable`: audio too garbled to judge grammar (grammar capped at 50).
- `accent_failed` / `grammar_failed`: that part failed technically; the score uses the rest.

## The formulas (constants at the top of `speech_score.py`)

- clarity = 0.35 × Whisper word confidence + 0.25 × wav2vec2 frame confidence + 0.40 × agreement (1 − WER between the two transcripts)
- fluency = 0.40 × rate + 0.35 × pauses (gaps > 0.25 s, ≤ 15% ideal) + 0.25 × fillers/repetitions, −5 per pause > 1.5 s
- grammar = 100 − 15 × errors per 100 words
- neutral accent = min(clarity, accent mass: US/Canada × 1.0 + other native × 0.6)
- overall × (words/40) if under 40 words; capped at 25 if Whisper hears another language

## When NOT to trust the machine (override)

The score is an aid, not a judge. A human decides when:
- **Noise or a bad recording** (street, music, bad mic): clarity drops even if they speak well. Ask for a new video in a quiet place.
- **Too short**: ask for 45-60 seconds.
- **Reading a script**: can score high. Ask an unexpected question in the interview.
- **Strong accent but fully understandable** and good grammar: may fit Spanish or bilingual campaigns.
- **Just under the bar (55-59)** and you think they're good: watch the video, and if you approve, change the ATS status to "Qualified" yourself. Always leave a note saying **why**.

## Calibrate before you move the bar

Run the CLI on 10+ known-good and known-bad candidates and look at the spread before changing `TALENT_PASS_SPEAKING`. Synthetic check clips: a native TTS voice should land around C1, a TTS voice reading ungrammatical text around B2, and a Spanish-accented robot voice around A1.
