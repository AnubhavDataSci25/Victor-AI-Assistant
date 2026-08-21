from app.auth.factory import build_auth_manager
from app.auth.hashing import hash_phrase
from app.brain.orchestrator import VictorCore
from app.config import load_config
from app.tools.browser.fake_driver import FakeBrowserDriver
from app.tools.computer.fake_driver import FakeComputerDriver
from app.tools.factory import build_registry

PHRASE = "open sesame"


def _core(tmp_path, monkeypatch, provisioned: bool = True):
    monkeypatch.setenv("HOME", str(tmp_path))
    config = load_config("config/default.yaml")
    config.filesystem.allowed_roots = [str(tmp_path)]
    config.security.secrets_path = str(tmp_path / "secrets.yaml")
    config.computer.applications = {"notepad": "notepad.exe"}
    driver = FakeComputerDriver()
    browser_driver = FakeBrowserDriver()
    registry = build_registry(config, computer_driver=driver, browser_driver=browser_driver)
    auth = build_auth_manager(config)
    if provisioned:
        auth._store.set_phrase_hash(hash_phrase(PHRASE))
    return VictorCore(config, registry, auth), auth, driver, browser_driver


def test_tool_call_denied_while_locked(tmp_path, monkeypatch):
    (tmp_path / "notes.txt").write_text("hi")
    core, _, _driver, _browser = _core(tmp_path, monkeypatch)

    reply = core.handle_input(f"list files in {tmp_path}")

    assert "authenticate" in reply.lower()


def test_casual_conversation_allowed_while_locked(tmp_path, monkeypatch):
    core, _, _driver, _browser = _core(tmp_path, monkeypatch)
    reply = core.handle_input("who are you?")
    assert "Victor" in reply


def test_full_wake_authenticate_then_tool_flow(tmp_path, monkeypatch):
    (tmp_path / "notes.txt").write_text("hi")
    core, _, _driver, _browser = _core(tmp_path, monkeypatch)

    wake_reply = core.handle_input("Victor")
    assert "verification required" in wake_reply.lower()

    auth_reply = core.handle_input(PHRASE)
    assert "verified" in auth_reply.lower()

    tool_reply = core.handle_input(f"list files in {tmp_path}")
    assert "notes.txt" in tool_reply


def test_wrong_phrase_keeps_tools_locked(tmp_path, monkeypatch):
    """
    After a wrong phrase, Victor stays in the authentication challenge
    (spec section 10: consecutive attempts), so the next input is
    still treated as a phrase attempt - not as a command. Either way,
    the tool must never execute.
    """
    (tmp_path / "notes.txt").write_text("hi")
    core, _, _driver, _browser = _core(tmp_path, monkeypatch)

    core.handle_input("Victor")
    auth_reply = core.handle_input("wrong phrase")
    assert "failed" in auth_reply.lower()

    # Still inside the challenge - this is consumed as another phrase
    # attempt, not routed to the filesystem tool.
    second_reply = core.handle_input(f"list files in {tmp_path}")
    assert "notes.txt" not in second_reply


def test_manual_lock_relocks_active_session(tmp_path, monkeypatch):
    (tmp_path / "notes.txt").write_text("hi")
    core, _, _driver, _browser = _core(tmp_path, monkeypatch)

    core.handle_input("Victor")
    core.handle_input(PHRASE)
    lock_reply = core.handle_input("Victor, lock yourself")
    assert "locked" in lock_reply.lower()

    tool_reply = core.handle_input(f"list files in {tmp_path}")
    assert "authenticate" in tool_reply.lower()


def test_open_application_after_authentication(tmp_path, monkeypatch):
    core, _, driver, _browser = _core(tmp_path, monkeypatch)

    core.handle_input("Victor")
    core.handle_input(PHRASE)
    reply = core.handle_input("open notepad")

    assert "opened" in reply.lower()
    assert driver.is_process_running("notepad.exe")


def test_open_application_denied_while_locked(tmp_path, monkeypatch):
    core, _, driver, _browser = _core(tmp_path, monkeypatch)

    reply = core.handle_input("open notepad")

    assert "authenticate" in reply.lower()
    assert not driver.is_process_running("notepad.exe")


def test_close_application_requires_confirmation_not_yet_available(tmp_path, monkeypatch):
    """close_application is MEDIUM risk (spec section 20: destructive
    actions require confirmation). Since no confirmation UI exists yet,
    it must be denied even for an authenticated session."""
    core, _, driver, _browser = _core(tmp_path, monkeypatch)
    driver.running_processes.add("notepad.exe")

    core.handle_input("Victor")
    core.handle_input(PHRASE)
    reply = core.handle_input("close notepad")

    assert driver.is_process_running("notepad.exe")
    assert "confirmation" in reply.lower() or "requires" in reply.lower()


