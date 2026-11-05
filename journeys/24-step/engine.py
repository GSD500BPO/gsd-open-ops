#!/usr/bin/env python3
"""24-step nurture journey engine. Python 3.9+, standard library only.

DRY RUN BY DEFAULT. Nothing is sent unless you pass --live, and --live refuses to start if `check` fails.

Commands (run from this folder):
  python3 engine.py check   [--live]                 validate journey, templates and config
  python3 engine.py enroll  contacts.csv [--live]    add contacts (STOP/do-not-contact are never enrolled)
  python3 engine.py run     [--live] [--now ISO] [--ignore-window]
                                                     send what is due (cron: every 10-15 minutes)
  python3 engine.py inbound --from ADDRESS --text "..." [--channel sms|email] [--live]
                                                     a reply came in: STOP = suppressed forever, anything else = pause + human
  python3 engine.py event   --contact ID --type open|click|bounce|booked|unsubscribe [--live]
  python3 engine.py preview --contact ID --step 1    show one rendered message
  python3 engine.py status  [--live]

Dry run uses state/dry-run.db. Live uses state/live.db. They never mix.
Kill switch: touch state/KILL_ALL (or run: python3 ../../safety/guard.py kill --dir state).
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.environ.get("GSD_SAFETY_DIR", os.path.join(HERE, "..", "..", "safety")))
import guard as guardlib  # noqa: E402
import notify as notifylib  # noqa: E402
import providers as providerlib  # noqa: E402

PLACEHOLDER = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*(?:\|([^}]*))?\}\}")
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
YES = {"yes", "y", "true", "1", "si", "sí"}


def load_env(path):
    """Minimal .env loader (KEY=VALUE lines). Existing environment variables win."""
    if not os.path.exists(path):
        return
    for line in read_text(path).splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"\''))


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_time(s):
    if not s:
        return guardlib.utcnow()
    t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


class RenderError(Exception):
    pass


def render(text, values):
    """{{field}} or {{field|fallback}}. Two passes so config values may contain {{contact_id}}.
    Anything left unfilled (or a {{YOUR_...}} placeholder) raises RenderError: we never send a broken message."""
    def sub(m):
        v = values.get(m.group(1))
        v = "" if v is None else str(v).strip()
        if v:
            return v
        if m.group(2) is not None:
            return m.group(2)
        raise RenderError(f"missing value for {{{{{m.group(1)}}}}}")
    out = PLACEHOLDER.sub(sub, PLACEHOLDER.sub(sub, text))
    if "{{" in out or "}}" in out:
        raise RenderError("unfilled placeholder left in message")
    return out


class Engine:
    def __init__(self, cfg_path, live=False, out=print, provider_overrides=None, notifier=None):
        self.cfg_path = os.path.abspath(cfg_path)
        base = os.path.dirname(self.cfg_path)
        self.cfg = read_json(self.cfg_path)
        p = lambda k, d: os.path.join(base, self.cfg.get(k, d))
        self.journey = read_json(p("journey_file", "journey.json"))
        self.templates_dir = p("templates_dir", "templates/en")
        self.state_dir = p("state_dir", "state")
        self.events_out = p("events_out", "state/events.jsonl")
        self.live = live
        self.out = out
        os.makedirs(self.state_dir, exist_ok=True)
        self.db_path = os.path.join(self.state_dir, "live.db" if live else "dry-run.db")
        self.notify = notifier or notifylib.Notifier(os.path.join(self.state_dir, "alerts.log"), live=live,
                                                     source=self.cfg.get("sender_id", "nurture-24"))
        caps = self.cfg.get("caps", {})
        self.guard = guardlib.Guard(
            self.db_path, self.cfg.get("sender_id", "nurture-24"), notifier=self.notify,
            caps={"email": caps.get("email_per_address_per_day", 1), "sms": caps.get("sms_per_address_per_day", 1)},
            max_touches_per_day=caps.get("touches_per_contact_per_day", 2),
            breaker=self.cfg.get("circuit_breaker_failures", 2))
        self.db = self.guard.db
        self.db.execute("""CREATE TABLE IF NOT EXISTS contacts (
            id TEXT PRIMARY KEY, data TEXT, status TEXT, step_index INTEGER, enrolled_at TEXT, next_due TEXT,
            engaged INTEGER DEFAULT 0, updated TEXT)""")
        self.provider_overrides = provider_overrides or {}
        self._providers = {}

    def close(self):
        self.guard.close()

    # ---- helpers --------------------------------------------------------------------------------
    def provider(self, channel):
        if channel in self.provider_overrides:
            return self.provider_overrides[channel]
        if channel not in self._providers:
            self._providers[channel] = providerlib.build(channel, self.cfg.get("providers", {}).get(channel), self.live, self.out)
        return self._providers[channel]

    def template(self, step, channel):
        path = os.path.join(self.templates_dir, f"{step['template']}.{channel}.txt")
        text = read_text(path)
        if channel == "email":
            first, _, rest = text.partition("\n")
            if not first.lower().startswith("subject:"):
                raise RenderError(f"{path}: first line must be 'Subject: ...'")
            return first.split(":", 1)[1].strip(), rest.strip() + "\n"
        return "", text.strip()

    def values(self, contact):
        v = dict(self.cfg.get("merge", {}))
        v.update({k: c for k, c in contact.items() if c not in (None, "")})
        v["contact_id"] = contact["id"]
        return v

    def contact(self, cid):
        row = self.db.execute("SELECT data, status, step_index, enrolled_at, next_due, engaged FROM contacts WHERE id=?",
                              (cid,)).fetchone()
        if not row:
            return None
        c = json.loads(row[0])
        c.update(id=cid, _status=row[1], _step=row[2], _enrolled=row[3], _due=row[4], _engaged=row[5])
        return c

    def set_status(self, cid, status):
        self.db.execute("UPDATE contacts SET status=?, updated=? WHERE id=?", (status, guardlib.utcnow().isoformat(), cid))

    def emit(self, event):
        """Write an event the alerts/ module can read (reply, stop, open, click, booked)."""
        event.setdefault("ts", guardlib.utcnow().isoformat())
        event.setdefault("source", self.cfg.get("sender_id", "nurture-24"))
        with open(self.events_out, "a") as f:
            f.write(json.dumps(event) + "\n")

    def in_window(self, now):
        w = self.cfg.get("send_window")
        if not w:
            return True
        from zoneinfo import ZoneInfo
        local = now.astimezone(ZoneInfo(w.get("timezone", "UTC")))
        return DAYS[local.weekday()] in w.get("days", DAYS) and w.get("start_hour", 0) <= local.hour < w.get("end_hour", 24)

    # ---- check ----------------------------------------------------------------------------------
    def check(self):
        problems = []
        steps = self.journey.get("steps", [])
        if len({s["id"] for s in steps}) != len(steps):
            problems.append("duplicate step ids")
        days = [s["day"] for s in steps]
        if days != sorted(days):
            problems.append("step days must go up")
        sample = {k: "x" for k in ("first_name", "last_name", "company", "email", "phone", "city", "state")}
        sample["id"] = "check"
        for s in steps:
            for ch in s["channels"]:
                try:
                    subj, body = self.template(s, ch)
                    render(subj + "\n" + body, self.values(sample))
                    if ch == "sms" and "stop" not in body.lower():
                        problems.append(f"{s['id']}.sms: every text must say how to opt out (Reply STOP)")
                    if ch == "email" and "{{unsubscribe_link" not in body:
                        problems.append(f"{s['id']}.email: missing {{{{unsubscribe_link}}}}")
                    if ch == "email" and "{{physical_address" not in body:
                        problems.append(f"{s['id']}.email: missing {{{{physical_address}}}}")
                except (OSError, RenderError) as e:
                    problems.append(f"{s['id']}.{ch}: {e}")
        merge = self.cfg.get("merge", {})
        if self.live:
            for k, v in merge.items():
                if "CHANGE-ME" in str(v) or "example.com" in str(v):
                    problems.append(f"merge.{k} still has a placeholder ({v}); fill it before going live")
            for ch, pc in self.cfg.get("providers", {}).items():
                if any("example.com" in str(x) or "CHANGE-ME" in str(x) or "+1555" in str(x).replace(" ", "") for x in pc.values()):
                    problems.append(f"providers.{ch} still has an example value")
                try:
                    providerlib.build(ch, pc, True)
                except Exception as e:
                    problems.append(f"providers.{ch}: {e}")
        return problems

    # ---- enroll ---------------------------------------------------------------------------------
    def enroll(self, csv_path, now=None):
        now = now or guardlib.utcnow()
        added = skipped = 0
        first_day = self.journey["steps"][0]["day"]
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        for row in rows:
            row = {k.strip(): (v or "").strip() for k, v in row.items() if k}
            cid = row.get("id") or row.get("email") or row.get("phone")
            if not cid:
                skipped += 1; continue
            keys = [cid, row.get("email", ""), row.get("phone", "")]
            if row.get("do_not_contact", "").lower() in YES or row.get("in_other_journey", "").lower() in YES:
                self.out(f"skip {cid}: do_not_contact / already in another journey"); skipped += 1; continue
            if self.guard.is_suppressed(keys, "*"):
                self.out(f"skip {cid}: suppressed (STOP / unsubscribe) - never re-enrolled"); skipped += 1; continue
            if self.db.execute("SELECT 1 FROM contacts WHERE id=?", (cid,)).fetchone():
                skipped += 1; continue
            row["id"] = cid
            due = now + dt.timedelta(days=first_day)
            self.db.execute("INSERT INTO contacts VALUES (?,?,?,?,?,?,0,?)",
                            (cid, json.dumps(row), "active", 0, now.isoformat(), due.isoformat(), now.isoformat()))
            added += 1
        self.out(f"enrolled {added}, skipped {skipped} ({'LIVE' if self.live else 'dry-run'} state)")
        return added, skipped

    # ---- eligibility ----------------------------------------------------------------------------
    def eligible(self, c, channel):
        rules = self.journey.get("channel_rules", {}).get(channel, {})
        for req in rules.get("requires", []):
            v = (c.get(req) or "").strip().lower()
            if req.endswith("consent"):
                if v not in YES:
                    return f"no {req}"
            elif not v:
                return f"no {req}"
        if rules.get("only_if_engaged") and not c.get("_engaged"):
            return "waiting for engagement (open/click/reply)"
        if self.guard.is_suppressed([c["id"], c.get(channel_address_field(channel), "")], channel):
            return "suppressed"
        return None

    # ---- run ------------------------------------------------------------------------------------
    def run(self, now=None, ignore_window=False):
        now = now or guardlib.utcnow()
        sender = self.guard.sender
        k = self.guard.killed()
        if k:
            self.out(f"KILL SWITCH ON ({k}). Nothing sent.")
            return {"killed": k}
        if ignore_window and self.live:
            raise SystemExit("--ignore-window is for dry runs only")
        if not ignore_window and not self.in_window(now):
            self.out("outside the send window; nothing to do")
            return {"outside_window": True}
        stats = {"sent": 0, "failed": 0, "skipped": 0, "deferred": 0, "advanced": 0, "completed": 0}
        steps = self.journey["steps"]
        due = self.db.execute("SELECT id FROM contacts WHERE status='active' AND next_due<=? ORDER BY next_due LIMIT ?",
                              (now.isoformat(), int(self.cfg.get("max_contacts_per_run", 50)))).fetchall()
        for (cid,) in due:
            if self.guard.killed():
                self.out("engine stopped mid-run by kill switch / circuit breaker")
                break
            c = self.contact(cid)
            if self.guard.is_suppressed([cid, c.get("email", ""), c.get("phone", "")], "*"):
                self.set_status(cid, "stopped"); continue
            if self.guard.halted(cid):
                self.set_status(cid, "halted"); continue
            step = steps[c["_step"]]
            deferred = False
            for ch in step["channels"]:
                if self.guard.marker(cid, step["id"], ch):
                    continue                                     # already handled once: never again
                why = self.eligible(c, ch)
                if why:
                    self.guard.mark(cid, step["id"], ch, "skipped", why); stats["skipped"] += 1; continue
                try:
                    subject, body = self.template(step, ch)
                    vals = self.values(c)
                    subject, body = render(subject, vals), render(body, vals)
                except (OSError, RenderError) as e:
                    self.guard.mark(cid, step["id"], ch, "skipped", f"render: {e}")
                    self.notify("ERROR", f"{sender}: could not render {step['id']}.{ch} for {cid}: {e}. Skipped, not sent.")
                    stats["skipped"] += 1; continue
                addr = c.get(channel_address_field(ch), "")
                ok, reason = self.guard.reserve(cid, step["id"], ch, addr, now=now)   # marker written HERE, before sending
                if not ok:
                    if reason == "cap":
                        deferred = True; stats["deferred"] += 1; break           # try the rest on a later day
                    if reason in ("killed", "guard_error"):
                        return stats
                    self.guard.mark(cid, step["id"], ch, "skipped", reason); stats["skipped"] += 1; continue
                meta = {"contact_id": cid, "step": step["id"], "unsubscribe_link": self.values(c).get("unsubscribe_link"),
                        "idempotency_key": f"{sender}:{cid}:{step['id']}:{ch}"}
                if "{{" in str(meta["unsubscribe_link"]):
                    meta["unsubscribe_link"] = render(meta["unsubscribe_link"], self.values(c))
                try:
                    msg_id = self.provider(ch).send(addr, subject, body, meta)
                    self.guard.complete(cid, step["id"], ch, True, str(msg_id)); stats["sent"] += 1
                except Exception as e:
                    stats["failed"] += 1
                    res = self.guard.complete(cid, step["id"], ch, False, f"{type(e).__name__}: {e}")
                    if res == "engine_tripped":
                        return stats
                    if res == "contact_halted":
                        self.set_status(cid, "halted"); break
            if self.guard.halted(cid) or deferred:
                continue
            if all(self.guard.marker(cid, step["id"], ch) for ch in step["channels"]):
                self.advance(c, now); stats["advanced"] += 1
                if c["_step"] + 1 >= len(steps):
                    stats["completed"] += 1
        self.out(f"run done ({'LIVE' if self.live else 'dry-run'}): {json.dumps(stats)}")
        return stats

    def advance(self, c, now):
        steps = self.journey["steps"]
        nxt = c["_step"] + 1
        if nxt >= len(steps):
            self.db.execute("UPDATE contacts SET status='completed', step_index=?, updated=? WHERE id=?",
                            (nxt, now.isoformat(), c["id"]))
            return
        enrolled = parse_time(c["_enrolled"])
        gap = dt.timedelta(hours=self.journey.get("min_hours_between_steps", 20))
        due = max(enrolled + dt.timedelta(days=steps[nxt]["day"]), now + gap)
        self.db.execute("UPDATE contacts SET step_index=?, next_due=?, updated=? WHERE id=?",
                        (nxt, due.isoformat(), now.isoformat(), c["id"]))

    # ---- inbound + events -----------------------------------------------------------------------
    def find_by_address(self, address):
        key = guardlib.norm_address(address)
        for (cid, data) in self.db.execute("SELECT id, data FROM contacts").fetchall():
            d = json.loads(data)
            if key and key in (guardlib.norm_address(d.get("email")), guardlib.norm_address(d.get("phone"))):
                return cid
        return None

    def inbound(self, address, text, channel="sms"):
        cid = self.find_by_address(address)
        if guardlib.is_stop(text):
            self.guard.suppress([address] + ([cid] if cid else []), "*", f"STOP via {channel}: {text[:60]}")
            if cid:
                c = self.contact(cid)
                self.guard.suppress([c.get("email", ""), c.get("phone", "")], "*", "STOP (all channels)")
                self.set_status(cid, "stopped")
            self.emit({"type": "stop", "lead_id": cid or address, "channel": channel, "text": text[:200],
                       "id": f"stop:{guardlib.norm_address(address)}"})
            self.notify("INFO", f"STOP from {cid or address}: suppressed forever on every channel.")
            return "stopped"
        if cid:
            self.set_status(cid, "replied")
            self.db.execute("UPDATE contacts SET engaged=1 WHERE id=?", (cid,))
        self.emit({"type": "reply", "lead_id": cid or address, "channel": channel, "text": text[:500],
                   "id": f"reply:{guardlib.norm_address(address)}:{hashlib.sha1(text.encode()).hexdigest()[:10]}"})
        self.notify("ALERT", f"REPLY from {cid or address} ({channel}): \"{text[:160]}\". Journey paused. A human owns it now.")
        return "replied"

    def event(self, cid, etype):
        c = self.contact(cid)
        if not c:
            raise SystemExit(f"unknown contact {cid}")
        if etype in ("open", "click"):
            self.db.execute("UPDATE contacts SET engaged=1 WHERE id=?", (cid,))
            self.emit({"type": f"email_{etype}", "lead_id": cid})
        elif etype == "bounce":
            self.guard.suppress([c.get("email", "")], "email", "hard bounce")
        elif etype == "unsubscribe":
            self.guard.suppress([cid, c.get("email", ""), c.get("phone", "")], "*", "unsubscribed")
            self.set_status(cid, "stopped")
            self.emit({"type": "stop", "lead_id": cid, "channel": "email"})
        elif etype == "booked":
            self.set_status(cid, "won")
            self.emit({"type": "booked", "lead_id": cid})
        else:
            raise SystemExit(f"unknown event type {etype}")
        return etype

    def status(self):
        rows = self.db.execute("SELECT status, COUNT(*) FROM contacts GROUP BY status").fetchall()
        return {"mode": "LIVE" if self.live else "dry-run", "db": self.db_path, "contacts_by_status": dict(rows),
                **self.guard.summary()}


def channel_address_field(channel):
    return "email" if channel == "email" else "phone"


def main(argv=None):
    ap = argparse.ArgumentParser(description="24-step nurture engine (dry run unless --live)")
    ap.add_argument("cmd", choices=["check", "enroll", "run", "inbound", "event", "preview", "status"])
    ap.add_argument("csv", nargs="?")
    ap.add_argument("--config", default=os.path.join(HERE, "config.json") if os.path.exists(os.path.join(HERE, "config.json"))
                    else os.path.join(HERE, "config.example.json"))
    ap.add_argument("--live", action="store_true", help="really send (default: dry run)")
    ap.add_argument("--now", help="pretend it is this time (ISO 8601), for dry-run simulations")
    ap.add_argument("--ignore-window", action="store_true", help="dry run only: ignore the send window")
    ap.add_argument("--from", dest="sender_addr")
    ap.add_argument("--text", default="")
    ap.add_argument("--channel", default="sms")
    ap.add_argument("--contact")
    ap.add_argument("--type")
    ap.add_argument("--step", type=int, default=1)
    a = ap.parse_args(argv)
    load_env(os.path.join(HERE, ".env"))
    e = Engine(a.config, live=a.live)
    now = parse_time(a.now)
    if a.cmd == "check" or (a.live and a.cmd in ("run", "enroll")):
        problems = e.check()
        for p in problems:
            print("PROBLEM:", p)
        if problems:
            print(f"{len(problems)} problem(s). {'Live run refused.' if a.live else ''}")
            sys.exit(1)
        if a.cmd == "check":
            print(f"check OK ({len(e.journey['steps'])} steps, {'live' if a.live else 'dry-run'} config)")
            return
    if a.cmd == "enroll":
        e.enroll(a.csv or os.path.join(HERE, "contacts.example.csv"), now)
    elif a.cmd == "run":
        e.run(now, a.ignore_window)
    elif a.cmd == "inbound":
        print(e.inbound(a.sender_addr, a.text, a.channel))
    elif a.cmd == "event":
        print(e.event(a.contact, a.type))
    elif a.cmd == "preview":
        c = e.contact(a.contact)
        if not c:
            sys.exit(f"unknown contact {a.contact} (enroll first)")
        s = e.journey["steps"][a.step - 1]
        for ch in s["channels"]:
            subj, body = e.template(s, ch)
            print(f"--- {s['id']} {ch} ---")
            if subj:
                print("Subject:", render(subj, e.values(c)))
            print(render(body, e.values(c)))
    elif a.cmd == "status":
        print(json.dumps(e.status(), indent=2, default=str))


if __name__ == "__main__":
    main()
