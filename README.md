# Victor

A local-first, tool-calling personal AI computer assistant.

> Understand. Decide. Act. Verify.

## Status

**Phase 2 — Victor Core.** Tool registry, permission engine, and the
first tool are live and wired end to end via a temporary rule-based
router (stands in for the LLM until Phase 9). No authentication,
computer control, terminal, browser, voice, or UI yet.


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
python -m app.main   # boot check only
python -m app.cli    # interactive text mode
```

Try in the CLI: `list files in ~`, `who are you?`, `how are you?`

## Test

```bash
pytest tests/ -v
```

## Project layout

Currently implemented:

```text
app/
├── main.py                        # boot: config + logging
├── cli.py                         # interactive text REPL
├── config.py                      # typed, validated YAML configuration
├── logging.py                     # structured JSON logging + redaction
│
├── brain/
│   ├── router.py                  # TEMPORARY rule-based stand-in for the LLM
│   ├── responder.py                # ToolResult -> natural language
│   └── orchestrator.py            # VictorCore: wires router + registry + responder
│
└── tools/
    ├── models.py                  # ToolCallRequest, ToolResult
    ├── permissions.py             # PermissionLevel, PermissionEngine (Layer 2 security)
    ├── base.py                    # Tool abstract base class
    ├── registry.py                # ToolRegistry: validate -> permission -> execute -> verify -> log
    ├── factory.py                 # builds the registry from config
    └── filesystem/
        ├── path_validation.py     # allowed-roots + traversal protection
        └── tool.py                # list_directory (first SAFE tool)

tests/
├── unit/          # 45 tests
└── integration/   # 3 tests, full text-in -> reply-out chain
```

## Important note on `app/brain/router.py`

This is explicitly a temporary stub, not the real LLM integration.
It exists so the whole safety chain (tool call → validation →
permission → execution → verification → structured result →
response) could be proven without depending on a running Ollama
instance. Its output is still just a `ToolCallRequest` — it goes
through the exact same registry/permission gate as any future LLM
output would. When Ollama integration lands (Phase 9), only this
module's internals change.


## Security note

`.env`, `config/local.yaml`, `config/secrets.yaml`, and everything
under `logs/` are git-ignored. Victor never stores secrets in
plaintext — see the authentication design in Phase 3.

## Roadmap

1. ~~Project skeleton~~
2. ~~Tool registry + one safe tool end-to-end~~ ← you are here
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