def test_create_and_read_file_after_authentication(tmp_path, monkeypatch):
    core, _, _driver, _browser = _core(tmp_path, monkeypatch)

    core.handle_input("Victor")
    core.handle_input(PHRASE)
    create_reply = core.handle_input(f"create_file {tmp_path / 'diary.txt'} hello there")
    read_reply = core.handle_input(f"read {tmp_path / 'diary.txt'}")

    assert "Sir" in create_reply
    assert "hello there" in read_reply


def test_delete_file_denied_without_confirmation(tmp_path, monkeypatch):
    """delete_file is HIGH risk (spec section 12) and must stay denied
    until a real confirmation flow exists, even for an authenticated
    session."""
    core, _, _driver, _browser = _core(tmp_path, monkeypatch)
    target = tmp_path / "important.txt"
    target.write_text("do not delete")

    core.handle_input("Victor")
    core.handle_input(PHRASE)
    reply = core.handle_input(f"delete file {target}")

    assert target.exists()
    assert "confirmation" in reply.lower() or "requires" in reply.lower()


def test_file_operations_denied_while_locked(tmp_path, monkeypatch):
    core, _, _driver, _browser = _core(tmp_path, monkeypatch)
    target = tmp_path / "secret.txt"
    target.write_text("classified")

    reply = core.handle_input(f"read {target}")

    assert "authenticate" in reply.lower()


def test_run_command_low_risk_executes_after_authentication(tmp_path, monkeypatch):
    core, _, _driver, _browser = _core(tmp_path, monkeypatch)

    core.handle_input("Victor")
    core.handle_input(PHRASE)
    reply = core.handle_input("run echo hello")

    assert "hello" in reply.lower()


def test_run_command_denied_while_locked(tmp_path, monkeypatch):
    core, _, _driver, _browser = _core(tmp_path, monkeypatch)
    reply = core.handle_input("run echo hello")
    assert "authenticate" in reply.lower()


def test_run_command_medium_risk_denied_without_confirmation(tmp_path, monkeypatch):
    core, _, _driver, _browser = _core(tmp_path, monkeypatch)

    core.handle_input("Victor")
    core.handle_input(PHRASE)
    reply = core.handle_input("run pip install requests")

    assert "confirmation" in reply.lower() or "requires" in reply.lower()


def test_run_command_blocked_command_always_denied(tmp_path, monkeypatch):
    """A BLOCKED command must be denied even for an authenticated
    session - there is no confirmation path that unlocks it."""
    core, _, _driver, _browser = _core(tmp_path, monkeypatch)

    core.handle_input("Victor")
    core.handle_input(PHRASE)
    reply = core.handle_input("run del important.txt")

    assert "blocked" in reply.lower() or "cannot be executed" in reply.lower()


def test_run_python_after_authentication(tmp_path, monkeypatch):
    core, _, _driver, _browser = _core(tmp_path, monkeypatch)

    core.handle_input("Victor")
    core.handle_input(PHRASE)
    reply = core.handle_input("run_python print(6 * 7)")

    assert "42" in reply


def test_open_url_and_read_page_after_authentication(tmp_path, monkeypatch):
    core, _, _driver, browser = _core(tmp_path, monkeypatch)
    browser.page_registry["https://example.com"] = {
        "title": "Example",
        "text": "Hello from the example page.",
    }

    core.handle_input("Victor")
    core.handle_input(PHRASE)
    core.handle_input("go to https://example.com")
    reply = core.handle_input("read the page")

    assert "Hello from the example page" in reply


def test_browser_tools_denied_while_locked(tmp_path, monkeypatch):
    core, _, _driver, _browser = _core(tmp_path, monkeypatch)
    reply = core.handle_input("go to https://example.com")
    assert "authenticate" in reply.lower()


def test_close_tab_denied_without_confirmation(tmp_path, monkeypatch):
    """close_tab is MEDIUM (spec section 20 reasoning applied to
    browser tabs) and must stay denied until confirmation exists."""
    core, _, _driver, browser = _core(tmp_path, monkeypatch)
    tab_id = browser.open_tab(None)

    core.handle_input("Victor")
    core.handle_input(PHRASE)
    reply = core.handle_input(f"close tab {tab_id}")

    assert "confirmation" in reply.lower() or "requires" in reply.lower()
    assert tab_id in browser._tabs