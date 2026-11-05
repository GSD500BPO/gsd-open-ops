# Contributing

Thanks for helping. Issues and pull requests are welcome.

- **New roleplay scenario?** Add `recruiting/ramon/scenarios/<id>.json` (same shape as `water_treatment.json`) and a line in the recruiting README.
- **Translation or new module?** Add `<slug>.md` + `<slug>.es.md` in `training/curriculum/`, an entry in `modules.json`, and 3-4 quiz questions.
- **Code:** keep the pipeline on the Python standard library (heavy ML only inside `speech_score.py` / `rp_transcribe.py`). Run the tests before you open a PR: `python3 recruiting/ramon/tests/test_offline.py`, `python3 -m unittest discover -s journeys/24-step/tests`, `python3 -m unittest discover -s alerts/tests`, `python3 -m unittest discover -s data-pipeline/tests`.
- **New data source?** Only sources whose terms allow automated collection go in `data-pipeline/sources/`. Everything else goes through the manual research path in `data-pipeline/SOURCES.md`. Scrapers for sites that forbid them won't be merged.
- **Safety rails are not optional:** dry by default, per-recipient caps, state saved before sending, STOP is permanent, consent before anything public. PRs that weaken them won't be merged.

## Never commit
Real candidate or customer data, phone numbers, emails, recordings, `.env` files, tokens or keys. Use `example.com`, `+1 555 ...` and `{{PLACEHOLDERS}}`. We run `gitleaks` on every PR.
