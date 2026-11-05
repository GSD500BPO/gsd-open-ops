"""Offline tests for alerts. No network. Run from the repo root:
    python3 -m unittest discover -s alerts/tests -v"""
import datetime as dt
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import alerts  # noqa: E402

T0 = dt.datetime(2026, 3, 2, 15, 0, tzinfo=dt.timezone.utc)


class Chat:
    def __init__(self, ok=True):
        self.ok, self.posts = ok, []

    def send(self, level, text):
        self.posts.append((level, text))
        return self.ok if level not in ("ERROR", "CRITICAL", "WARN") else True

    __call__ = send


class CRM:
    def __init__(self, fail=False):
        self.fail, self.tasks = fail, []

    def create_task(self, **kw):
        self.tasks.append(kw)
        if self.fail:
            raise RuntimeError("HTTP 401 token expired")
        return "ok"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="alerts-test-")
        self.cfg = os.path.join(self.tmp, "config.json")
        with open(os.path.join(os.path.dirname(HERE), "config.example.json")) as f:
            cfg = json.load(f)
        with open(self.cfg, "w") as f:
            json.dump(cfg, f)
        self.chat, self.crm = Chat(), CRM()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def make(self, live=True):
        a = alerts.Alerts(self.cfg, live=live, notifier=self.chat, crm=self.crm, out=lambda *x: None)
        self.addCleanup(a.close)
        return a

    def kinds(self, level=None):
        return [t for l, t in self.chat.posts if level is None or l == level]


