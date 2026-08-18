# Victor

A local-first, tool-calling personal AI computer assistant.

> Understand. Decide. Act. Verify.

## Status

**Phase 1 — Project Skeleton.** No tools, authentication, voice, or UI
are implemented yet. This phase only proves the application boots
reliably with validated configuration and structured logging.

## Requirements

- Python 3.10+

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

## Run

```bash
python -m app.main
```

## Test

```bash
pytest tests/ -v
```

## Project layout

See `docs/architecture.md` (added as later phases land) and the
master specification for the full target architecture. Currently
implemented:

```text
app/
├── main.py       # entrypoint: loads config, sets up logging, boots
├── config.py     # typed, validated YAML configuration loading
└── logging.py    # structured JSON logging with mandatory secret redaction

config/
└── default.yaml  # default configuration

tests/unit/
├── test_config.py
└── test_logging.py
```

## Security note

`.env`, `config/local.yaml`, `config/secrets.yaml`, and everything
under `logs/` are git-ignored. Victor never stores secrets in
plaintext — see the authentication design in Phase 3.

## Roadmap

1. ~~Project skeleton~~ ← you are here
2. Tool registry + one safe tool end-to-end
3. Authentication (Argon2id, lockout, session timeout)
4. Computer control
5. File management
6. Terminal execution
7. Browser automation
8. Voice pipeline
9. Conversation / intent routing
10. Orb UI
11. Verification layer
12. Security hardening
13. Full test suite
14. Multi-step tasks
