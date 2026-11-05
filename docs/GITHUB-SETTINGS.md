# GitHub settings for discovery

Applied with `gh repo edit` on 2026-11-04 (description + topics + homepage). The social preview image must be uploaded by hand (GitHub has no API for it).

## Description (≤ 350 characters)

> Open-source appointment-setting & BPO operations kit: WhatsApp recruiting bot with automated candidate scoring, 23-module setter academy (EN/ES), sales cadence templates, CRM ownership rules and a 96-step year-round CRM journey for water-treatment and home-service businesses. Built with Claude. MIT.

## Homepage

`https://gsd500bpo.com/?utm_source=github&utm_medium=repo_homepage&utm_campaign=open-ops`

## Topics (20, GitHub max)

`appointment-setting` · `bpo` · `call-center` · `sales-operations` · `sales-cadence` · `lead-nurturing` · `crm` · `zoho-crm` · `gohighlevel` · `hubspot` · `recruiting` · `whatsapp-bot` · `whatsapp-cloud-api` · `speech-scoring` · `whisper` · `sales-training` · `sdr` · `home-services` · `water-treatment` · `claude`

## Social preview

- File: [`assets/social-preview.png`](assets/social-preview.png), 1280 × 640 PNG, < 1 MB.
- Brand: black background, #21E957 green, Poppins ExtraBold headline, Space Mono labels, GSD 500 BPO badge top left, safe margins 80 px (GitHub crops edges on some cards).
- Copy: "The BPO operating system, open-sourced." + "Recruiting bot with automated scoring · 23-module setter academy · sales cadences · 96-step year-round CRM journey" + tag "FREE · MIT · EN/ES".
- Upload: repo → **Settings → General → Social preview → Edit → Upload an image**.

## Other settings (when public)

- Features: Issues on, Discussions on (Q&A + "Show your setup"), Wiki off (docs live in the repo).
- Pin the repo on the GSD500BPO organization profile.
- Release `v1.0.0` with the 96-step PDF attached (releases get indexed and show in the sidebar).
- Pages (optional): `mkdocs.yml` is ready; see [`index.md`](index.md). Build with `pip install mkdocs-material && mkdocs gh-deploy` only after the repo is public.
- Link the repo from gsd500bpo.com (footer + the launch blog post) and from the YouTube descriptions of the 96-step and cadence videos: inbound links are what get the repo indexed by Google.

## Launch checklist (maintainers)

1. Re-read the README and the build story ([`how-we-built-it.md`](how-we-built-it.md)), especially Chapter 8.
2. Upload the social preview.
3. Flip visibility to public (Settings → Danger zone).
4. Replace `{{REPO_URL}}` in the blog drafts with `https://github.com/GSD500BPO/gsd-open-ops` and publish the launch post.
