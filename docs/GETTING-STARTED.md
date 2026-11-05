# Getting started (no technical background needed)

This guide walks you through GSD Open Ops in order. You can stop after any step and still have something useful.

**You will need:** a computer with Python 3.9 or newer (Mac and Linux have it; on Windows, install it from python.org), a terminal window, and about one hour.

**Nothing in this guide sends a real message.** Everything runs in "dry run" mode, which only prints what *would* happen. Going live is a separate, deliberate step at the end.

---

## Step 0. Get the files

```bash
git clone https://github.com/GSD500BPO/gsd-open-ops.git
cd gsd-open-ops
```

No git? On the GitHub page, click **Code > Download ZIP**, unzip it, and open a terminal in that folder.

Check that everything works:

```bash
python3 -m unittest discover -s journeys/24-step/tests
python3 -m unittest discover -s alerts/tests
python3 -m unittest discover -s data-pipeline/tests
```

Each one should end with `OK`.

---

## Which folder first?

| If you want to... | Start with | Time |
|---|---|---|
| Write down how your team follows up | [`crm/`](../crm/) (rules, no code) | 30 min reading |
| Build a clean list of businesses to call | [`data-pipeline/`](../data-pipeline/) | 15 min |
| Know the minute a lead comes in or replies | [`alerts/`](../alerts/) | 15 min |
| Follow up automatically for 90 days | [`journeys/24-step/`](../journeys/24-step/) | 30 min |
| Hire and screen setters | [`recruiting/`](../recruiting/) | 1 hour |
| Train setters | [`training/`](../training/) | read at your pace |

The usual order for a sales team is: **rules, then list, then alerts, then journey.** Rules first, because every automation just enforces a rule. Alerts before the journey, because a journey creates replies, and replies need a human fast.

---

## Step 1. Rules (no code)

Read [`crm/cadences.md`](../crm/cadences.md) and [`crm/ownership-rules.md`](../crm/ownership-rules.md). Decide your numbers:

- How fast must a new lead be called? (We use 15 minutes.)
- When is the next follow-up due? (We use 3 days after a conversation, 5 business days without one.)
- Who owns a lead nobody touched for 3 days?

Write them down. Every tool below has a setting for these numbers.

---

## Step 2. Your list ([`data-pipeline/`](../data-pipeline/))

**What you'll get:** clean CSV files ready to import into Zoho CRM, GoHighLevel or HubSpot, with duplicates merged and do-not-contact records removed.

1. Try it on the examples:
   ```bash
   cd data-pipeline
   python3 pipeline.py run samples/registry-export.example.csv samples/manual-research.example.csv \
       --existing samples/crm-export.example.csv --suppression samples/suppression.example.csv
   cat out/report.md
   ```
2. Read [`data-pipeline/SOURCES.md`](../data-pipeline/SOURCES.md): which data you may collect automatically, and how to research by hand when a site doesn't allow it.
3. Put your own files in place of the samples. Export what's already in your CRM and your opt-out list, and pass them with `--existing` and `--suppression`.
4. Open `out/clean.csv` in a spreadsheet and check 10 rows.
5. Import 10 rows into your CRM as a test. Then the rest.

**What to configure:** usually nothing. If your file's columns aren't recognized, add their names to `profiles/generic.json`.

---

## Step 3. Alerts ([`alerts/`](../alerts/))

**What you'll get:** a message in your team chat when a lead comes in ("call within 15 minutes"), when someone replies, and when a lead gets hot. Plus an escalation if nobody called a new lead in time.

1. Try it:
   ```bash
   cd alerts
   python3 alerts.py process events.example.jsonl --now 2026-03-02T16:10:00Z
   python3 alerts.py sla --now 2026-03-02T16:10:00Z
   ```
   Read the lines that start with `[ALERT]`, `[CRITICAL]` and `[DRY RUN] CRM task`. That is what your team would see.
