#!/usr/bin/env python3
"""Alerts: new lead -> task + team alert (speed to lead); reply -> task + alert; engagement -> hot-lead score.
Python 3.9+, standard library only. DRY RUN BY DEFAULT: without --live nothing is posted and no task is created.

This module only talks to YOUR TEAM (team chat + CRM tasks). It never messages a lead.

Commands (run from this folder):
  python3 alerts.py process events.jsonl [--live]     read events (one JSON per line) and act on new ones
  python3 alerts.py sla [--live] [--now ISO]          speed-to-lead check: escalate leads nobody contacted in time
  python3 alerts.py serve [--live] [--port 8787]      tiny webhook receiver (POST /events) for your CRM / forms
  python3 alerts.py test-alert [--live]               send ONE test alert so you know the chat webhook works
  python3 alerts.py status [--live]                   leads, scores, alerts sent

Event (one JSON object):
  {"id": "evt-123", "type": "new_lead|email_open|email_click|reply|stop|contacted|booked",
   "lead_id": "L-1", "name": "Ana", "phone": "+15550000001", "email": "ana@example.com",
   "text": "reply text, if any", "ts": "2026-03-02T15:00:00Z"}

Score: open +5, click +10, reply +25 (configurable). Hot >= 70, Critical >= 90.
"""
import argparse
import datetime as dt
import hashlib
import hmac
import json
import os
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.environ.get("GSD_SAFETY_DIR", os.path.join(HERE, "..", "safety")))
import guard as guardlib  # noqa: E402
import notify as notifylib  # noqa: E402
import crm as crmlib  # noqa: E402

DEFAULTS = {
    "sender_id": "alerts",
    "state_dir": "state",
    "points": {"email_open": 5, "email_click": 10, "reply": 25},
    "max_open_points": 20,
    "hot_threshold": 70,
    "critical_threshold": 90,
    "speed_to_lead_minutes": 15,
    "max_alerts_per_run": 20,
    "max_alerts_per_lead_per_day": 5,
    "circuit_breaker_failures": 2,
    "crm": {"type": "dryrun"},
    "field_map": {},
    "crm_link": "",
}


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_time(s):
    if not s:
        return guardlib.utcnow()
    t = dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


class Tripped(Exception):
    pass


