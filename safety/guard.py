"""Outbound guard: the shared safety layer for every sender in this repo.

Why it exists: we once had a follow-up engine that sent an email, then tried a text. The text provider failed,
the step never advanced, and the scheduler retried the whole step every few minutes, email included. The same
person got the same email dozens of times. Everything below makes that impossible.

What it enforces (all ON by default, no flag turns them off):
  1. Kill switch     A file named KILL_ALL (or KILL_<sender>) in the state folder stops all sending at once.
  2. Idempotency     One "marker" per (sender, contact, step, channel). It is written BEFORE the send.
                     A channel that has a marker is never sent again, whatever happened after.
  3. Daily caps      Per recipient address per channel per day, and total touches per contact per day.
  4. Suppression     STOP / unsubscribe / hard bounce = permanent. There is no code path that removes it.
  5. Circuit breaker 2 consecutive failures on a channel for one contact halts that contact.
                     2 consecutive failures on a channel across the run trips the engine (writes KILL_<sender>).
  6. Fail closed     If the guard itself errors, nothing is sent.
  7. Loud errors     Every failure, halt and trip goes to the notifier (team chat webhook + alerts.log).

Storage: one SQLite file (standard library, atomic transactions, safe if two runs overlap).

CLI (run from anywhere):
  python3 safety/guard.py status   --db STATE.db
  python3 safety/guard.py kill     --dir STATE_DIR [--sender NAME] [--reason TEXT]
  python3 safety/guard.py resume   --dir STATE_DIR [--sender NAME]
  python3 safety/guard.py suppress --db STATE.db --address you@example.com [--reason "asked by phone"]
"""
import argparse
import datetime as dt
import json
import os
import re
import sqlite3
import sys

# STOP words in English and Spanish. Matching any of these is a permanent opt-out for that contact.
STOP_RE = re.compile(
    r"\b(stop|stopall|unsubscribe|remove me|opt[- ]?out|do not (text|contact|message|email)|"
    r"don'?t (text|contact|message|email)|baja|alto|no (me )?(env[ií]en|escriban|manden|contacten))\b"
    r"|^\s*(cancel|end|quit|parar|detener)\s*[.!]*\s*$",
    re.I,
)


def is_stop(text):
    return bool(STOP_RE.search(text or ""))


def norm_address(addr):
    """Email -> lowercase. Phone -> digits only, last 10 (US). Empty -> ''."""
    a = (addr or "").strip().lower()
    if not a:
        return ""
    if "@" in a:
        return a
    digits = re.sub(r"\D", "", a)
    return digits[-10:] if len(digits) >= 10 else digits


def utcnow():
    return dt.datetime.now(dt.timezone.utc)


SCHEMA = """
CREATE TABLE IF NOT EXISTS markers (
  sender TEXT, contact TEXT, step TEXT, channel TEXT, status TEXT, ts TEXT, detail TEXT,
  PRIMARY KEY (sender, contact, step, channel));
CREATE TABLE IF NOT EXISTS touches (ts TEXT, day TEXT, sender TEXT, contact TEXT, address TEXT, channel TEXT);
CREATE INDEX IF NOT EXISTS touches_day ON touches(day, address, channel);
CREATE INDEX IF NOT EXISTS touches_contact ON touches(day, contact);
CREATE TABLE IF NOT EXISTS suppression (key TEXT, channel TEXT, reason TEXT, ts TEXT, PRIMARY KEY (key, channel));
CREATE TABLE IF NOT EXISTS failures (sender TEXT, scope TEXT, channel TEXT, n INTEGER, PRIMARY KEY (sender, scope, channel));
CREATE TABLE IF NOT EXISTS halted (sender TEXT, contact TEXT, reason TEXT, ts TEXT, PRIMARY KEY (sender, contact));
"""