class TestAlerts(Base):
    def test_dry_run_default(self):
        a = alerts.Alerts(self.cfg, out=lambda *x: None)
        self.addCleanup(a.close)
        self.assertFalse(a.live)
        self.assertIsInstance(a.crm, alerts.crmlib.DryRunCRM)
        self.assertFalse(a.notify.live)

    def test_new_lead_creates_task_and_alert_once(self):
        a = self.make()
        ev = {"id": "e1", "type": "new_lead", "lead_id": "L1", "name": "Ana", "ts": T0.isoformat()}
        a.process([ev, ev, dict(ev)], T0)
        a.process([ev], T0)
        self.assertEqual(len([t for t in self.kinds("ALERT") if t.startswith("NEW LEAD")]), 1)
        self.assertEqual(len(self.crm.tasks), 1)
        self.assertEqual(self.crm.tasks[0]["due_minutes"], 15)

    def test_score_thresholds(self):
        a = self.make()
        evs = [{"id": "n", "type": "new_lead", "lead_id": "L1", "ts": T0.isoformat()}]
        evs += [{"id": f"r{i}", "type": "reply", "lead_id": "L1", "text": f"question {i}"} for i in range(2)]   # 50
        evs += [{"id": "c1", "type": "email_click", "lead_id": "L1"}, {"id": "c2", "type": "email_click", "lead_id": "L1"}]  # 70
        a.process(evs, T0)
        self.assertEqual(a.lead("L1")["score"], 70)
        self.assertEqual(len([t for t in self.kinds() if t.startswith("HOT LEAD")]), 1)
        self.assertEqual([t for t in self.kinds() if t.startswith("CRITICAL")], [])
        a.process([{"id": "r9", "type": "reply", "lead_id": "L1", "text": "call me"}], T0)        # 95
        self.assertEqual(len([t for t in self.kinds("CRITICAL") if t.startswith("CRITICAL LEAD")]), 1)
        a.process([{"id": "c9", "type": "email_click", "lead_id": "L1"}], T0)                      # 105: no repeat
        self.assertEqual(len([t for t in self.kinds("CRITICAL") if t.startswith("CRITICAL LEAD")]), 1)

    def test_opens_are_capped(self):
        a = self.make()
        a.process([{"id": f"o{i}", "type": "email_open", "lead_id": "L1"} for i in range(50)], T0)
        self.assertEqual(a.lead("L1")["score"], 20, "opens add at most max_open_points (bots and privacy proxies open mail)")

    def test_stop_is_permanent(self):
        a = self.make()
        a.process([{"id": "n", "type": "new_lead", "lead_id": "L2", "phone": "+15550000002", "ts": T0.isoformat()},
                   {"id": "s", "type": "reply", "lead_id": "L2", "text": "STOP"}], T0)
        self.assertEqual(a.lead("L2")["status"], "stopped")
        self.assertTrue(a.guard.is_suppressed(["+15550000002"], "sms"))
        n = len(self.chat.posts)
        a.process([{"id": f"x{i}", "type": "reply", "lead_id": "L2", "text": "hello?"} for i in range(5)], T0)
        self.assertEqual(len(self.chat.posts), n, "no alerts or tasks for a stopped lead")
        a.sla(T0 + dt.timedelta(hours=2))
        self.assertEqual([t for t in self.kinds() if "L2" in t and "SPEED" in t], [])

    def test_speed_to_lead_escalates_once(self):
        a = self.make()
        a.process([{"id": "n", "type": "new_lead", "lead_id": "L3", "name": "Cara", "ts": T0.isoformat()}], T0)
        a.sla(T0 + dt.timedelta(minutes=10))
        self.assertEqual([t for t in self.kinds() if "SPEED-TO-LEAD" in t], [])
        for m in (16, 20, 60, 600):
            a.sla(T0 + dt.timedelta(minutes=m))
        self.assertEqual(len([t for t in self.kinds() if "SPEED-TO-LEAD" in t]), 1)

    def test_contacted_lead_is_not_escalated(self):
        a = self.make()
        a.process([{"id": "n", "type": "new_lead", "lead_id": "L4", "ts": T0.isoformat()},
                   {"id": "c", "type": "contacted", "lead_id": "L4", "ts": (T0 + dt.timedelta(minutes=5)).isoformat()}], T0)
        a.sla(T0 + dt.timedelta(minutes=30))
        self.assertEqual([t for t in self.kinds() if "SPEED-TO-LEAD" in t], [])

    def test_circuit_breaker_on_failing_crm(self):
        self.crm = CRM(fail=True)
        a = self.make()
        a.process([{"id": f"n{i}", "type": "new_lead", "lead_id": f"L{i}", "ts": T0.isoformat()} for i in range(10)], T0)
        self.assertEqual(len(self.crm.tasks), 2, "stops after 2 consecutive failures")
        self.assertTrue(a.guard.killed())
        a.process([{"id": "late", "type": "new_lead", "lead_id": "late", "ts": T0.isoformat()}], T0)
        self.assertEqual(len(self.crm.tasks), 2, "nothing more while tripped")

    def test_failed_alert_is_not_retried(self):
        self.crm = CRM(fail=True)
        a = self.make()
        a.cfg["circuit_breaker_failures"] = 99
        ev = {"id": "n", "type": "new_lead", "lead_id": "L5", "ts": T0.isoformat()}
        for _ in range(5):
            a.process([ev], T0)
        self.assertEqual(len(self.crm.tasks), 1)

    def test_reply_alerts_capped_per_lead_per_day(self):
        a = self.make()
        a.process([{"id": f"r{i}", "type": "reply", "lead_id": "L1", "text": f"msg {i}"} for i in range(12)], T0)
        self.assertEqual(len([t for t in self.kinds("ALERT") if t.startswith("REPLY")]), 5)

    def test_per_run_cap(self):
        a = self.make()
        a.process([{"id": f"n{i}", "type": "new_lead", "lead_id": f"L{i}", "ts": T0.isoformat()} for i in range(100)], T0)
        self.assertLessEqual(len(self.crm.tasks), 20)
        self.assertTrue(any("Unusual volume" in t for t in self.kinds("WARN")))

    def test_kill_switch(self):
        a = self.make()
        with open(os.path.join(a.state_dir, "KILL_ALL"), "w") as f:
            f.write("test")
        a.process([{"id": "n", "type": "new_lead", "lead_id": "L1", "ts": T0.isoformat()}], T0)
        self.assertEqual(self.crm.tasks, [])

    def test_field_map(self):
        with open(self.cfg) as f:
            cfg = json.load(f)
        cfg["field_map"] = {"Lead_Id": "lead_id", "Event": "type", "Full_Name": "name"}
        with open(self.cfg, "w") as f:
            json.dump(cfg, f)
        a = self.make()
        a.process([{"Lead_Id": "Z9", "Event": "new_lead", "Full_Name": "Dee"}], T0)
        self.assertEqual(a.lead("Z9")["name"], "Dee")


if __name__ == "__main__":
    unittest.main()
