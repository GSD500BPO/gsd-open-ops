"""Offline tests for the 24-step engine. No network, no real providers.
Run from the repo root:  python3 -m unittest discover -s journeys/24-step/tests -v

Every test works in a fresh temporary folder, so your real state/ is never touched."""
import datetime as dt
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE_DIR = os.path.dirname(HERE)
sys.path.insert(0, ENGINE_DIR)
import engine  # noqa: E402

T0 = dt.datetime(2026, 3, 2, 15, 0, tzinfo=dt.timezone.utc)   # a Monday, 10:00 in New York


def rj(path):
    with open(path) as f:
        return json.load(f)


def wj(obj, path):
    with open(path, "w") as f:
        json.dump(obj, f)


class FakeProvider:
    """Records every send. fail_with=Exception makes every send fail (out of credits, 429, 401...)."""
    def __init__(self, fail_with=None):
        self.calls = []
        self.fail_with = fail_with

    def send(self, to, subject, body, meta):
        self.calls.append((to, meta["step"]))
        if self.fail_with:
            raise self.fail_with
        return f"id-{len(self.calls)}"


class Quiet:
    def __init__(self):
        self.lines = []

    def __call__(self, level, text):
        self.lines.append((level, text))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="journey-test-")
        shutil.copy(os.path.join(ENGINE_DIR, "journey.json"), self.tmp)
        shutil.copytree(os.path.join(ENGINE_DIR, "templates"), os.path.join(self.tmp, "templates"))
        cfg = rj(os.path.join(ENGINE_DIR, "config.example.json"))
        self.cfg_path = os.path.join(self.tmp, "config.json")
        wj(cfg, self.cfg_path)
        with open(os.path.join(self.tmp, "contacts.csv"), "w") as f:
            f.write("id,first_name,company,email,phone,city,state,sms_consent,do_not_contact\n"
                    "c-1,Ana,Example Co,ana@example.com,+15550000001,Austin,TX,yes,no\n"
                    "c-2,Ben,Sample Co,ben@example.com,+15550000002,Tampa,FL,yes,no\n")
        self.email, self.sms, self.alerts = FakeProvider(), FakeProvider(), Quiet()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def make(self, live=True):
        # live=True exercises the live code path, but with fake providers: nothing leaves this machine
        e = engine.Engine(self.cfg_path, live=live, out=lambda *a: None, notifier=self.alerts,
                          provider_overrides={"email": self.email, "sms": self.sms})
        self.addCleanup(e.close)
        return e


