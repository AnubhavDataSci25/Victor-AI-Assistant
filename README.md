# Victor

A local-first, tool-calling personal AI computer assistant.

> Understand. Decide. Act. Verify.

## Status

**Phase 5 — File Management.** Victor now has the full filesystem
tool set from spec section 21: search, find, read, create, write,
append, rename, copy, move, delete (file and directory). All are path-
validated against the allowed-roots sandbox; risky operations
(write_file, rename_file, move_file, delete_file, delete_directory)
are correctly denied pending Phase 12's confirmation flow, same
pattern established for close_application in Phase 4. No terminal,
browser, voice, or UI yet.


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
    ├── factory.py                 # builds the registry from config (+ driver selection)
    ├── filesystem/
    │   ├── path_validation.py     # allowed-roots + traversal protection
    │   ├── tool.py                 # list_directory (SAFE)
    │   ├── read_tools.py           # search_files, find_file, read_file (SAFE)
    │   ├── write_tools.py          # create_file, create_directory (SAFE),
    │   │                            # append_file (LOW), write_file (MEDIUM)
    │   ├── modify_tools.py         # copy_file (LOW), rename/move_file (MEDIUM)
    │   └── delete_tools.py         # delete_file, delete_directory (HIGH)
    └── computer/
        ├── driver.py               # ComputerDriver protocol + DriverError
        ├── fake_driver.py          # in-memory driver used by all tool tests
        ├── windows_driver.py       # real driver: subprocess + psutil + pyautogui
        └── tool.py                 # 8 tools: open/close app, focus/switch window,
                                     # type_text, press_key, hotkey, take_screenshot

tests/
├── unit/          # 152 tests
├── integration/   # 11 tests, full text-in -> reply-out chain including auth, computer control, files
└── security/      # 2 tests, phrase never touches disk in logs or plaintext
```

## Permission judgment calls for Phase 5

Spec section 12's table only lists a few filesystem operations
explicitly. For the rest, I classified by data-loss risk:

| Tool | Level | Why |
|---|---|---|
| list_directory, search_files, find_file, read_file | SAFE | read-only |
| create_file, create_directory | SAFE | refuses to overwrite; can only add |
| append_file, copy_file | LOW | additive only, never destroys existing bytes |
| write_file, rename_file, move_file | MEDIUM | can overwrite/relocate; destination collisions are refused, but the underlying operation still risks data loss |
| delete_file, delete_directory | HIGH | matches spec section 12 explicitly |

`delete_directory` also requires an explicit `recursive=True` for a
non-empty directory even after HIGH gets a confirmation flow in a
later phase - a confirmed "delete this" shouldn't accidentally mean
"delete everything inside it" too.

Every MEDIUM/HIGH tool above is registered and reachable through the
router, but currently always denied by the permission engine, since
there's no confirmation UI yet (proven in
`test_delete_file_denied_without_confirmation` and similar tests) -
this is intentional, not a gap.

## Testing note: computer control tools

This sandbox has no Windows and no display, so `WindowsComputerDriver`
(the real PyAutoGUI/psutil backend) cannot be run here. To keep the
tool *logic* - argument validation, the application whitelist,
permission classification, structured results, and verification -
fully tested anyway, every computer-control tool depends on a
`ComputerDriver` interface rather than calling the OS directly:

```text
Tool (open_application, focus_window, ...)
    -> ComputerDriver protocol
        -> FakeComputerDriver   (used by all 116 automated tests)
        -> WindowsComputerDriver (real OS calls, used in production)
```

`app/tools/factory.py` auto-selects `WindowsComputerDriver` when
`platform.system() == "Windows"`, and simply skips registering
computer tools otherwise (so Victor still boots fine in dev on
Linux/Mac - it just won't offer computer-control tools there).

**Before relying on this in production, verify on a real Windows
machine:**

```bash
pip install psutil pyautogui
python scripts/setup_auth.py
python -m app.cli
```

Add at least one entry to `computer.applications` in your config
first (e.g. `notepad: notepad.exe`), then try `open notepad`,
`take a screenshot`, `press enter`. `close_application` will refuse
by design (see below) until Phase 12's confirmation flow exists.

## Security note: the application whitelist

`open_application` and `close_application` only accept friendly names
that are explicitly mapped to a launch command in
`config.computer.applications`. An unlisted name is refused outright
- Victor will never invent or guess an executable path from a
request, which matters once real LLM tool-selection (Phase 9)
replaces the current stub router. This also means `close_application`
is classified **MEDIUM**, not SAFE (spec section 12 doesn't list it
explicitly; closing an app can lose unsaved work), so it is currently
denied for every request - by design, not a bug - until a real
confirmation flow exists.

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
3. ~~Authentication (Argon2id, lockout, session timeout)~~
4. ~~Computer control~~
5. ~~File management~~ ← you are here
6. Terminal
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