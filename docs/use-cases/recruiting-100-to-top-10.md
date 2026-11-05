# Use case: 100 appointment-setter applicants → a top 10 worth interviewing

**Persona:** a small BPO (or a dealer building an in-house desk) that posts a job for bilingual appointment setters and gets far more applications than one recruiter can call.
**Uses:** [`recruiting/`](../../recruiting/) · [`recruiting/docs/speaking-score.md`](../../recruiting/docs/speaking-score.md) · [`recruiting/docs/reviewer-sop.md`](../../recruiting/docs/reviewer-sop.md)

## The story
A job post for setters fills up fast. Most applicants never finish anything; some can't hold a conversation in English; a few are great. Calling all of them takes a week, and the great ones accept another offer in the meantime. The goal is a funnel where every applicant gets the same steps within minutes, and the recruiter only sees people who already proved they can do the job.

## Steps
1. **Intake in minutes.** Applications from your job ad, lead form or apply page create an ATS record and a WhatsApp message with the steps (`recruiting_steps_en` template), plus an email with the test link.
2. **Step 1: a 1-minute English video on WhatsApp.** Stored privately, attached to the ATS record.
3. **Automatic speaking score, on your own server.** `speech_score.py` returns clarity, fluency, grammar, neutral accent, an overall 0-100 and a CEFR estimate. No paid APIs.
4. **Step 2: the prequal test.** English + Sales + Typing; composite = 0.45 English + 0.35 Sales + 0.20 Typing.
5. **The gate.** Composite ≥ 65 **and** English ≥ 70 **and** video sent **and** speaking ≥ 60. Pass → card in the recruiting channel, ATS "Qualified", interview task for the recruiter, "you passed" on WhatsApp. Fail → ATS "Unqualified", no rejection spam.
6. **Reminders, capped.** No video after 24 h → one reminder, then at most two more inside WhatsApp's free window. STOP is permanent.
7. **Optional roleplay.** 5 voice rounds from a scenario file, graded with a rubric + the speaking score.
8. **Human interview (15 min).** The reviewer SOP's checklist: same person as the video, one unexpected question, a 2-minute live roleplay, logistics.

## How the 100 becomes 10
Each step removes a different kind of no-fit: people who never act (no video), people who can't speak to US customers (speaking < 60), people who can't write or reason through a sales situation (test). The thresholds are environment variables; calibrate them on 10+ candidates you already know before moving them. The ratio you get depends on your ad and your bar; the point is that the recruiter's time goes only to people who cleared all three.

## What to measure
Time from application to first WhatsApp (target < 2 min) · % who send the video · pass rate per gate · interview-to-hire rate · 30-day retention of hires.

## Watch
[Slow to Hire, Quick to Fire: A Fortune 500 Rule for Sales Teams](https://www.youtube.com/watch?v=gnPa9QbbgPA)
