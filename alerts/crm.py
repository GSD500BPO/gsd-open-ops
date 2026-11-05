"""CRM task adapters for alerts. One method: create_task(lead_id, subject, due_minutes, priority, description, idempotency_key).

  dryrun   prints the task, creates nothing (always used without --live)
  webhook  POSTs JSON to a URL you control. Point it at something that can create a task in your CRM:
           a Zoho CRM function exposed as a REST API, a Zoho Flow / n8n / Make / Zapier webhook,
           a GoHighLevel workflow with an inbound-webhook trigger, or a HubSpot workflow webhook trigger.
           (Check your plan: inbound webhook triggers are not on every plan of every CRM.)

Writing a direct adapter for your CRM's API is fine too: keep the same method signature and raise on any error.
"""
import hashlib
import hmac
import json
import os
import urllib.request


class DryRunCRM:
    def __init__(self, out=print):
        self.out = out
        self.tasks = []

    def create_task(self, lead_id, subject, due_minutes, priority, description, idempotency_key=""):
        self.tasks.append({"lead_id": lead_id, "subject": subject, "due_minutes": due_minutes, "priority": priority})
        self.out(f"[DRY RUN] CRM task for {lead_id}: {subject} (due in {due_minutes} min, {priority})")
        return "dry-run"


class WebhookCRM:
    def __init__(self, cfg):
        self.url = cfg.get("url") or os.environ.get("CRM_TASK_WEBHOOK_URL", "")
        self.secret = os.environ.get("WEBHOOK_SECRET", "")
        if not self.url:
            raise RuntimeError("CRM_TASK_WEBHOOK_URL is not set")

    def create_task(self, lead_id, subject, due_minutes, priority, description, idempotency_key=""):
        body = json.dumps({"action": "create_task", "lead_id": lead_id, "subject": subject, "due_minutes": due_minutes,
                           "priority": priority, "description": description, "idempotency_key": idempotency_key}).encode()
        headers = {"Content-Type": "application/json", "Idempotency-Key": idempotency_key}
        if self.secret:
            headers["X-Signature-SHA256"] = hmac.new(self.secret.encode(), body, hashlib.sha256).hexdigest()
        req = urllib.request.Request(self.url, data=body, method="POST", headers=headers)
        with urllib.request.urlopen(req, timeout=20) as r:
            if not 200 <= r.status < 300:
                raise RuntimeError(f"CRM webhook HTTP {r.status}")
            return f"HTTP {r.status}"


def build(cfg, live, out=print):
    if not live or (cfg or {}).get("type", "dryrun") == "dryrun":
        return DryRunCRM(out)
    if cfg.get("type") == "webhook":
        return WebhookCRM(cfg)
    raise RuntimeError(f"unknown crm type {cfg.get('type')!r}")
