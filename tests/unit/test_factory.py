from app.config import load_config
from app.tools.computer.fake_driver import FakeComputerDriver
from app.tools.factory import build_registry


def _config():
    config = load_config("config/default.yaml")
    config.computer.applications = {"notepad": "notepad.exe"}
    return config


def test_computer_tools_registered_when_driver_injected():
    registry = build_registry(_config(), computer_driver=FakeComputerDriver())
    names = {t["name"] for t in registry.list_tools()}
    assert {
        "open_application",
        "close_application",
        "focus_window",
        "switch_window",
        "type_text",
        "press_key",
        "hotkey",
        "take_screenshot",
    }.issubset(names)


def test_computer_tools_skipped_when_driver_is_none():
    registry = build_registry(_config(), computer_driver=None)
    names = {t["name"] for t in registry.list_tools()}
    assert "open_application" not in names
    # filesystem tool is still there regardless
    assert "list_directory" in names


def test_filesystem_tool_always_registered_regardless_of_driver():
    registry = build_registry(_config(), computer_driver=None)
    assert registry.get("list_directory") is not None