"""Send adapters. Each one has a single method: send(to, subject, body, meta) -> provider message id (str).
Any problem raises an exception; the engine records it as a failure and NEVER retries it automatically.

  dryrun   prints the message, sends nothing (always used without --live)
  smtp     email over SMTP with STARTTLS (standard library smtplib)
  twilio   SMS through the Twilio Messages REST API
  webhook  POSTs JSON to a URL you control (your CRM workflow, n8n, Make, Zapier) and lets it do the sending
"""
import base64
import hashlib
import hmac
import json
import os
import smtplib
import urllib.parse
import urllib.request
from email.message import EmailMessage
from email.utils import formataddr, make_msgid


class DryRun:
    def __init__(self, channel, out=print):
        self.channel = channel
        self.out = out
        self.sent = []

    def send(self, to, subject, body, meta):
        self.sent.append((to, subject, body, meta))
        head = f"[DRY RUN] {self.channel} -> {to} | {meta.get('step')}"
        self.out(head + (f" | {subject}" if subject else ""))
        self.out("    " + body.strip().replace("\n", "\n    ")[:600])
        return "dry-run"


class SMTP:
    def __init__(self, cfg):
        self.host = os.environ.get("SMTP_HOST", "")
        self.port = int(os.environ.get("SMTP_PORT", "587"))
        self.user = os.environ.get("SMTP_USER", "")
        self.password = os.environ.get("SMTP_PASSWORD", "")
        self.from_email = cfg["from_email"]
        self.from_name = cfg.get("from_name", "")
        self.reply_to = cfg.get("reply_to", "")
        if not (self.host and self.user and self.password):
            raise RuntimeError("SMTP_HOST, SMTP_USER and SMTP_PASSWORD must be set for live email")

    def send(self, to, subject, body, meta):
        m = EmailMessage()
        m["From"] = formataddr((self.from_name, self.from_email))
        m["To"] = to
        m["Subject"] = subject
        m["Message-ID"] = make_msgid()
        if self.reply_to:
            m["Reply-To"] = self.reply_to
        if meta.get("unsubscribe_link"):
            m["List-Unsubscribe"] = f"<{meta['unsubscribe_link']}>"
        m.set_content(body)
        with smtplib.SMTP(self.host, self.port, timeout=30) as s:
            s.starttls()
            s.login(self.user, self.password)
            s.send_message(m)
        return m["Message-ID"]


class Twilio:
    def __init__(self, cfg):
        self.sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
        self.token = os.environ.get("TWILIO_AUTH_TOKEN", "")
        self.from_number = cfg.get("from_number", "")
        self.messaging_service = cfg.get("messaging_service_sid", "")
        if not (self.sid and self.token and (self.from_number or self.messaging_service)):
            raise RuntimeError("TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and a from_number (or messaging_service_sid) are required")

    def send(self, to, subject, body, meta):
        data = {"To": to, "Body": body}
        data.update({"MessagingServiceSid": self.messaging_service} if self.messaging_service else {"From": self.from_number})
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.sid}/Messages.json"
        auth = base64.b64encode(f"{self.sid}:{self.token}".encode()).decode()
        req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(), method="POST",
                                     headers={"Authorization": "Basic " + auth})
        with urllib.request.urlopen(req, timeout=30) as r:   # raises on 4xx/5xx (401, 402-style billing, 429...)
            return json.load(r).get("sid", "")


class Webhook:
    def __init__(self, channel, cfg):
        self.url = cfg.get("url") or os.environ.get(f"{channel.upper()}_WEBHOOK_URL", "")
        self.secret = os.environ.get("WEBHOOK_SECRET", "")
        self.channel = channel
        if not self.url:
            raise RuntimeError(f"{channel.upper()}_WEBHOOK_URL is not set")

    def send(self, to, subject, body, meta):
        payload = json.dumps({"channel": self.channel, "to": to, "subject": subject, "body": body,
                              "contact_id": meta.get("contact_id"), "step": meta.get("step"),
                              "idempotency_key": meta.get("idempotency_key")}).encode()
        headers = {"Content-Type": "application/json", "Idempotency-Key": meta.get("idempotency_key", "")}
        if self.secret:
            headers["X-Signature-SHA256"] = hmac.new(self.secret.encode(), payload, hashlib.sha256).hexdigest()
        req = urllib.request.Request(self.url, data=payload, method="POST", headers=headers)
        with urllib.request.urlopen(req, timeout=30) as r:
            if not 200 <= r.status < 300:
                raise RuntimeError(f"webhook HTTP {r.status}")
            return r.headers.get("X-Message-Id", "webhook-ok")


def build(channel, cfg, live, out=print):
    if not live:
        return DryRun(channel, out)
    kind = (cfg or {}).get("type", "")
    if channel == "email" and kind == "smtp":
        return SMTP(cfg)
    if channel == "sms" and kind == "twilio":
        return Twilio(cfg)
    if kind == "webhook":
        return Webhook(channel, cfg)
    raise RuntimeError(f"no live provider configured for {channel} (type={kind!r})")
