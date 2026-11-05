# Ramón: the bot's code

The pipeline, webhook, scorer and roleplay. Full overview, flow diagram, configuration and safety rails: **[`../README.md`](../README.md)**.

```bash
cp .env.example .env && chmod 600 .env
python3 tests/test_offline.py        # dry, no network: "OK 10 checks"
```

| Start with | Why |
|---|---|
| `.env.example` | Every setting, commented. Nothing is hard-coded |
| `talent.py` | The pipeline and CLI (`run`, `score`, `rescore`, `digest`, `rpscore`, `rpstart`, `status`) |
| `speech_score.py` | Run it on any video to see the speaking score JSON |
| `scenarios/` | Copy one to make a roleplay for your trade |
| `deploy/` | systemd units + crontab example |

Adapting: change `.env` first; only touch code to swap the ATS (`recruit_*` functions in `talent.py`) or the storage backend.
