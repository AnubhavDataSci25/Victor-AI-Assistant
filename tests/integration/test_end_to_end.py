from app.auth.factory import build_auth_manager
from app.auth.hashing import hash_phrase
from app.brain.orchestrator import VictorCore
from app.config import load_config
from app.tools.computer.fake_driver import FakeComputerDriver
from app.tools.factory import build_registry

PHRASE = "open sesame"


def _core(tmp_path, monkeypatch, provisioned: bool = True):
    monkeypatch.setenv("HOME", str(tmp_path))
    config = load_config("config/default.yaml")
    config.filesystem.allowed_roots = [str(tmp_path)]
    config.security.secrets_path = str(tmp_path / "secrets.yaml")
    config.computer.applications = {"notepad": "notepad.exe"}
    config.computer.screenshot_directory = str(tmp_path / "screenshots")
    driver = FakeComputerDriver()
    registry = build_registry(config, computer_driver=driver)
    auth = build_auth_manager(config)
    if provisioned:
        auth._store.set_phrase_hash(hash_phrase(PHRASE))
    return VictorCore(config, registry, auth), auth, driver


def test_tool_call_denied_while_locked(tmp_path, monkeypatch):
    (tmp_path / "notes.txt").write_text("hi")
    core, _, _driver = _core(tmp_path, monkeypatch)

    reply = core.handle_input(f"list files in {tmp_path}")

    assert "authenticate" in reply.lower()


def test_casual_conversation_allowed_while_locked(tmp_path, monkeypatch):
    core, _, _driver = _core(tmp_path, monkeypatch)
    reply = core.handle_input("who are you?")
    assert "Victor" in reply


def test_full_wake_authenticate_then_tool_flow(tmp_path, monkeypatch):
    (tmp_path / "notes.txt").write_text("hi")
    core, _, _driver = _core(tmp_path, monkeypatch)

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
    core, _, _driver = _core(tmp_path, monkeypatch)

    core.handle_input("Victor")
    auth_reply = core.handle_input("wrong phrase")
    assert "failed" in auth_reply.lower()

    # Still inside the challenge - this is consumed as another phrase
    # attempt, not routed to the filesystem tool.
    second_reply = core.handle_input(f"list files in {tmp_path}")
    assert "notes.txt" not in second_reply


def test_manual_lock_relocks_active_session(tmp_path, monkeypatch):
    (tmp_path / "notes.txt").write_text("hi")
    core, _, _driver = _core(tmp_path, monkeypatch)

    core.handle_input("Victor")
    core.handle_input(PHRASE)
    lock_reply = core.handle_input("Victor, lock yourself")
    assert "locked" in lock_reply.lower()

    tool_reply = core.handle_input(f"list files in {tmp_path}")
    assert "authenticate" in tool_reply.lower()


def test_open_application_after_authentication(tmp_path, monkeypatch):
    core, _, driver = _core(tmp_path, monkeypatch)

    core.handle_input("Victor")
    core.handle_input(PHRASE)
    reply = core.handle_input("open notepad")

    assert "opened" in reply.lower()
    assert driver.is_process_running("notepad.exe")


def test_open_application_denied_while_locked(tmp_path, monkeypatch):
    core, _, driver = _core(tmp_path, monkeypatch)

    reply = core.handle_input("open notepad")

    assert "authenticate" in reply.lower()
    assert not driver.is_process_running("notepad.exe")


def test_close_application_requires_confirmation_not_yet_available(tmp_path, monkeypatch):
    """close_application is MEDIUM risk (spec section 20: destructive
    actions require confirmation). Since no confirmation UI exists yet,
    it must be denied even for an authenticated session."""
    core, _, driver = _core(tmp_path, monkeypatch)
    driver.running_processes.add("notepad.exe")

    core.handle_input("Victor")
    core.handle_input(PHRASE)
    reply = core.handle_input("close notepad")

    assert driver.is_process_running("notepad.exe")
    assert "confirmation" in reply.lower() or "requires" in reply.lower()


def test_screenshot_after_authentication_reports_saved_path(tmp_path, monkeypatch):
    core, _, _driver = _core(tmp_path, monkeypatch)

    core.handle_input("Victor")
    core.handle_input(PHRASE)
    reply = core.handle_input("take a screenshot")

    assert "screenshot saved to" in reply.lower()
    assert str(tmp_path / "screenshots") in reply
    assert len(list((tmp_path / "screenshots").glob("*.png"))) == 1
