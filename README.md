# Victor

A local-first, tool-calling personal AI computer assistant.

> Understand. Decide. Act. Verify.

## Status

**Phase 3 — Authentication.** Tools now require the wake word →
security phrase challenge before executing. Argon2id hashing, failed
attempt lockout, session timeout, and manual lock are all live and
tested. Casual conversation still works while locked; tool calls do
not. No computer control, terminal, browser, voice, or UI yet.


## Requirements

- Python 3.10+

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python scripts/setup_auth.py     # provision your security phrase (Argon2id hash only)
```

## Run

```bash
python -m app.main   # boot check only
python -m app.cli    # interactive text mode
```

Try in the CLI:

```text
list files in ~              # blocked - not authenticated yet
Victor                        # triggers the security phrase challenge
<your phrase>                  # unlocks
list files in ~              # now works
Victor, lock yourself         # manual lock
```

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
│   └── orchestrator.py            # VictorCore: wake word, auth gate, router, registry
│
├── auth/
│   ├── hashing.py                 # Argon2id hash_phrase / verify_phrase
│   ├── store.py                   # SecretStore: hash-only persistence, 0600 perms
│   ├── session.py                 # inactivity timeout tracking
│   ├── manager.py                 # AuthManager: LOCKED/UNLOCKED state machine
│   └── factory.py                 # builds AuthManager from config
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
├── unit/          # 66 tests
├── integration/   # 5 tests, full text-in -> reply-out chain including auth
└── security/      # 2 tests, phrase never touches disk in logs or plaintext
```

## Security notes for Phase 3

- `scripts/setup_auth.py` is the *only* place a plaintext phrase is
  ever typed. It's read via `getpass` (no echo), hashed immediately,
  and the local variable is deleted after use.
- `AuthManager.authenticate()` never logs the candidate phrase, only
  generic event names (`auth_success`, `auth_failure`, ...). This was
  verified with a real logging pipeline in
  `tests/security/test_secrets_not_logged.py`, not just by code
  review - the redaction filter in `app/logging.py` catches *named*
  sensitive fields, but not text embedded in a message string, so the
  auth code itself has to uphold this discipline.
- `config/secrets.yaml` stores only an Argon2id hash, is git-ignored,
  and is written with owner-only file permissions (POSIX).
- Tool calls are gated in `VictorCore.handle_input`, in front of the
  registry - the registry itself has no concept of authentication, by
  design, so it can't be bypassed by calling it directly instead of
  through VictorCore. (A future hardening item, noted for Phase 12, is
  making the registry refuse to be constructed/dispatched outside an
  authenticated context at all, rather than relying on the caller to
  check first.)


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
2. ~~Tool registry + one safe tool end-to-end~~
3. ~~Authentication (Argon2id, lockout, session timeout)~~ ← you are here
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