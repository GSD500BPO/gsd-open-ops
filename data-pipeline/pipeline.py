#!/usr/bin/env python3
"""List pipeline: business data you are allowed to use -> clean -> dedupe -> enrich -> CRM-ready CSV.
Python 3.9+, standard library only. It reads and writes local files. It never contacts anyone and never scrapes.

  python3 pipeline.py run samples/registry-export.example.csv samples/manual-research.example.csv --out out
  python3 pipeline.py run my.csv --profile profiles/generic.json --existing crm-export.csv --suppression stop-list.csv
  python3 pipeline.py template research.csv          # blank CSV for manual research (the columns we expect)

Output (in --out):
  clean.csv                 every kept record, canonical columns + quality fields
  zoho_leads.csv            ready rows, Zoho CRM Leads import columns
  gohighlevel_contacts.csv  ready rows, GoHighLevel contacts import columns
  hubspot_contacts.csv      ready rows, HubSpot contacts import columns
  removed.csv               rows dropped (duplicate of an existing CRM record, suppressed, unusable) and why
  report.md                 counts, so you can check before importing
"""
import argparse
import csv
import datetime as dt
import difflib
import json
import os
import re
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))

FIELDS = ["company", "first_name", "last_name", "title", "email", "phone", "website", "street", "city", "state", "zip",
          "country", "industry", "language", "source", "source_url", "collected_on", "notes", "sms_consent"]
EXTRA = ["domain", "timezone", "email_type", "language_hint", "quality", "ready", "issues", "dup_count", "merged_sources"]

STATES = {"alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA", "colorado": "CO",
          "connecticut": "CT", "delaware": "DE", "district of columbia": "DC", "florida": "FL", "georgia": "GA",
          "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
          "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD", "massachusetts": "MA", "michigan": "MI",
          "minnesota": "MN", "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
          "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY", "north carolina": "NC",
          "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
          "rhode island": "RI", "south carolina": "SC", "south dakota": "SD", "tennessee": "TN", "texas": "TX",
          "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
          "wisconsin": "WI", "wyoming": "WY", "puerto rico": "PR"}
# Main time zone per state. States split across zones are marked with * (check the city).
TZ = {"AL": "America/Chicago", "AK": "America/Anchorage", "AZ": "America/Phoenix", "AR": "America/Chicago",
      "CA": "America/Los_Angeles", "CO": "America/Denver", "CT": "America/New_York", "DE": "America/New_York",
      "DC": "America/New_York", "FL": "America/New_York*", "GA": "America/New_York", "HI": "Pacific/Honolulu",
      "ID": "America/Boise*", "IL": "America/Chicago", "IN": "America/Indiana/Indianapolis*", "IA": "America/Chicago",
      "KS": "America/Chicago*", "KY": "America/New_York*", "LA": "America/Chicago", "ME": "America/New_York",
      "MD": "America/New_York", "MA": "America/New_York", "MI": "America/Detroit*", "MN": "America/Chicago",
      "MS": "America/Chicago", "MO": "America/Chicago", "MT": "America/Denver", "NE": "America/Chicago*",
      "NV": "America/Los_Angeles", "NH": "America/New_York", "NJ": "America/New_York", "NM": "America/Denver",
      "NY": "America/New_York", "NC": "America/New_York", "ND": "America/Chicago*", "OH": "America/New_York",
      "OK": "America/Chicago", "OR": "America/Los_Angeles*", "PA": "America/New_York", "RI": "America/New_York",
      "SC": "America/New_York", "SD": "America/Chicago*", "TN": "America/Chicago*", "TX": "America/Chicago*",
      "UT": "America/Denver", "VT": "America/New_York", "VA": "America/New_York", "WA": "America/Los_Angeles",
      "WV": "America/New_York", "WI": "America/Chicago", "WY": "America/Denver", "PR": "America/Puerto_Rico"}
FREEMAIL = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "icloud.com", "live.com", "msn.com",
            "comcast.net", "att.net", "sbcglobal.net", "verizon.net", "me.com", "ymail.com", "protonmail.com", "gmx.com"}
