"""Offline tests for the list pipeline. No network. Run from the repo root:
    python3 -m unittest discover -s data-pipeline/tests -v"""
import csv
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "sources"))
import pipeline as pl  # noqa: E402
import osm_overpass  # noqa: E402

S = os.path.join(ROOT, "samples")


def rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class TestClean(unittest.TestCase):
    def test_phone(self):
        self.assertEqual(pl.clean_phone("(555) 010-0001")[0], "+15550100001")
        self.assertEqual(pl.clean_phone("1-555-010-0001 ext 22")[0], "+15550100001")
        self.assertEqual(pl.clean_phone("+57 300 123 4567")[0], "+573001234567")
        self.assertEqual(pl.clean_phone("12345")[0], "")

    def test_email(self):
        self.assertEqual(pl.clean_email(" MAILTO:Info@Example.COM ")[0], "info@example.com")
        self.assertEqual(pl.clean_email("not-an-email")[0], "")

    def test_website_and_state(self):
        self.assertEqual(pl.clean_website("WWW.Example.com/")[1], "example.com")
        r = pl.clean({**{f: "" for f in pl.FIELDS}, "company": "ACME WATER LLC", "state": "texas",
                      "website": "facebook.com/acme"})
        self.assertEqual(r["state"], "TX")
        self.assertEqual(r["company"], "Acme Water LLC")
        self.assertEqual(r["website"], "", "a social profile is not a company website")


class TestRun(unittest.TestCase):
    def setUp(self):
        self.out = tempfile.mkdtemp(prefix="pipeline-test-")

    def tearDown(self):
        shutil.rmtree(self.out, ignore_errors=True)

    def test_full_run(self):
        st = pl.run([os.path.join(S, "registry-export.example.csv"), os.path.join(S, "manual-research.example.csv")],
                    os.path.join(ROOT, "profiles", "generic.json"), self.out,
                    existing=[os.path.join(S, "crm-export.example.csv")],
                    suppression=[os.path.join(S, "suppression.example.csv")])
        self.assertEqual(st["rows_in"], 9)
        self.assertEqual(st["duplicates_merged"], 2, "3 rows of the same business become 1")
        self.assertEqual(st["already_in_crm"], 1)
        self.assertEqual(st["suppressed"], 1)
        clean = rows(os.path.join(self.out, "clean.csv"))
        ex = [r for r in clean if r["company"] == "Example Water Solutions"]
        self.assertEqual(len(ex), 1)
        self.assertEqual(ex[0]["email"], "ana@example.com", "a person's email beats info@")
        self.assertEqual(ex[0]["industry"], "Water Treatment")
        self.assertTrue(ex[0]["timezone"].startswith("America/Chicago"))
        agua = [r for r in clean if r["company"].startswith("Servicios")][0]
        self.assertEqual(agua["language_hint"], "es?")
        for name in ("zoho_leads.csv", "gohighlevel_contacts.csv", "hubspot_contacts.csv"):
            self.assertEqual(len(rows(os.path.join(self.out, name))), st["ready_to_import"])
        z = rows(os.path.join(self.out, "zoho_leads.csv"))
        self.assertTrue(all(r["Last Name"] for r in z), "Zoho Leads needs a Last Name on every row")
        removed = {r["company"]: r["removed_reason"] for r in rows(os.path.join(self.out, "removed.csv"))}
        self.assertEqual(removed["Demo Heating and Air"], "on suppression / do-not-contact list")
        all_phones = {r["phone"] for r in clean}
        self.assertNotIn("+15550100003", all_phones, "suppressed numbers never reach the CRM files")

    def test_fuzzy_dedupe(self):
        base = {f: "" for f in pl.FIELDS}
        recs = [pl.clean({**base, "company": "A.B.C. Water Company", "city": "Austin", "state": "TX", "phone": "5550100009"}),
                pl.clean({**base, "company": "ABC Water Co", "city": "Austin", "state": "TX", "email": "x@abc.example"}),
                pl.clean({**base, "company": "ABC Water Co", "city": "Dallas", "state": "TX", "email": "y@abc2.example"})]
        self.assertEqual(len(pl.dedupe(recs)), 2, "same name in another city is a different business")


class TestOSM(unittest.TestCase):
    def test_query_only_by_default(self):
        q = osm_overpass.build_query("craft=plumber", area="Austin")
        self.assertIn('["craft"="plumber"]', q)
        with self.assertRaises(SystemExit):
            osm_overpass.build_query('craft"];out;', area="Austin")

    def test_rows(self):
        data = {"elements": [{"type": "node", "id": 1, "tags": {"name": "Example Plumbing", "phone": "555-010-0001",
                                                               "addr:city": "Austin"}},
                             {"type": "node", "id": 2, "tags": {}}]}
        r = osm_overpass.to_rows(data, "craft=plumber")
        self.assertEqual(len(r), 1)
        self.assertIn("OpenStreetMap", r[0]["attribution"])


if __name__ == "__main__":
    unittest.main()
