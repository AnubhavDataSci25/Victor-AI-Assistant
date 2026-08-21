# Victor

A local-first, tool-calling personal AI computer assistant.

> Understand. Decide. Act. Verify.

## Status

**Phase 7 — Browser.** Twelve browser tools from spec section 24 are
implemented against a driver interface, mirroring Phase 4's split:
tool logic is fully unit-tested with `FakeBrowserDriver`; the real
`PlaywrightBrowserDriver` is written correctly but can't run in this
sandbox (no network access to download browser binaries) - see
"Testing note" below. No voice or UI yet.


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
    ├── terminal/
    │   ├── validator.py            # classify_command: deterministic risk classifier
    │   ├── process_manager.py      # tracks Victor-started background processes
    │   └── tool.py                  # run_command, run_python, start/stop_process
    ├── browser/
    │   ├── driver.py                # BrowserDriver protocol + BrowserDriverError
    │   ├── fake_driver.py           # in-memory driver used by all browser tool tests
    │   ├── playwright_driver.py     # real driver: Playwright (chromium)
    │   └── tool.py                  # 12 tools: open_url, search_web, read_page,
    │                                 # extract_text, click_element, type_into_page,
    │                                 # scroll_page, go_back/forward, open/close_tab,
    │                                 # screenshot_page
    └── computer/
        ├── driver.py               # ComputerDriver protocol + DriverError
        ├── fake_driver.py          # in-memory driver used by all tool tests
        ├── windows_driver.py       # real driver: subprocess + psutil + pyautogui
        └── tool.py                 # 8 tools: open/close app, focus/switch window,
                                     # type_text, press_key, hotkey, take_screenshot

tests/
├── unit/          # 215 tests
├── integration/   # 19 tests, full text-in -> reply-out chain including auth, computer control, files, terminal, browser
└── security/      # 2 tests, phrase never touches disk in logs or plaintext
```

## Architecture note: dynamic permission classification (Phase 6)

Every prior tool had one fixed permission level. `run_command` breaks
that assumption - `python --version` and `pip install x` go through
the identical tool but carry very different risk. Rather than special-
case the registry for terminal tools, `Tool` gained one new method:

```python
def classify(self, args: BaseModel) -> PermissionLevel:
    return self.permission_level  # default: unchanged behavior
```

`ToolRegistry.dispatch()` now calls `tool.classify(args)` instead of
reading `tool.permission_level` directly. Every tool from Phases 2-5
gets the default implementation and behaves exactly as before -
verified by `test_registry_dynamic_permission.py`. Only
`run_command`/`start_process` override it, delegating to
`classify_command()` - the deterministic pattern-matching validator in
`app/tools/terminal/validator.py`. The classification logic is still
pure application code with no LLM involvement, per rule 20.

## Security notes for Phase 6

- **`classify_command()` is deliberately conservative.** Where spec
  section 23 names a narrow example (`rmdir /s`), the pattern here is
  broader (any `rmdir`) - a false positive costs a retry; a false
  negative risks real data. Same reasoning extended it to cover
  patterns not in the spec at all: pipe-to-shell (`curl ... | bash`,
  `iwr ... | iex`) is blocked outright as unbounded remote code
  execution, and a classic shell fork bomb pattern is blocked too.
- **`stop_process` can only stop what Victor itself started.**
  `ProcessManager` tracks PIDs from `start_process` calls; an
  untracked PID is refused with a clear message, not silently
  ignored or (worse) attempted against an arbitrary system process.
- **`run_python` never touches the shell at all** - code is passed as
  a single `argv` element to the interpreter, not shell-parsed, even
  though it's still classified the same LOW level as `run_command`'s
  safest tier.
- **`run_command`/`start_process` do use `shell=True`.** Deliberate,
  documented choice: many everyday commands (`dir`, `cd`) are shell
  builtins with no standalone executable, so `shell=False` would break
  basic usage. Safety comes from classification happening *before*
  the subprocess call, not from avoiding the shell.

**Flagged for expanded testing later** (per your request): more shell-
quoting edge cases, concurrent `start_process` calls, and real
Windows-specific `shell=True` behavior (this sandbox only proves
POSIX shell behavior via `/bin/sh`).

## Testing note: browser tools

Same situation as Phase 4's computer-control tools: this sandbox has
no network access to download Playwright's browser binaries
(`playwright install chromium`), so `PlaywrightBrowserDriver` cannot
run here. All 236 tests exercise browser tool logic through
`FakeBrowserDriver` instead - argument validation, permission levels,
verification hooks, error handling. `app/tools/factory.py`
auto-detects whether Playwright is importable and simply skips
registering browser tools if not, so Victor still boots fine without
it.

**Before relying on this in production:**

```bash
pip install playwright
playwright install chromium
python -m app.cli
```

Try `go to https://example.com`, `read the page`, `search the web for
<something>`, `click_element h1`. `close_tab` will refuse by design
(see below) until Phase 12's confirmation flow exists.

## Security note: browser content is data, not instructions (spec section 25)

`read_page`, `extract_text`, and `search_web` return whatever text is
on a page - which could contain something that reads like an
instruction ("ignore previous instructions and..."). Victor's
architecture makes this structurally inert, not just policy: a
`ToolResult` only ever flows to the responder for humanization -
there is no code path that takes a tool's output and re-feeds it into
the router as a new command. That will remain true once the real LLM
replaces the router stub in Phase 9; the constraint is architectural
(no feedback loop exists), not something that has to be remembered
and re-enforced by prompting.

## Permission judgment calls for Phase 7

Consistent with the risk philosophy from Phases 4-6:

| Tool | Level | Why |
|---|---|---|
| open_url, search_web, read_page, extract_text, scroll_page, go_back, go_forward, open_tab, screenshot_page | SAFE | read-only or purely additive |
| click_element, type_into_page | LOW | real but bounded effect on the page, same tier as computer control's type_text/press_key |
| close_tab | MEDIUM | can lose an unsubmitted form or unsaved page state - same reasoning as close_application in Phase 4; denied by default until confirmation exists |

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
5. ~~File management~~
6. ~~Terminal~~
7. ~~Browser~~ ← we are here
8. Voice
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