class Alerts:
    def __init__(self, cfg_path=None, live=False, notifier=None, crm=None, out=print):
        cfg = dict(DEFAULTS)
        base = HERE
        if cfg_path and os.path.exists(cfg_path):
            cfg.update(read_json(cfg_path))
            base = os.path.dirname(os.path.abspath(cfg_path))
        self.cfg = cfg
        self.live = live
        self.out = out
        self.state_dir = os.path.join(base, cfg["state_dir"])
        os.makedirs(self.state_dir, exist_ok=True)
        self.db_path = os.path.join(self.state_dir, "alerts-live.db" if live else "alerts-dry-run.db")
        self.notify = notifier or notifylib.Notifier(os.path.join(self.state_dir, "alerts.log"), live=live,
                                                     source=cfg["sender_id"])
        self.guard = guardlib.Guard(self.db_path, cfg["sender_id"], notifier=self.notify)
        self.crm = crm or crmlib.build(cfg.get("crm", {}), live, out)
        self.db = self.guard.db
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, lead_id TEXT, type TEXT, ts TEXT, data TEXT);
          CREATE TABLE IF NOT EXISTS leads (lead_id TEXT PRIMARY KEY, name TEXT, phone TEXT, email TEXT, score INTEGER DEFAULT 0,
              open_points INTEGER DEFAULT 0, status TEXT DEFAULT 'new', created_ts TEXT, contacted_ts TEXT, data TEXT);
          CREATE TABLE IF NOT EXISTS sent_alerts (lead_id TEXT, kind TEXT, ts TEXT, status TEXT, detail TEXT,
              PRIMARY KEY (lead_id, kind));""")
        self.consecutive_failures = 0
        self.alerts_this_run = 0

    def close(self):
        self.guard.close()

    # ---- helpers --------------------------------------------------------------------------------
    def normalize(self, ev):
        fm = self.cfg.get("field_map") or {}
        ev = {fm.get(k, k): v for k, v in ev.items()}
        ev["type"] = str(ev.get("type", "")).strip().lower()
        ev["lead_id"] = str(ev.get("lead_id") or ev.get("email") or ev.get("phone") or "").strip()
        if not ev.get("id"):
            raw = json.dumps(ev, sort_keys=True).encode()
            ev["id"] = "auto-" + hashlib.sha1(raw).hexdigest()[:16]
        return ev

    def lead(self, lead_id):
        r = self.db.execute("SELECT lead_id, name, phone, email, score, open_points, status, created_ts, contacted_ts "
                            "FROM leads WHERE lead_id=?", (lead_id,)).fetchone()
        if not r:
            return None
        return dict(zip(("lead_id", "name", "phone", "email", "score", "open_points", "status", "created_ts",
                         "contacted_ts"), r))

    def upsert_lead(self, ev, now):
        if not self.lead(ev["lead_id"]):
            self.db.execute("INSERT INTO leads (lead_id, name, phone, email, created_ts, data) VALUES (?,?,?,?,?,?)",
                            (ev["lead_id"], ev.get("name", ""), ev.get("phone", ""), ev.get("email", ""),
                             ev.get("ts") or now.isoformat(), json.dumps(ev)))
        else:
            for f in ("name", "phone", "email"):
                if ev.get(f):
                    self.db.execute(f"UPDATE leads SET {f}=? WHERE lead_id=? AND ({f} IS NULL OR {f}='')",
                                    (ev[f], ev["lead_id"]))

    def label(self, lead):
        bits = [lead.get("name") or lead["lead_id"]]
        if lead.get("phone"):
            bits.append(lead["phone"])
        if lead.get("email"):
            bits.append(lead["email"])
        link = self.cfg.get("crm_link", "")
        if link:
            bits.append(link.replace("{lead_id}", urllib.parse.quote(lead["lead_id"])))
        return " | ".join(bits)

    # ---- the one place an alert is sent ---------------------------------------------------------
    def fire(self, lead_id, kind, level, text, task=None, now=None):
        """Mark BEFORE posting. One alert per (lead, kind) ever. Caps per run and per lead per day.
        Returns True if sent now, False if skipped (already sent, capped, killed)."""
        now = now or guardlib.utcnow()
        if self.guard.killed():
            return False
        if self.db.execute("SELECT 1 FROM sent_alerts WHERE lead_id=? AND kind=?", (lead_id, kind)).fetchone():
            return False
        day = now.strftime("%Y-%m-%d")
        n_today = self.db.execute("SELECT COUNT(*) FROM sent_alerts WHERE lead_id=? AND kind LIKE 'reply:%' AND substr(ts,1,10)=?",
                                  (lead_id, day)).fetchone()[0]
        # once-ever kinds (new_lead, hot, critical, stop, sla_missed) cannot repeat; the daily cap guards the noisy one: replies
        if kind.startswith("reply:") and n_today >= int(self.cfg["max_alerts_per_lead_per_day"]):
            self.db.execute("INSERT OR IGNORE INTO sent_alerts VALUES (?,?,?,?,?)", (lead_id, kind, now.isoformat(), "capped", ""))
            return False
        self.db.execute("INSERT INTO sent_alerts VALUES (?,?,?,?,?)", (lead_id, kind, now.isoformat(), "sending", ""))
        self.alerts_this_run += 1
        ok_chat = self.notify.send(level, text)
        ok_task, detail = True, ""
        if task:
            try:
                detail = str(self.crm.create_task(**task, idempotency_key=f"{lead_id}:{kind}"))
            except Exception as e:
                ok_task, detail = False, f"{type(e).__name__}: {e}"
        ok = ok_chat and ok_task
        self.db.execute("UPDATE sent_alerts SET status=?, detail=? WHERE lead_id=? AND kind=?",
                        ("sent" if ok else "failed", detail[:300], lead_id, kind))
        if ok:
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
            self.notify.send("ERROR", f"alert '{kind}' for {lead_id} failed (chat ok={ok_chat}, task ok={ok_task} {detail[:120]}). "
                                      f"Not retried automatically.")
            if self.consecutive_failures >= int(self.cfg["circuit_breaker_failures"]):
                self.guard.trip(f"{self.consecutive_failures} alert deliveries failed in a row")
                raise Tripped("circuit breaker")
        return ok

    # ---- events ---------------------------------------------------------------------------------
    def handle(self, raw, now=None):
        now = now or guardlib.utcnow()
        ev = self.normalize(raw)
        if not ev["lead_id"] or not ev["type"]:
            self.notify.send("WARN", f"ignored event without lead_id/type: {json.dumps(raw)[:160]}")
            return "ignored"
        if self.db.execute("SELECT 1 FROM events WHERE id=?", (ev["id"],)).fetchone():
            return "duplicate"
        self.db.execute("INSERT INTO events VALUES (?,?,?,?,?)",
                        (ev["id"], ev["lead_id"], ev["type"], ev.get("ts") or now.isoformat(), json.dumps(ev)))
        self.upsert_lead(ev, now)
        t, lid = ev["type"], ev["lead_id"]
        lead = self.lead(lid)
        sla = int(self.cfg["speed_to_lead_minutes"])

        if t == "reply" and guardlib.is_stop(ev.get("text", "")):
            t = "stop"
        if t == "stop":
            self.guard.suppress([lid, lead.get("email") or "", lead.get("phone") or ""], "*", "STOP / unsubscribe")
            self.db.execute("UPDATE leads SET status='stopped' WHERE lead_id=?", (lid,))
            self.fire(lid, "stop", "INFO", f"OPT-OUT: {self.label(lead)} asked to stop. Do not contact again on any channel.",
                      now=now)
            return "stop"
        if lead["status"] == "stopped":
            return "stopped_lead"
        if t == "new_lead":
            self.fire(lid, "new_lead", "ALERT",
                      f"NEW LEAD: {self.label(lead)}. Call within {sla} minutes.",
                      task={"lead_id": lid, "subject": f"Call new lead within {sla} min", "due_minutes": sla,
                            "priority": "High", "description": f"New lead {self.label(lead)}"}, now=now)
        elif t in ("contacted", "booked"):
            self.db.execute("UPDATE leads SET contacted_ts=COALESCE(contacted_ts, ?), status=? WHERE lead_id=?",
                            (ev.get("ts") or now.isoformat(), "booked" if t == "booked" else "contacted", lid))
        elif t in self.cfg["points"]:
            pts = int(self.cfg["points"][t])
            if t == "email_open":
                pts = max(0, min(pts, int(self.cfg["max_open_points"]) - int(lead["open_points"] or 0)))
                self.db.execute("UPDATE leads SET open_points=open_points+? WHERE lead_id=?", (pts, lid))
            self.db.execute("UPDATE leads SET score=score+? WHERE lead_id=?", (pts, lid))
            if t == "reply":
                txt = (ev.get("text") or "").strip()
                self.fire(lid, f"reply:{ev['id']}", "ALERT",
                          f"REPLY from {self.label(lead)}: \"{txt[:200]}\". Answer within {sla} minutes. Automation is paused for this lead.",
                          task={"lead_id": lid, "subject": "Answer lead reply", "due_minutes": sla, "priority": "High",
                                "description": txt[:1000]}, now=now)
            self.check_tier(lid, now)
        return t

    def check_tier(self, lid, now):
        lead = self.lead(lid)
        s = int(lead["score"])
        if s >= int(self.cfg["critical_threshold"]):
            self.fire(lid, "critical", "CRITICAL", f"CRITICAL LEAD (score {s}): {self.label(lead)}. Call now.",
                      task={"lead_id": lid, "subject": f"CRITICAL lead, score {s}: call now", "due_minutes": 15,
                            "priority": "Highest", "description": f"Engagement score {s}"}, now=now)
        elif s >= int(self.cfg["hot_threshold"]):
            self.fire(lid, "hot", "ALERT", f"HOT LEAD (score {s}): {self.label(lead)}. Call today.",
                      task={"lead_id": lid, "subject": f"Hot lead, score {s}: call today", "due_minutes": 240,
                            "priority": "High", "description": f"Engagement score {s}"}, now=now)

    def process(self, events, now=None):
        stats = {}
        k = self.guard.killed()
        if k:
            self.out(f"KILL SWITCH ON ({k}). Nothing processed.")
            return {"killed": k}
        for ev in events:
            if self.alerts_this_run >= int(self.cfg["max_alerts_per_run"]):
                self.out("max_alerts_per_run reached; the rest waits for the next run")
                self.notify.send("WARN", f"{self.cfg['sender_id']}: more than {self.cfg['max_alerts_per_run']} alerts in one run. "
                                         "Unusual volume, please look.")
                stats["deferred"] = True
                break
            try:
                r = self.handle(ev, now)
            except Tripped as e:
                self.out(f"stopped: {e}")
                stats["stopped"] = str(e)
                break
            stats[r] = stats.get(r, 0) + 1
        self.out(f"processed ({'LIVE' if self.live else 'dry-run'}): {json.dumps(stats)}")
        return stats

    def sla(self, now=None):
        now = now or guardlib.utcnow()
        if self.guard.killed():
            return {"killed": True}
        cutoff = now - dt.timedelta(minutes=int(self.cfg["speed_to_lead_minutes"]))
        n = 0
        rows = self.db.execute("SELECT lead_id, created_ts FROM leads WHERE contacted_ts IS NULL AND status NOT IN ('stopped')"
                               " AND lead_id IN (SELECT lead_id FROM events WHERE type='new_lead')").fetchall()
        for lid, created in rows:
            if parse_time(created) <= cutoff:
                mins = int((now - parse_time(created)).total_seconds() // 60)
                try:
                    if self.fire(lid, "sla_missed", "CRITICAL",
                                 f"SPEED-TO-LEAD MISSED: {self.label(self.lead(lid))} has waited {mins} min with no contact.",
                                 now=now):
                        n += 1
                except Tripped as e:
                    self.out(f"stopped: {e}")
                    break
        self.out(f"sla check: {n} escalation(s)")
        return {"escalated": n}

    def status(self):
        return {"mode": "LIVE" if self.live else "dry-run", "db": self.db_path, "killed": self.guard.killed(),
                "leads": self.db.execute("SELECT lead_id, score, status FROM leads ORDER BY score DESC LIMIT 25").fetchall(),
                "alerts": self.db.execute("SELECT kind, status, COUNT(*) FROM sent_alerts GROUP BY kind, status").fetchall()}


def read_events(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def serve(a, port, secret):
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path.split("?")[0] != "/events":
                self.send_response(404); self.end_headers(); return
            body = self.rfile.read(min(int(self.headers.get("Content-Length", 0)), 1_000_000))
            sig = self.headers.get("X-Signature-SHA256", "")
            token = self.headers.get("X-Webhook-Secret", "") or urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("secret", [""])[0]
            good = hmac.compare_digest(token, secret) or (sig and hmac.compare_digest(sig, hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()))
            if not good:
                self.send_response(401); self.end_headers(); return
            try:
                data = json.loads(body) if body.strip().startswith((b"{", b"[")) else {k: v[0] for k, v in urllib.parse.parse_qs(body.decode()).items()}
            except Exception:
                self.send_response(400); self.end_headers(); return
            res = a.process(data if isinstance(data, list) else [data])
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(json.dumps(res).encode())

        def log_message(self, *args):
            pass

    print(f"listening on 127.0.0.1:{port} (POST /events). Put HTTPS (a reverse proxy) in front before exposing it.")
    HTTPServer(("127.0.0.1", port), H).serve_forever()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Lead alerts (dry run unless --live)")
    ap.add_argument("cmd", choices=["process", "sla", "serve", "test-alert", "status"])
    ap.add_argument("file", nargs="?")
    ap.add_argument("--config", default=os.path.join(HERE, "config.json") if os.path.exists(os.path.join(HERE, "config.json"))
                    else os.path.join(HERE, "config.example.json"))
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--now")
    ap.add_argument("--port", type=int, default=8787)
    a = ap.parse_args(argv)
    env = os.path.join(HERE, ".env")
    if os.path.exists(env):
        with open(env) as f:
            for line in f:
                if "=" in line and not line.lstrip().startswith("#"):
                    k, v = line.strip().split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"\''))
    al = Alerts(a.config, live=a.live)
    now = parse_time(a.now) if a.now else None
    if a.cmd == "process":
        al.process(read_events(a.file or os.path.join(HERE, "events.example.jsonl")), now)
    elif a.cmd == "sla":
        al.sla(now)
    elif a.cmd == "test-alert":
        ok = al.notify.send("TEST", "Test alert from gsd-open-ops alerts. If you can read this in your team chat, alerts work.")
        print("posted" if ok and a.live else ("dry run: printed only" if ok else "FAILED: check ALERT_WEBHOOK_URL"))
        sys.exit(0 if ok else 1)
    elif a.cmd == "serve":
        secret = os.environ.get("WEBHOOK_SECRET", "")
        if len(secret) < 16:
            sys.exit("set WEBHOOK_SECRET (16+ random characters) in .env before running serve")
        serve(al, a.port, secret)
    elif a.cmd == "status":
        print(json.dumps(al.status(), indent=2, default=str))


if __name__ == "__main__":
    main()