class Guard:
    def __init__(self, db_path, sender, notifier=None, caps=None, max_touches_per_day=2, breaker=2):
        self.db_path = db_path
        self.dir = os.path.dirname(os.path.abspath(db_path))
        self.sender = sender
        self.notify = notifier or (lambda level, text: print(f"[{level}] {text}", file=sys.stderr))
        self.caps = {"email": 1, "sms": 1, "whatsapp": 1}
        self.caps.update(caps or {})
        self.max_touches = int(max_touches_per_day)
        self.breaker = int(breaker)
        os.makedirs(self.dir, exist_ok=True)
        self.db = sqlite3.connect(db_path, timeout=30, isolation_level=None)  # autocommit; we use explicit BEGIN
        self.db.executescript(SCHEMA)

    def close(self):
        self.db.close()

    # ---- kill switch -------------------------------------------------------------------------
    def killed(self):
        for name in ("KILL_ALL", f"KILL_{self.sender}"):
            p = os.path.join(self.dir, name)
            if os.path.exists(p):
                try:
                    with open(p) as f:
                        reason = f.read().strip()
                except OSError:
                    reason = ""
                return f"{name}: {reason or 'no reason given'}"
        return None

    def trip(self, reason):
        p = os.path.join(self.dir, f"KILL_{self.sender}")
        with open(p, "w") as f:
            f.write(f"{utcnow().isoformat()} {reason}\n")
        self.notify("CRITICAL", f"{self.sender}: circuit breaker TRIPPED, engine stopped. {reason}. "
                                f"Fix the cause, then delete {p} to resume.")

    # ---- suppression -------------------------------------------------------------------------
    def suppress(self, keys, channel="*", reason=""):
        for k in keys:
            k = norm_address(k) if ("@" in (k or "") or re.search(r"\d{7}", k or "")) else (k or "").strip()
            if k:
                self.db.execute("INSERT OR IGNORE INTO suppression VALUES (?,?,?,?)",
                                (k, channel, reason[:200], utcnow().isoformat()))

    def is_suppressed(self, keys, channel):
        for k in keys:
            k = norm_address(k) if ("@" in (k or "") or re.search(r"\d{7}", k or "")) else (k or "").strip()
            if not k:
                continue
            row = self.db.execute("SELECT reason FROM suppression WHERE key=? AND channel IN ('*', ?)",
                                  (k, channel)).fetchone()
            if row:
                return row[0] or "suppressed"
        return None

    # ---- markers (idempotency) ---------------------------------------------------------------
    def marker(self, contact, step, channel):
        row = self.db.execute("SELECT status FROM markers WHERE sender=? AND contact=? AND step=? AND channel=?",
                              (self.sender, contact, str(step), channel)).fetchone()
        return row[0] if row else None

    def mark(self, contact, step, channel, status, detail=""):
        """Write a final marker without sending (skipped, not eligible...). Never overwrites an existing one."""
        self.db.execute("INSERT OR IGNORE INTO markers VALUES (?,?,?,?,?,?,?)",
                        (self.sender, contact, str(step), channel, status, utcnow().isoformat(), detail[:300]))

    # ---- halted contacts ---------------------------------------------------------------------
    def halted(self, contact):
        row = self.db.execute("SELECT reason FROM halted WHERE sender=? AND contact=?", (self.sender, contact)).fetchone()
        return row[0] if row else None

    def halt(self, contact, reason):
        self.db.execute("INSERT OR IGNORE INTO halted VALUES (?,?,?,?)", (self.sender, contact, reason[:200], utcnow().isoformat()))

    # ---- the two calls every sender makes ----------------------------------------------------
    def reserve(self, contact, step, channel, address, extra_keys=(), now=None):
        """Check everything and write the marker BEFORE sending. Returns (True, 'ok') or (False, reason).
        Reasons: killed, suppressed, halted, already_marked, cap, no_address, guard_error."""
        try:
            k = self.killed()
            if k:
                return False, "killed"
            addr = norm_address(address)
            if not addr:
                return False, "no_address"
            if self.is_suppressed([addr, contact, *extra_keys], channel):
                return False, "suppressed"
            if self.halted(contact):
                return False, "halted"
            now = now or utcnow()
            day = now.strftime("%Y-%m-%d")
            self.db.execute("BEGIN IMMEDIATE")
            try:
                if self.db.execute("SELECT 1 FROM markers WHERE sender=? AND contact=? AND step=? AND channel=?",
                                   (self.sender, contact, str(step), channel)).fetchone():
                    self.db.execute("ROLLBACK")
                    return False, "already_marked"
                n_addr = self.db.execute("SELECT COUNT(*) FROM touches WHERE day=? AND address=? AND channel=?",
                                         (day, addr, channel)).fetchone()[0]
                n_contact = self.db.execute("SELECT COUNT(*) FROM touches WHERE day=? AND contact=?",
                                            (day, contact)).fetchone()[0]
                cap = int(self.caps.get(channel, 1))
                if n_addr >= cap or n_contact >= self.max_touches:
                    self.db.execute("ROLLBACK")
                    return False, "cap"
                self.db.execute("INSERT INTO markers VALUES (?,?,?,?,?,?,?)",
                                (self.sender, contact, str(step), channel, "sending", now.isoformat(), ""))
                self.db.execute("INSERT INTO touches VALUES (?,?,?,?,?,?)",
                                (now.isoformat(), day, self.sender, contact, addr, channel))
                self.db.execute("COMMIT")
            except Exception:
                self.db.execute("ROLLBACK")
                raise
            return True, "ok"
        except Exception as e:  # fail CLOSED: a guard problem never results in a send
            self.notify("ERROR", f"{self.sender}: guard error, nothing sent ({type(e).__name__}: {e})")
            return False, "guard_error"

    def complete(self, contact, step, channel, ok, detail=""):
        """Record the result of a send that reserve() allowed. Updates the circuit breakers.
        Returns 'ok', 'failed', 'contact_halted' or 'engine_tripped'."""
        status = "sent" if ok else "failed"
        self.db.execute("UPDATE markers SET status=?, detail=? WHERE sender=? AND contact=? AND step=? AND channel=?",
                        (status, (detail or "")[:300], self.sender, contact, str(step), channel))
        if ok:
            self.db.execute("DELETE FROM failures WHERE sender=? AND channel=? AND scope IN (?, '*')",
                            (self.sender, channel, contact))
            return "ok"
        self.notify("ERROR", f"{self.sender}: {channel} send FAILED for contact {contact}, step {step}: {detail[:200]}. "
                             f"It will NOT be retried automatically.")
        result = "failed"
        for scope in (contact, "*"):
            self.db.execute("INSERT INTO failures VALUES (?,?,?,1) ON CONFLICT(sender, scope, channel) DO UPDATE SET n=n+1",
                            (self.sender, scope, channel))
        n_contact = self.db.execute("SELECT n FROM failures WHERE sender=? AND scope=? AND channel=?",
                                    (self.sender, contact, channel)).fetchone()[0]
        n_all = self.db.execute("SELECT n FROM failures WHERE sender=? AND scope='*' AND channel=?",
                                (self.sender, channel)).fetchone()[0]
        if n_contact >= self.breaker:
            self.halt(contact, f"{n_contact} consecutive {channel} failures")
            self.notify("ERROR", f"{self.sender}: contact {contact} HALTED after {n_contact} consecutive {channel} failures.")
            result = "contact_halted"
        if n_all >= self.breaker:
            self.trip(f"{n_all} consecutive {channel} failures in a row (last: {detail[:120]})")
            result = "engine_tripped"
        return result

    def stuck(self):
        """Markers left in 'sending' (the process died mid-send). They are never re-sent; a human checks them."""
        return self.db.execute("SELECT contact, step, channel, ts FROM markers WHERE sender=? AND status='sending'",
                               (self.sender,)).fetchall()

    def summary(self):
        q = lambda sql, *a: self.db.execute(sql, a).fetchall()
        return {
            "killed": self.killed(),
            "markers": dict(q("SELECT status, COUNT(*) FROM markers WHERE sender=? GROUP BY status", self.sender)),
            "suppressed": q("SELECT COUNT(*) FROM suppression")[0][0],
            "halted": q("SELECT contact, reason FROM halted WHERE sender=?", self.sender),
            "stuck_sending": self.stuck(),
        }


