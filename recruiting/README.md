# Recruiting: Ramón, the WhatsApp recruiting bot with automated candidate scoring

Ramón screens call-center candidates (SDR/BDR, appointment setters) end to end, so your recruiters only talk to people who already proved they can speak English on the phone. It's how a large pile of applications becomes a short list worth interviewing: every applicant gets the same steps, the same test and the same scoring, and nobody on your team spends time on the ones who never send the video or fail the English bar.

**Use case:** [100 applicants → a top 10 to interview](../docs/use-cases/recruiting-100-to-top-10.md)

```
Meta ad / lead form / apply page
        │
        ▼
 intake ──► ATS candidate (Zoho Recruit) + WhatsApp steps + email
        │
        ▼
 candidate sends a 1-minute English video on WhatsApp
        │   stored in a PRIVATE bucket, attached to the ATS record
        ▼
 speaking score (100% local: Whisper + wav2vec2 + accent ID + LanguageTool)
        │
        ▼
 prequal test on your site: English + Sales + Typing  ──►  intake_server.py
        │
        ▼
 optional: 5-round voice roleplay (WhatsApp voice notes or the web page)
        │
        ▼
 gate: composite ≥ 65 AND English ≥ 70 AND video AND speaking ≥ 60
        │
   pass ├──► team chat card + ATS "Qualified" + interview task for your recruiter + "you passed" on WhatsApp
        │    + public talent profile ONLY after the candidate replies YES (consent)
   fail └──► ATS "Unqualified", silent (no rejection spam)
```

| Folder | What |
|---|---|
| `ramon/` | The bot and pipeline (Python; the core needs only the standard library) |
| `assessment/` | The prequal test: `prequal-test.json` (questions + scoring), `prequalTests.ts` (React/TS module), `index.html` (stand-alone page) |
| `docs/` | How to read the speaking score, the reviewer SOP, WhatsApp cost rules, privacy and consent |

## Files in `ramon/`

| File | Job |
|---|---|
| `talent.py` | The pipeline: intake, WhatsApp, email, Zoho Recruit, Supabase storage, the pass/fail gate, follow-ups, digest. CLI: `run`, `score`, `rescore`, `digest`, `rpscore`, `rpstart`, `status` |
| `wa_webhook.py` | WhatsApp Cloud API webhook (signature check, de-dup, routes candidate messages to `talent.on_wa`) |
| `intake_server.py` | Receives test results from the apply page and serves the web roleplay |
| `speech_score.py` | Local speaking scorer: clarity, fluency, grammar, accent → 0-100 + CEFR estimate |
| `roleplay.py`, `rp_web.py`, `rp_transcribe.py`, `roleplay.html` | 5-round voice roleplay (WhatsApp or browser), graded with a regex rubric + speaking score |
| `scenarios/*.json` | Roleplay scripts: `water_treatment` (default), `storm_restoration`. Copy one to make your own |
| `hire_alert.py` | Alerts the team when a company clicks "Hire" on your public talent page |
| `client_share.py`, `client_ats_mirror.py` | Optional (off by default): share passers with a client's chat or ATS, never with phone/email/rates in the chat |
| `outbound_guard.py` | Per-recipient daily caps + kill switches for every automated email |
| `cliq.py` | Minimal Zoho Cliq client |
| `deploy/` | systemd units + crontab example |
| `tests/test_offline.py` | Dry end-to-end test, no network |

## Quick start

```bash
cd recruiting/ramon
cp .env.example .env && chmod 600 .env          # fill in what you use; TALENT_LIVE stays 0 for now
python3 tests/test_offline.py                   # dry flow, no network: should print "OK 10 checks"

# speaking scorer (CPU, ~1.5 GB RAM peak, ~30 s per 1-minute clip)
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python speech_score.py some-intro-video.mp4     # JSON with the scores

# services
.venv/bin/python wa_webhook.py      # :8787, put it behind TLS and register it in your Meta app
.venv/bin/python intake_server.py   # :8788, your apply page POSTs here
crontab deploy/crontab.example      # after editing the path
```

Going live, in this order:
1. Run with `TALENT_LIVE=0` for a day and read `events.jsonl`: every message it *would* have sent is there.
2. Set `TALENT_LIVE=1` with `TALENT_ALLOW=<your own number>` and walk through the whole flow on your own phone.
3. Remove `TALENT_ALLOW`. Keep `TALENT_WA_DAILY_CAP` at 4 or less.

## Configuration

Everything is in `.env` (see `.env.example`, every key is commented). Nothing is hard-coded: company name, bot name, role, WhatsApp templates, thresholds, buckets, channels and ATS ids all come from config. Several openings at once: copy `jobs.example.json` to `jobs.json`.

WhatsApp templates you need approved in Meta (names are configurable):
- `recruiting_steps_en`: `Hi {{1}}! ... Step 1: send a 1-minute video in English here. Step 2: take the test: {{2}}`
- `recruiting_welcome_en`: `Hi {{1}}! Thanks for applying ...` (fallback)
- `recruiting_reminder_en`: `Hi {{1}}, we're still waiting for your 1-minute English video ...`

Supabase: a **private** bucket for raw videos/CVs (`TALENT_VIDEO_BUCKET`), and public buckets for consented reels and stills. The public page reads a `talent_profiles` table (RLS: public sees `status='approved'` only). Schema notes: [`../crm/talent-data-schema.md`](../crm/talent-data-schema.md).

## Safety rails (keep them)

- **Dry by default.** `TALENT_LIVE=0` logs instead of sending.
- **Caps.** Max `TALENT_WA_DAILY_CAP` automated WhatsApp messages per candidate per day; `outbound_guard.py` caps email per recipient; `touch guard/PAUSE_ALL` stops everything.
- **Idempotent.** State is written *before* each send (`passed`, follow-up flags, hire alerts), so a crash or a double cron run never repeats a message.
- **STOP means stop.** "stop / unsubscribe / baja" sets `stage=stopped` and nothing else is ever sent.
- **Consent before public.** Nobody appears on a public page until they reply YES. Public URLs use a salted hash (`TALENT_REEL_SALT`), never the phone number.
- **Clients never see contact data or pay.** The client share shows an alias + scores only and rejects templates that contain rates.
- **Anti-SSRF.** The scorer only downloads videos from your own Supabase storage.

## How to adapt it

- **Your company and role:** `TALENT_COMPANY`, `ROLE_TITLE`, `PAY_LINE`, `CAMPAIGN_BLURB`, bot name, WhatsApp display/link: all in `.env`. Several openings: `jobs.json`.
- **Your bar:** `TALENT_PASS_COMPOSITE`, `TALENT_PASS_ENGLISH`, `TALENT_PASS_SPEAKING`. Calibrate on 10+ known candidates first ([how](docs/speaking-score.md#calibrate-before-you-move-the-bar)).
- **Your test:** edit [`assessment/prequal-test.json`](assessment/) (questions, typing sample, weights).
- **Your roleplay:** copy `ramon/scenarios/water_treatment.json` to `<your_trade>.json` and change the persona, the 5 rounds and the regex rubric.
- **Another ATS** (not Zoho Recruit): the ATS calls are grouped in `talent.py` (`recruit_*` functions). Replace them; the gate and the WhatsApp flow don't change.
- **No public talent page:** leave the Supabase public buckets unset; the pipeline still works without it.

## Related
- Train the people you hire: [`../training/`](../training/)
- The data the pipeline writes: [`../crm/talent-data-schema.md`](../crm/talent-data-schema.md)