2. Configure:
   - `cp config.example.json config.json`. Change `speed_to_lead_minutes` if your rule isn't 15.
   - `cp .env.example .env`, then `chmod 600 .env`. Paste your team chat's **incoming webhook URL** into `ALERT_WEBHOOK_URL`. (In Slack, Google Chat, Zoho Cliq or Discord, look for "incoming webhook" in the channel's settings or apps.)
3. Test the chat connection (this posts ONE test message):
   ```bash
   python3 alerts.py test-alert --live
   ```
4. Connect your CRM: the "Where to plug it in" section of [`alerts/README.md`](../alerts/README.md) has steps for Zoho CRM, GoHighLevel and HubSpot.

---

## Step 4. The 24-step journey ([`journeys/24-step/`](../journeys/24-step/))

**What you'll get:** 24 emails and 6 texts over 90 days for leads who didn't buy yet, sent safely: never twice, never after STOP, never more than 2 messages a day.

1. Try it:
   ```bash
   cd journeys/24-step
   python3 engine.py check
   python3 engine.py enroll contacts.example.csv
   python3 engine.py run --ignore-window
   ```
   You'll see each email and text it *would* send.
2. Read the copy in `templates/en/`. Rewrite it in your voice. Keep the unsubscribe line, the mailing address and "Reply STOP to opt out."
3. Configure:
   - `cp config.example.json config.json` and replace every `CHANGE-ME` and `example.com`: your name, company, website, mailing address, booking link, unsubscribe link.
   - Set the send window (days and hours) and time zone for your audience.
   - `cp .env.example .env`, `chmod 600 .env`, and fill in your email (SMTP) and SMS (Twilio) settings, or the webhook URLs if your CRM sends for you.
4. Check again. This time it must pass the live check:
   ```bash
   python3 engine.py check --live
   ```
5. Test on yourself: make a CSV with only **your own** email and phone, enroll it, and run in dry run with `--now` dates to see every step.

---

## Step 5. Going live (only when you're ready)

Read the [15-check going-live list](../safety/README.md#going-live-checklist-15-checks). Do every item. The short version:

1. Tests pass. `check --live` passes.
2. Alerts reach your team chat.
3. Every past opt-out is loaded into the suppression list.
4. No other tool (a CRM workflow, another app) messages the same leads.
5. You tested every step on your own inbox and phone.
6. The owner says "go" twice: once on the test, once on the audience and count.
7. You know the kill switch by heart:
   ```bash
   python3 safety/guard.py kill --dir journeys/24-step/state --reason "stop everything"
   ```
8. You watch the first live run, and again an hour later.

Then, and only then, add `--live` to the commands and schedule them (the READMEs show the cron lines).

---

## When something goes wrong

1. **Stop first:** run the kill command above. Nothing sends while the kill file exists.
2. **Look:** `python3 safety/guard.py status --db journeys/24-step/state/live.db` and the `alerts.log` file in the module's `state/` folder.
3. **Fix the cause.** Failed messages are never retried automatically, so fixing the cause doesn't cause a burst.
4. **Resume:** `python3 safety/guard.py resume --dir journeys/24-step/state`.

## Glossary

| Word | Meaning |
|---|---|
| Dry run | Practice mode. Prints what would happen. Sends nothing |
| `--live` | The flag that makes a command really send |
| Journey | A planned series of messages over time |
| Step | One message (or one email + one text) in a journey |
| Marker | A note the engine saves before sending: "step 3 email to Ana". If it exists, that message never goes out again |
| Cap | A daily limit per person |
| Suppression list | People who said STOP or unsubscribed. Permanent |
| Circuit breaker | Automatic stop after repeated failures, so a broken provider can't cause a flood |
| Kill switch | A file that stops all sending while it exists |
| Webhook | A web address one tool calls to tell another tool something happened |
| Speed to lead | How fast a new lead gets a first call |

## Need help?

Open an issue on GitHub, or if you'd rather have us set it up: [book a strategy call](https://gsd500bpo.com/strategy-call?utm_source=github&utm_medium=getting_started&utm_campaign=open-ops).