def _cli():
    ap = argparse.ArgumentParser(description="Outbound guard: status, kill switch, manual suppression.")
    ap.add_argument("cmd", choices=["status", "kill", "resume", "suppress"])
    ap.add_argument("--db", help="state database file (status, suppress)")
    ap.add_argument("--dir", help="state folder (kill, resume)")
    ap.add_argument("--sender", default="", help="one sender only (default: ALL)")
    ap.add_argument("--reason", default="manual")
    ap.add_argument("--address", help="email or phone to suppress permanently")
    a = ap.parse_args()
    if a.cmd in ("kill", "resume"):
        d = a.dir or (os.path.dirname(os.path.abspath(a.db)) if a.db else None)
        if not d:
            ap.error("--dir is required")
        p = os.path.join(d, f"KILL_{a.sender}" if a.sender else "KILL_ALL")
        if a.cmd == "kill":
            os.makedirs(d, exist_ok=True)
            with open(p, "w") as f:
                f.write(f"{utcnow().isoformat()} {a.reason}\n")
            print(f"KILLED: {p} exists, nothing will send until you run 'resume'.")
        else:
            if os.path.exists(p):
                os.remove(p)
            print(f"resumed: {p} removed")
        return
    if not a.db:
        ap.error("--db is required")
    g = Guard(a.db, a.sender or "*")
    if a.cmd == "suppress":
        g.suppress([a.address], "*", a.reason)
        print(f"suppressed permanently: {norm_address(a.address)}")
        return
    rows = g.db.execute("SELECT sender, status, COUNT(*) FROM markers GROUP BY sender, status").fetchall()
    print(json.dumps({"kill_files": [f for f in os.listdir(g.dir) if f.startswith("KILL_")],
                      "markers_by_sender_status": rows,
                      "suppressed": g.db.execute("SELECT COUNT(*) FROM suppression").fetchone()[0],
                      "halted": g.db.execute("SELECT sender, contact, reason FROM halted").fetchall(),
                      "stuck_sending": g.db.execute("SELECT sender, contact, step, channel, ts FROM markers WHERE status='sending'").fetchall()},
                     indent=2))


if __name__ == "__main__":
    _cli()
