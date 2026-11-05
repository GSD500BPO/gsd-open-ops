# Security

Please report vulnerabilities privately to **security@gsd500bpo.com** (or a private GitHub security advisory on this repo). Don't open a public issue. We'll answer within 3 business days.

This repo contains no credentials. If you find something that looks like a secret or personal data, report it the same way and we'll rotate and purge it.

Deploying Ramón: keep `.env` at chmod 600, run the services on localhost behind TLS, set `WA_APP_SECRET` (the webhook refuses unsigned requests), set a unique `TALENT_REEL_SALT`, and keep video storage private.
