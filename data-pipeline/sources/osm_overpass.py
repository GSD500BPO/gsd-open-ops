#!/usr/bin/env python3
"""Pull businesses of one type in one area from OpenStreetMap (Overpass API) into a CSV.

Why OpenStreetMap: its data is open (ODbL license) and the public Overpass API allows automated queries
within its usage policy (small, infrequent queries; identify yourself). Respect both:
  - Run it by hand or at most daily, for one area at a time. No loops over hundreds of cities.
  - Keep the attribution: "Data (c) OpenStreetMap contributors, ODbL". The CSV includes it.
  - ODbL is share-alike: if you PUBLISH a database built from this data, read the license first.
    Using it inside your own CRM is the normal case.
Coverage of phones/emails in OSM is uneven. Expect names and addresses, sometimes websites and phones.

By default this prints the query and does NOT touch the network. Add --fetch to run it.

  python3 sources/osm_overpass.py --tag craft=plumber --area "Austin" --out osm-plumbers.csv            # shows the query
  python3 sources/osm_overpass.py --tag craft=plumber --area "Austin" --out osm-plumbers.csv --fetch    # runs it
  python3 sources/osm_overpass.py --tag craft=hvac --bbox 30.1,-97.9,30.5,-97.5 --out hvac.csv --fetch

Useful tags: craft=plumber, craft=hvac, craft=roofer, craft=electrician, craft=photovoltaic, shop=water, office=company.
See https://wiki.openstreetmap.org/wiki/Map_features for more.
Then: python3 pipeline.py run osm-plumbers.csv --profile profiles/openstreetmap.json
"""
import argparse
import csv
import json
import os
import re
import sys
import urllib.parse
import urllib.request

ENDPOINT = os.environ.get("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
UA = os.environ.get("OVERPASS_USER_AGENT", "gsd-open-ops-data-pipeline/1.0 (set OVERPASS_USER_AGENT to your contact email)")
COLS = ["name", "contact:phone", "contact:email", "contact:website", "street", "city", "state", "zip", "category",
        "osm_url", "attribution"]


def build_query(tag, area=None, bbox=None):
    k, _, v = tag.partition("=")
    if not re.fullmatch(r"[a-z_:]+", k) or not re.fullmatch(r"[A-Za-z0-9_ ;-]*", v):
        raise SystemExit("tag must look like key=value, e.g. craft=plumber")
    sel = f'["{k}"="{v}"]' if v else f'["{k}"]'
    if bbox:
        s, w, n, e = [float(x) for x in bbox.split(",")]
        return f"[out:json][timeout:60];nwr{sel}({s},{w},{n},{e});out center tags 500;"
    if not area or '"' in area:
        raise SystemExit("give --area NAME or --bbox south,west,north,east")
    return (f'[out:json][timeout:60];area["name"="{area}"]["boundary"="administrative"]->.a;'
            f"nwr{sel}(area.a);out center tags 500;")


def to_rows(data, tag):
    rows = []
    for el in data.get("elements", []):
        t = el.get("tags", {})
        if not t.get("name"):
            continue
        rows.append({
            "name": t.get("name", ""),
            "contact:phone": t.get("phone") or t.get("contact:phone", ""),
            "contact:email": t.get("email") or t.get("contact:email", ""),
            "contact:website": t.get("website") or t.get("contact:website", ""),
            "street": " ".join(x for x in (t.get("addr:housenumber", ""), t.get("addr:street", "")) if x),
            "city": t.get("addr:city", ""),
            "state": t.get("addr:state", ""),
            "zip": t.get("addr:postcode", ""),
            "category": f"{tag} {t.get('description', '')}".strip(),
            "osm_url": f"https://www.openstreetmap.org/{el.get('type')}/{el.get('id')}",
            "attribution": "Data (c) OpenStreetMap contributors, ODbL",
        })
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description="OpenStreetMap businesses -> CSV (prints the query unless --fetch)")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--area")
    ap.add_argument("--bbox")
    ap.add_argument("--out", required=True)
    ap.add_argument("--fetch", action="store_true", help="really call the Overpass API (one request)")
    a = ap.parse_args(argv)
    q = build_query(a.tag, a.area, a.bbox)
    if not a.fetch:
        print("Query (not sent; add --fetch to run it):\n" + q)
        return
    req = urllib.request.Request(ENDPOINT, data=urllib.parse.urlencode({"data": q}).encode(), method="POST",
                                 headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        data = json.load(r)
    rows = to_rows(data, a.tag)
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} businesses to {a.out}. Data (c) OpenStreetMap contributors, ODbL.", file=sys.stderr)


if __name__ == "__main__":
    main()
