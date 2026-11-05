"""Team-chat notifier used by every runner for errors, halts and hot-lead alerts.

Every message is ALWAYS appended to <state>/alerts.log first, so nothing is silent even if the chat is down.
In dry-run mode nothing is posted; the message is printed and logged.
In live mode it POSTs JSON to ALERT_WEBHOOK_URL (an "incoming webhook" URL from your team chat).

ALERT_WEBHOOK_FORMAT picks the JSON shape:
  text     {"text": "..."}      Slack incoming webhooks, Google Chat, Mattermost, Rocket.Chat, Zoho Cliq channel webhooks
  discord  {"content": "..."}   Discord webhooks
  generic  {"level": "...", "text": "...", "source": "..."}   your own endpoint, n8n, Make, Zapier catch hooks
"""
import datetime as dt
import json
import os
import sys
import urllib.request


class Notifier:
    def __init__(self, log_path, live=False, webhook_url=None, fmt=None, source="gsd-open-ops", timeout=15):
        self.log_path = log_path
        self.live = live
        self.url = webhook_url if webhook_url is not None else os.environ.get("ALERT_WEBHOOK_URL", "")
        self.fmt = (fmt or os.environ.get("ALERT_WEBHOOK_FORMAT", "text")).lower()
        self.source = source
        self.timeout = timeout
        self.posted = []          # what was (or would have been) posted, for tests and dry-run summaries
        self.failures = 0
        os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)

    def _log(self, line):
        with open(self.log_path, "a") as f:
            f.write(line + "\n")

    def __call__(self, level, text):
        return self.send(level, text)

    def send(self, level, text):
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        line = f"{stamp} [{level}] {self.source}: {text}"
        self._log(line)
        print(line, file=sys.stderr)
        self.posted.append((level, text))
        if not self.live:
            return True
        if not self.url:
            self._log(f"{stamp} [WARN] {self.source}: ALERT_WEBHOOK_URL is empty, alert only in alerts.log")
            return False
        body = {"content": f"[{level}] {text}"} if self.fmt == "discord" else (
            {"level": level, "text": text, "source": self.source} if self.fmt == "generic" else {"text": f"[{level}] {text}"})
        try:
            req = urllib.request.Request(self.url, data=json.dumps(body).encode(), method="POST",
                                         headers={"Content-Type": "application/json", "User-Agent": "gsd-open-ops/1.0"})
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                ok = 200 <= r.status < 300
        except Exception as e:  # never raise from the notifier; log loudly instead
            ok = False
            self._log(f"{stamp} [ERROR] {self.source}: could not post alert ({type(e).__name__}: {e})")
        if not ok:
            self.failures += 1
        return ok
