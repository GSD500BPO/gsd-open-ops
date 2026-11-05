# Where list data can come from

Rule one: **only collect data in ways the source allows.** If a site's terms forbid automated collection, we don't automate it. We research by hand, or we don't use that site. This repo ships no scraper for any site whose terms forbid one.

This is not legal advice. Terms change. Read the current terms of any source before you use it, and check the laws where you and your contacts are (anti-spam, telemarketing and privacy laws).

## Sources we use, and how

| Source | Automated? | How to bring it in | Notes |
|---|---|---|---|
| **Your own data**: CRM exports, past customers, event sign-ups, web forms, inbound calls | Yes, it's yours | Export CSV, run `pipeline.py` | The best list you will ever have. Respect each person's opt-outs |
| **Government open data**: state contractor license lists, business registrations, permit data, published as downloads | Usually yes, when offered as a download or open-data API | Download the CSV, run `pipeline.py` with the generic profile | Check each dataset's license or terms page. Many allow reuse; some forbid use for solicitation. Respect that |
| **OpenStreetMap** via the public Overpass API | Yes, within the Overpass usage policy | [`sources/osm_overpass.py`](sources/osm_overpass.py) (prints the query; `--fetch` runs one request) | Open data (ODbL): keep the attribution. Small, infrequent queries. Coverage of phones/emails is uneven |
| **Official APIs with a key** (maps/places APIs, business data providers) | Only as their terms allow | Not included | Many of these APIs restrict how long you may store results or forbid exporting to a CRM. Read them first |
| **Purchased or rented lists** | n/a | CSV, `pipeline.py` | Ask the vendor how consent was collected. Keep their answer on file |
| **Trade association or chamber directories** | Only with permission | Ask the association; many sell or share member lists | Never automate a members-only directory |
| **A business's own website** (its contact page) | We research these **by hand** | Manual research CSV (below) | Look at the page, type what you see. No automated email harvesting |

## Sources that are manual-only (no scraper in this repo)

| Source | Why manual | What to do instead |
|---|---|---|
| **Social media ad libraries** (for example the Meta Ad Library) | The platform's terms do not allow automated collection outside its official API, and the API has its own access rules and limits | A person searches, opens each advertiser's public business page, and types the business details into the manual research CSV. Include the page URL in `source_url` |
| **Classifieds and job boards** (for example Craigslist) | Their terms forbid scraping and automated access | A person reads the listing and types the business details into the CSV. Do not copy personal details of private individuals |
| **Review and directory sites** (Yelp, BBB, Angi, and similar) | Most forbid scraping in their terms | Manual research, or the site's official API if its terms allow your use |
| **Search engine results** | Search engines' terms generally forbid automated queries outside their paid APIs | Manual research |
| **LinkedIn and other professional networks** | Terms forbid scraping | Manual research or the platform's own tools |

## The manual research path

1. Make a blank sheet with the right columns:
   ```bash
   python3 pipeline.py template research.csv
   ```
2. Open it in Excel or Google Sheets. One row per **business**.
3. For each business, fill only what you can see on a public business page: company, phone, email, website, city, state, industry, language. Put the exact page you used in `source_url`, today's date in `collected_on`, and your initials in `notes`.
4. Do **not** collect: personal social profiles, home addresses of individuals, or anything behind a login.
5. `sms_consent` stays `no`. Finding a number on a website is not consent to text it.
6. Save as CSV and run:
   ```bash
   python3 pipeline.py run research.csv --existing crm-export.csv --suppression stop-list.csv
   ```
7. Check `out/report.md`, spot-check `out/clean.csv`, then import.

A trained researcher does 20-40 businesses an hour this way, and the data is usually better than scraped data: a person can tell a real installer from a directory page.

## Business vs. personal data

- Collect **business** contact details (company phone, company email, role addresses like `info@`).
- If you collect a named person's business email, treat it as personal data under privacy laws that apply to you (for example GDPR in the EU, or US state privacy laws).
- Keep `source` and `source_url` for every record. If someone asks "where did you get my details?", you can answer.
- Lead source is for your reporting only. Never put it in a message to a customer or client.
