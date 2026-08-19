from pathlib import Path

from app.tools.computer.fake_driver import FakeComputerDriver
from app.tools.computer.driver import DriverError
from app.tools.computer.tool import (
    FocusWindowTool,
    HotkeyArgs,
    HotkeyTool,
    PressKeyArgs,
    PressKeyTool,
    SwitchWindowTool,
    TakeScreenshotArgs,
    TakeScreenshotTool,
    TypeTextArgs,
    TypeTextTool,
    WindowTitleArgs,
)


def _driver_with_window(title: str = "Notepad") -> FakeComputerDriver:
    driver = FakeComputerDriver()
    driver.open_windows[title] = "notepad.exe"
    return driver


def test_focus_window_found_and_verified():
    driver = _driver_with_window("Notepad")
    tool = FocusWindowTool(driver)

    result = tool.run(WindowTitleArgs(title="Notepad"))
    result = tool.verify(WindowTitleArgs(title="Notepad"), result)

    assert result.success is True
    assert driver.active_window == "Notepad"


def test_focus_window_not_found():
    driver = FakeComputerDriver()
    tool = FocusWindowTool(driver)

    result = tool.run(WindowTitleArgs(title="Nonexistent"))

    assert result.success is False
    assert result.error == "window_not_found"


def test_switch_window_found():
    driver = _driver_with_window("Chrome")
    tool = SwitchWindowTool(driver)

    result = tool.run(WindowTitleArgs(title="chrome"))  # case-insensitive substring

    assert result.success is True


def test_type_text_records_call():
    driver = FakeComputerDriver()
    tool = TypeTextTool(driver)

    result = tool.run(TypeTextArgs(text="hello world"))

    assert result.success is True
    assert driver.typed_text_log == ["hello world"]


def test_type_text_rejects_empty_string():
    try:
        TypeTextArgs(text="")
        assert False, "expected validation error"
    except Exception:
        pass


def test_press_key_records_call():
    driver = FakeComputerDriver()
    tool = PressKeyTool(driver)

    result = tool.run(PressKeyArgs(key="enter"))

    assert result.success is True
    assert driver.pressed_keys_log == ["enter"]


def test_hotkey_records_call():
    driver = FakeComputerDriver()
    tool = HotkeyTool(driver)

    result = tool.run(HotkeyArgs(keys=["ctrl", "c"]))

    assert result.success is True
    assert driver.hotkey_log == [["ctrl", "c"]]


def test_hotkey_requires_at_least_two_keys():
    try:
        HotkeyArgs(keys=["ctrl"])
        assert False, "expected validation error"
    except Exception:
        pass


def test_take_screenshot_returns_success_with_saved_path(tmp_path):
    driver = FakeComputerDriver()
    tool = TakeScreenshotTool(driver, screenshot_directory=str(tmp_path / "shots"))

    result = tool.run(TakeScreenshotArgs())
    result = tool.verify(TakeScreenshotArgs(), result)

    assert result.success is True
    assert result.data["size_bytes"] > 0
    assert result.data["format"] == "png"
    assert result.data["path"].endswith(".png")
    assert (tmp_path / "shots").is_dir()
    assert Path(result.data["path"]).exists()
    assert driver.screenshot_calls == 1


def test_take_screenshot_returns_driver_error_without_raising():
    class ScreenshotFailingDriver(FakeComputerDriver):
        def take_screenshot(self) -> bytes:
            raise DriverError("pyscreeze is missing")

    tool = TakeScreenshotTool(ScreenshotFailingDriver())

    result = tool.run(TakeScreenshotArgs())

    assert result.success is False
    assert result.error == "driver_error"
    assert "Failed to capture screenshot" in result.message