class TestSafety(Base):

    def test_dry_run_is_default_and_sends_nothing(self):
        e = engine.Engine(self.cfg_path, out=lambda *a: None, notifier=self.alerts)
        self.addCleanup(e.close)
        self.assertFalse(e.live)
        self.assertTrue(e.db_path.endswith("dry-run.db"))
        self.assertIsInstance(e.provider("email"), engine.providerlib.DryRun)

    def test_failing_sms_does_not_resend_email(self):
        """The incident: email goes out, SMS fails, the scheduler runs again and again. Email must go out ONCE."""
        self.sms = FakeProvider(fail_with=RuntimeError("HTTP 402: out of credits"))
        e = self.make()
        e.enroll(os.path.join(self.tmp, "contacts.csv"), T0)
        for i in range(10):                                    # a cron every 2 minutes, 10 times
            e.run(T0 + dt.timedelta(minutes=2 * i))
        emails_step1 = [c for c in self.email.calls if c[1] == "step-01"]
        self.assertEqual(len([c for c in emails_step1 if c[0] == "ana@example.com"]), 1)
        self.assertEqual(len([c for c in emails_step1 if c[0] == "ben@example.com"]), 1)
        self.assertLessEqual(len(self.sms.calls), 2, "a failed text is never retried automatically")
        self.assertTrue(any(l == "ERROR" for l, _ in self.alerts.lines), "failures must raise an alert")

    def test_circuit_breaker_trips_after_two_consecutive_failures(self):
        self.sms = FakeProvider(fail_with=RuntimeError("HTTP 429"))
        e = self.make()
        e.enroll(os.path.join(self.tmp, "contacts.csv"), T0)
        e.run(T0)
        self.assertTrue(e.guard.killed(), "two failed texts in a row must stop the engine")
        self.assertTrue(any(l == "CRITICAL" for l, _ in self.alerts.lines))
        before = len(self.email.calls) + len(self.sms.calls)
        e.run(T0 + dt.timedelta(days=3))
        self.assertEqual(len(self.email.calls) + len(self.sms.calls), before, "nothing sends while tripped")

    def test_stop_stops_everything_forever(self):
        e = self.make()
        e.enroll(os.path.join(self.tmp, "contacts.csv"), T0)
        e.run(T0)
        self.assertEqual(e.inbound("+1 (555) 000-0001", "STOP"), "stopped")
        before = [c for c in self.email.calls + self.sms.calls if c[0] in ("ana@example.com", "+15550000001")]
        for d in range(1, 100, 2):                             # run through the whole 90-day journey
            e.run(T0 + dt.timedelta(days=d))
        after = [c for c in self.email.calls + self.sms.calls if c[0] in ("ana@example.com", "+15550000001")]
        self.assertEqual(before, after, "no message of any channel after STOP")
        self.assertEqual(e.contact("c-1")["_status"], "stopped")
        # never re-enrolled, even from a fresh CSV with a new id
        with open(os.path.join(self.tmp, "again.csv"), "w") as f:
            f.write("id,email,phone,sms_consent\nnew-id,ana@example.com,+15550000001,yes\n")
        added, _ = e.enroll(os.path.join(self.tmp, "again.csv"), T0 + dt.timedelta(days=100))
        self.assertEqual(added, 0)

    def test_spanish_stop_words(self):
        for word in ("STOP", "Baja", "no me escriban", "unsubscribe", "Remove me please", "alto"):
            self.assertTrue(engine.guardlib.is_stop(word), word)
        self.assertFalse(engine.guardlib.is_stop("yes, call me tomorrow"))

    def test_reply_pauses_and_alerts(self):
        e = self.make()
        e.enroll(os.path.join(self.tmp, "contacts.csv"), T0)
        e.run(T0)
        e.inbound("ben@example.com", "Sounds interesting, call me Tuesday", "email")
        self.assertEqual(e.contact("c-2")["_status"], "replied")
        n = len([c for c in self.email.calls if c[0] == "ben@example.com"])
        e.run(T0 + dt.timedelta(days=10))
        self.assertEqual(len([c for c in self.email.calls if c[0] == "ben@example.com"]), n)
        self.assertTrue(any(l == "ALERT" and "REPLY" in t for l, t in self.alerts.lines))
        with open(e.events_out) as f:
            events = [json.loads(l) for l in f]
        self.assertEqual(events[-1]["type"], "reply")

    def test_caps_hold(self):
        """Two contacts share one email address (duplicate rows). Cap = 1 email per address per day."""
        with open(os.path.join(self.tmp, "dupes.csv"), "w") as f:
            f.write("id,email\nd-1,same@example.com\nd-2,same@example.com\nd-3,same@example.com\n")
        e = self.make()
        e.enroll(os.path.join(self.tmp, "dupes.csv"), T0)
        for i in range(5):
            e.run(T0 + dt.timedelta(minutes=10 * i))
        self.assertEqual(len([c for c in self.email.calls if c[0] == "same@example.com"]), 1)

    def test_touches_per_contact_per_day(self):
        e = self.make()
        e.enroll(os.path.join(self.tmp, "contacts.csv"), T0)
        # force a contact to be due for step 2 on the same day it got step 1
        e.run(T0)
        e.db.execute("UPDATE contacts SET next_due=? WHERE id='c-1'", (T0.isoformat(),))
        e.run(T0 + dt.timedelta(minutes=5))
        today = [c for c in self.email.calls + self.sms.calls if c[0] in ("ana@example.com", "+15550000001")]
        self.assertLessEqual(len(today), 2, "max 2 touches per contact per day")

    def test_kill_switch(self):
        e = self.make()
        e.enroll(os.path.join(self.tmp, "contacts.csv"), T0)
        with open(os.path.join(e.state_dir, "KILL_ALL"), "w") as f:
            f.write("testing")
        e.run(T0)
        self.assertEqual(self.email.calls + self.sms.calls, [])

    def test_no_sms_without_consent(self):
        with open(os.path.join(self.tmp, "nc.csv"), "w") as f:
            f.write("id,email,phone,sms_consent\nn-1,n@example.com,+15550000009,no\n")
        e = self.make()
        e.enroll(os.path.join(self.tmp, "nc.csv"), T0)
        e.run(T0)
        self.assertEqual([c for c in self.sms.calls if c[0] == "+15550000009"], [])
        self.assertEqual(len([c for c in self.email.calls if c[0] == "n@example.com"]), 1)

    def test_full_journey_sends_each_step_once(self):
        e = self.make()
        e.enroll(os.path.join(self.tmp, "contacts.csv"), T0)
        for h in range(0, 24 * 100, 6):                         # every 6 hours for 100 days
            e.run(T0 + dt.timedelta(hours=h), ignore_window=False)
        ana = [s for to, s in self.email.calls if to == "ana@example.com"]
        self.assertEqual(len(ana), 24)
        self.assertEqual(len(set(ana)), 24, "each step's email exactly once")
        self.assertEqual(e.contact("c-1")["_status"], "completed")

    def test_unfilled_placeholder_is_never_sent(self):
        cfg = rj(self.cfg_path)
        cfg["merge"].pop("booking_link")
        wj(cfg, self.cfg_path)
        e = self.make()
        e.enroll(os.path.join(self.tmp, "contacts.csv"), T0)
        e.run(T0)
        self.assertEqual(self.email.calls, [], "step 1 uses {{booking_link}}; a broken message is skipped, not sent")
        self.assertTrue(e.check())

    def test_live_check_refuses_example_config(self):
        e = engine.Engine(self.cfg_path, live=True, out=lambda *a: None, notifier=self.alerts)
        self.addCleanup(e.close)
        self.assertTrue(any("CHANGE-ME" in p for p in e.check()))


if __name__ == "__main__":
    unittest.main()