NOT_A_COMPANY_SITE = {"facebook.com", "instagram.com", "linkedin.com", "yelp.com", "google.com", "business.site",
                      "wixsite.com", "x.com", "twitter.com", "tiktok.com", "youtube.com", "nextdoor.com", "angi.com",
                      "homeadvisor.com", "bbb.org", "linktr.ee"}
ROLE = {"info", "office", "sales", "contact", "hello", "admin", "support", "service", "team", "help", "billing",
        "accounts", "marketing", "jobs", "careers", "hr"}
SPANISH_HINTS = re.compile(r"\b(agua|servicios?|limpieza|construcci[oó]n|hermanos|plomer[ií]a|techos|el|la|los|las|y|"
                           r"latino|hispan[oa]|mi casa|nuestra|soluciones|pura)\b", re.I)
EMAIL_RE = re.compile(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$")
SUFFIX_RE = re.compile(r"\b(llc|inc|incorporated|corp|corporation|co|company|ltd|pllc|lp|the)\b\.?", re.I)


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, cols):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def load_profile(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---- 1. ingest ------------------------------------------------------------------------------------
def ingest(rows, profile, source_name):
    """Map whatever columns the file has onto our canonical fields using the profile's column aliases."""
    aliases = {k: [a.lower() for a in v] for k, v in profile.get("columns", {}).items()}
    out = []
    for r in rows:
        low = {(k or "").strip().lower(): (v or "") for k, v in r.items()}
        rec = {f: "" for f in FIELDS}
        for f in FIELDS:
            for a in [f] + aliases.get(f, []):
                if low.get(a, "").strip():
                    rec[f] = low[a]
                    break
        if not rec["first_name"] and not rec["last_name"] and low.get("contact name"):
            parts = low["contact name"].split()
            rec["first_name"], rec["last_name"] = parts[0], " ".join(parts[1:])
        rec["source"] = rec["source"] or profile.get("source", source_name)
        rec["_category"] = " ".join(low.get(a, "") for a in profile.get("category_columns", []))
        out.append(rec)
    return out


# ---- 2. clean -------------------------------------------------------------------------------------
def clean_phone(p):
    raw = (p or "").strip()
    if not raw:
        return "", None
    raw = re.split(r"\s*(?:ext\.?|x|#)\s*\d+$", raw, flags=re.I)[0]
    d = re.sub(r"\D", "", raw)
    if len(d) == 10 and d[0] not in "01":
        return "+1" + d, None
    if len(d) == 11 and d[0] == "1" and d[1] not in "01":
        return "+" + d, None
    if raw.startswith("+") and 8 <= len(d) <= 15:
        return "+" + d, None
    return "", f"bad phone '{p}'"


def clean_email(e):
    e = (e or "").strip().lower().replace("mailto:", "").strip(" .;,<>")
    if not e:
        return "", None
    e = e.split("?")[0]
    if EMAIL_RE.match(e) and ".." not in e:
        return e, None
    return "", f"bad email '{e}'"


def clean_website(w):
    w = (w or "").strip()
    if not w:
        return "", ""
    if not re.match(r"^https?://", w, re.I):
        w = "https://" + w
    u = urllib.parse.urlparse(w)
    host = (u.netloc or "").lower().split("@")[-1].split(":")[0]
    host = host[4:] if host.startswith("www.") else host
    if "." not in host:
        return "", ""
    return f"https://{host}{u.path.rstrip('/')}", host


UPPER_WORDS = {"Llc": "LLC", "Pllc": "PLLC", "Lp": "LP", "Hvac": "HVAC", "Usa": "USA", "Ro": "RO"}


def tidy(s):
    s = re.sub(r"\s+", " ", (s or "").strip())
    if s and (s.isupper() or s.islower()) and len(s) > 3:
        s = " ".join(UPPER_WORDS.get(w, w) for w in s.title().split(" "))
    return s


def clean(rec):
    issues = []
    for f in FIELDS:
        rec[f] = re.sub(r"\s+", " ", (rec.get(f) or "").strip())
    rec["company"] = tidy(rec["company"])
    rec["first_name"], rec["last_name"], rec["city"] = tidy(rec["first_name"]), tidy(rec["last_name"]), tidy(rec["city"])
    rec["email"], err = clean_email(rec["email"]); err and issues.append(err)
    rec["phone"], err = clean_phone(rec["phone"]); err and issues.append(err)
    rec["website"], rec["domain"] = clean_website(rec["website"])
    if rec["domain"] and (rec["domain"] in NOT_A_COMPANY_SITE or any(rec["domain"].endswith("." + x) for x in NOT_A_COMPANY_SITE)):
        rec["notes"] = (rec["notes"] + f" | profile page: {rec['website']}").strip(" |")   # a social page is not a website
        rec["website"], rec["domain"] = "", ""
    st = rec["state"].strip()
    rec["state"] = st.upper() if len(st) == 2 else STATES.get(st.lower(), st)
    z = re.match(r"^\d{5}", rec["zip"])
    rec["zip"] = z.group(0) if z else rec["zip"]
    rec["sms_consent"] = "yes" if rec["sms_consent"].lower() in ("yes", "y", "true", "1") else "no"
    rec["collected_on"] = rec["collected_on"] or dt.date.today().isoformat()
    rec["issues"] = "; ".join(issues)
    return rec


# ---- 3. dedupe ------------------------------------------------------------------------------------
def name_key(company):
    k = re.sub(r"[.'’]", "", (company or "").lower()).replace("&", " and ")   # "A.B.C." -> "abc"
    k = SUFFIX_RE.sub(" ", k)
    k = re.sub(r"[^a-z0-9 ]", " ", k)
    return re.sub(r"\s+", " ", k).strip()


def match_keys(r):
    keys = []
    if r["email"]:
        keys.append("e:" + r["email"])
    if r["phone"]:
        keys.append("p:" + r["phone"])
    if r["domain"] and r["domain"] not in NOT_A_COMPANY_SITE and not any(r["domain"].endswith("." + s) for s in NOT_A_COMPANY_SITE):
        keys.append("d:" + r["domain"])
    nk = name_key(r["company"])
    if nk:
        keys.append(f"n:{nk}|{r['city'].lower()}|{r['state'].lower()}")
    return keys


def dedupe(records, fuzzy=0.92):
    parent = list(range(len(records)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        parent[find(i)] = find(j)

    seen = {}
    for i, r in enumerate(records):
        for k in match_keys(r):
            if k in seen:
                union(i, seen[k])
            else:
                seen[k] = i
    # fuzzy company names inside the same city + state ("ABC Water Co" vs "A.B.C. Water Company")
    by_place = {}
    for i, r in enumerate(records):
        by_place.setdefault((r["city"].lower(), r["state"].lower()), []).append(i)
    for idx in by_place.values():
        for a in range(len(idx)):
            for b in range(a + 1, len(idx)):
                na, nb = name_key(records[idx[a]]["company"]), name_key(records[idx[b]]["company"])
                if na and nb and difflib.SequenceMatcher(None, na, nb).ratio() >= fuzzy:
                    union(idx[a], idx[b])
    groups = {}
    for i in range(len(records)):
        groups.setdefault(find(i), []).append(i)
    def email_rank(e):
        if not e:
            return 9
        local, dom = e.split("@", 1)
        return 2 if dom in FREEMAIL else (1 if local in ROLE else 0)

    out = []
    for members in groups.values():
        members.sort(key=lambda m: email_rank(records[m]["email"]))       # best email first: person > role > freemail
        base = dict(records[members[0]])
        for m in members[1:]:
            for f in FIELDS + ["domain"]:
                if not base.get(f) and records[m].get(f):
                    base[f] = records[m][f]
            other = records[m]["email"]
            if other and other != base["email"] and other not in base["notes"]:
                base["notes"] = (base["notes"] + f" | also: {other}").strip(" |")
            if records[m].get("_category"):
                base["_category"] = (base.get("_category", "") + " " + records[m]["_category"]).strip()
        base["dup_count"] = str(len(members))
        base["merged_sources"] = ";".join(sorted({records[m]["source"] for m in members if records[m]["source"]}))
        base["issues"] = "; ".join(sorted({x for m in members for x in records[m].get("issues", "").split("; ") if x}))
        out.append(base)
    return out


# ---- 4. enrich (offline: no paid APIs, no scraping) -----------------------------------------------
def enrich(r, profile):
    r["timezone"] = TZ.get(r["state"], "")
    if r["email"]:
        local, dom = r["email"].split("@", 1)
        r["email_type"] = "freemail" if dom in FREEMAIL else ("role" if local in ROLE else "person")
        if not r["website"] and dom not in FREEMAIL:
            r["website"], r["domain"] = clean_website(dom)
    else:
        r["email_type"] = ""
    if not r["industry"]:
        text = f"{r['company']} {r.get('_category', '')} {r['notes']}".lower()
        for industry, words in profile.get("industry_keywords", {}).items():
            if any(re.search(r"\b" + re.escape(w.lower()) + r"\b", text) for w in words):
                r["industry"] = industry
                break
    r["language_hint"] = "" if r["language"] else ("es?" if SPANISH_HINTS.search(r["company"]) else "")
    q = 0
    q += 30 if r["phone"] else 0
    q += 30 if r["email"] else 0
    q += 5 if r["email_type"] == "person" else 0
    q += 10 if r["website"] else 0
    q += 10 if r["city"] and r["state"] else 0
    q += 10 if r["industry"] else 0
    q += 5 if r["first_name"] or r["last_name"] else 0
    r["quality"] = str(min(q, 100))
    r["ready"] = "yes" if r["company"] and (r["phone"] or r["email"]) else "no"
    return r


# ---- 5. drop what is already in the CRM or suppressed ---------------------------------------------
def key_set(paths):
    keys = set()
    for p in paths or []:
        for row in read_csv(p):
            low = {(k or "").strip().lower(): (v or "") for k, v in row.items()}
            for col in ("email", "email address", "e-mail"):
                e, _ = clean_email(low.get(col, ""))
                if e:
                    keys.add("e:" + e)
            for col in ("phone", "mobile", "phone number", "phone_number"):
                p_, _ = clean_phone(low.get(col, ""))
                if p_:
                    keys.add("p:" + p_)
            _, d = clean_website(low.get("website", "") or low.get("website url", "") or low.get("domain", ""))
            if d:
                keys.add("d:" + d)
    return keys


# ---- 6. export ------------------------------------------------------------------------------------
EXPORTS = {
    "zoho_leads.csv": [("First Name", "first_name"), ("Last Name", "last_name_or_company"), ("Company", "company"),
                       ("Title", "title"), ("Email", "email"), ("Phone", "phone"), ("Website", "website"),
                       ("Street", "street"), ("City", "city"), ("State", "state"), ("Zip Code", "zip"),
                       ("Country", "country"), ("Industry", "industry"), ("Lead Source", "source"),
                       ("Description", "notes")],
    "gohighlevel_contacts.csv": [("First Name", "first_name"), ("Last Name", "last_name"), ("Business Name", "company"),
                                 ("Email", "email"), ("Phone", "phone"), ("Website", "website"), ("Address", "street"),
                                 ("City", "city"), ("State", "state"), ("Postal Code", "zip"), ("Country", "country"),
                                 ("Source", "source"), ("Tags", "tags")],
    "hubspot_contacts.csv": [("First Name", "first_name"), ("Last Name", "last_name"), ("Email", "email"),
                             ("Phone Number", "phone"), ("Company Name", "company"), ("Website URL", "website"),
                             ("Street Address", "street"), ("City", "city"), ("State/Region", "state"),
                             ("Postal Code", "zip"), ("Country/Region", "country"), ("Industry", "industry")],
}


def export(rows, out_dir, tag):
    for name, cols in EXPORTS.items():
        mapped = []
        for r in rows:
            v = dict(r)
            v["last_name_or_company"] = r["last_name"] or r["company"]   # Zoho Leads requires Last Name
            v["tags"] = ",".join(t for t in (tag, r["industry"], r["language"] or r["language_hint"].rstrip("?")) if t)
            mapped.append({h: v.get(f, "") for h, f in cols})
        write_csv(os.path.join(out_dir, name), mapped, [h for h, _ in cols])


def run(inputs, profile_path, out_dir, existing=None, suppression=None, tag="", today=None):
    profile = load_profile(profile_path)
    os.makedirs(out_dir, exist_ok=True)
    recs = []
    for p in inputs:
        recs += ingest(read_csv(p), profile, os.path.splitext(os.path.basename(p))[0])
    n_in = len(recs)
    recs = [clean(r) for r in recs]
    removed = []
    usable = []
    for r in recs:
        if not (r["company"] or r["last_name"]) or not (r["phone"] or r["email"] or r["website"]):
            removed.append(dict(r, removed_reason="no name or no way to reach")); continue
        usable.append(r)
    merged = dedupe(usable, profile.get("fuzzy_name_threshold", 0.92))
    n_dupes = len(usable) - len(merged)
    crm_keys, stop_keys = key_set(existing), key_set(suppression)
    kept = []
    for r in merged:
        ks = set(match_keys(r))
        if ks & stop_keys:
            removed.append(dict(r, removed_reason="on suppression / do-not-contact list")); continue
        if ks & crm_keys:
            removed.append(dict(r, removed_reason="already in CRM")); continue
        kept.append(enrich(r, profile))
    kept.sort(key=lambda r: (-int(r["quality"]), r["company"].lower()))
    write_csv(os.path.join(out_dir, "clean.csv"), kept, FIELDS + EXTRA)
    write_csv(os.path.join(out_dir, "removed.csv"), removed, FIELDS + ["issues", "removed_reason"])
    ready = [r for r in kept if r["ready"] == "yes"]
    export(ready, out_dir, tag or profile.get("tag", ""))
    stats = {"rows_in": n_in, "unusable": sum(1 for r in removed if r["removed_reason"].startswith("no name")),
             "duplicates_merged": n_dupes,
             "already_in_crm": sum(1 for r in removed if r["removed_reason"] == "already in CRM"),
             "suppressed": sum(1 for r in removed if r["removed_reason"].startswith("on suppression")),
             "kept": len(kept), "ready_to_import": len(ready),
             "with_phone": sum(1 for r in ready if r["phone"]), "with_email": sum(1 for r in ready if r["email"]),
             "with_issues": sum(1 for r in kept if r["issues"])}
    with open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8") as f:
        f.write(f"# Pipeline report ({(today or dt.date.today()).isoformat()})\n\nInputs: {', '.join(os.path.basename(p) for p in inputs)}\n\n")
        f.write("| Step | Count |\n|---|---|\n" + "".join(f"| {k.replace('_', ' ')} | {v} |\n" for k, v in stats.items()))
        f.write("\nNext: open `clean.csv`, spot-check 10 rows, then import ONE of the CRM files. "
                "Imported records get no messages until you enroll them in a journey on purpose.\n")
    print(json.dumps(stats, indent=2))
    return stats


def main(argv=None):
    ap = argparse.ArgumentParser(description="Clean, dedupe and enrich business lists into CRM-ready CSVs (local files only)")
    ap.add_argument("cmd", choices=["run", "template"])
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--profile", default=os.path.join(HERE, "profiles", "generic.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--existing", action="append", help="CSV export of records already in your CRM (repeatable)")
    ap.add_argument("--suppression", action="append", help="CSV of do-not-contact emails/phones (repeatable)")
    ap.add_argument("--tag", default="", help="tag added to every imported row, e.g. list-2026-03")
    a = ap.parse_args(argv)
    if a.cmd == "template":
        write_csv(a.inputs[0], [], FIELDS)
        print(f"wrote {a.inputs[0]}: one row per business; fill what you can see on the public page; put the page URL in source_url")
        return
    run(a.inputs, a.profile, a.out, a.existing, a.suppression, a.tag)


if __name__ == "__main__":
    main(sys.argv[1:])
