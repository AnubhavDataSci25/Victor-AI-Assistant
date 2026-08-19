"""
Computer control tools (spec section 20, initial set from section 39).

Every tool here is a thin, validated wrapper around a ComputerDriver
call. None of them contain OS-specific code themselves - that
separation is what makes them unit-testable with FakeComputerDriver.

Permission level judgment calls (documented here since section 12's
table doesn't cover all of these explicitly):

- open_application / focus_window / switch_window / take_screenshot:
  SAFE, matching section 12's explicit "Open application -> SAFE".
  These don't destroy or send anything.
- close_application: MEDIUM, not SAFE. Section 12 doesn't list it, but
  closing an app can lose unsaved user work - closer in risk to
  "modify configuration" than to "open application". Currently means
  it's denied by default until a confirmation flow exists (Phase 12).
- type_text / press_key / hotkey: LOW rather than SAFE. They're not
  destructive, but they have a real side effect on whatever
  application currently has focus (could type into the wrong window).
  LOW and SAFE both auto-execute today, so this is mainly forward
  documentation for when permission policy gets more granular.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from app.tools.base import Tool
from app.tools.computer.driver import ComputerDriver, DriverError
from app.tools.models import ToolResult
from app.tools.permissions import PermissionLevel


# --- shared application whitelist lookup -----------------------------------


def _resolve_application(
    name: str, applications: dict[str, str]
) -> tuple[str, str] | None:
    """Look up a friendly application name in the configured whitelist.
    Returns (launch_command, process_name) or None if not whitelisted."""
    command = applications.get(name.strip().lower())
    if command is None:
        return None
    # Best-effort process name: the executable's basename, no path/args.
    process_name = command.split()[0].split("\\")[-1].split("/")[-1]
    return command, process_name


# --- open_application --------------------------------------------------


class OpenApplicationArgs(BaseModel):
    application: str

    model_config = {"extra": "forbid"}


class OpenApplicationTool(Tool):
    name = "open_application"
    description = "Open a whitelisted application by its configured friendly name."
    permission_level = PermissionLevel.SAFE
    args_model = OpenApplicationArgs
    timeout_seconds = 10.0

    def __init__(
        self,
        driver: ComputerDriver,
        applications: dict[str, str],
        verify_poll_interval: float = 0.2,
        verify_max_wait: float = 3.0,
    ) -> None:
        self._driver = driver
        self._applications = applications
        self._verify_poll_interval = verify_poll_interval
        self._verify_max_wait = verify_max_wait

    def run(self, args: BaseModel) -> ToolResult:
        assert isinstance(args, OpenApplicationArgs)
        resolved = _resolve_application(args.application, self._applications)
        if resolved is None:
            return ToolResult(
                success=False,
                tool=self.name,
                message=(
                    f"{args.application!r} is not a configured application, Sir. "
                    "Add it under computer.applications in config first."
                ),
                error="application_not_whitelisted",
            )
        command, process_name = resolved
        try:
            self._driver.open_application(command)
        except DriverError as exc:
            return ToolResult(
                success=False,
                tool=self.name,
                message=f"Failed to open {args.application}: {exc}",
                error="driver_error",
            )
        return ToolResult(
            success=True,
            tool=self.name,
            message=f"Opened {args.application}.",
            data={"process_name": process_name},
        )

    def verify(self, args: BaseModel, result: ToolResult) -> ToolResult:
        if not result.success:
            return result
        process_name = result.data.get("process_name", "")

        import time

        deadline = time.monotonic() + self._verify_max_wait
        running = self._driver.is_process_running(process_name)
        while not running and time.monotonic() < deadline:
            time.sleep(self._verify_poll_interval)
            running = self._driver.is_process_running(process_name)

        if not running:
            return ToolResult(
                success=False,
                tool=self.name,
                message=(
                    f"Launch command for {result.data.get('process_name')} "
                    "ran, but I couldn't confirm it's actually running, Sir."
                ),
                error="verification_failed",
            )
        return result


# --- close_application ---------------------------------------------------


class CloseApplicationArgs(BaseModel):
    application: str

    model_config = {"extra": "forbid"}


class CloseApplicationTool(Tool):
    name = "close_application"
    description = "Close a whitelisted, currently running application."
    permission_level = PermissionLevel.MEDIUM
    args_model = CloseApplicationArgs
    timeout_seconds = 10.0

    def __init__(self, driver: ComputerDriver, applications: dict[str, str]) -> None:
        self._driver = driver
        self._applications = applications

    def run(self, args: BaseModel) -> ToolResult:
        assert isinstance(args, CloseApplicationArgs)
        resolved = _resolve_application(args.application, self._applications)
        if resolved is None:
            return ToolResult(
                success=False,
                tool=self.name,
                message=f"{args.application!r} is not a configured application, Sir.",
                error="application_not_whitelisted",
            )
        _, process_name = resolved
        try:
            closed = self._driver.close_application(process_name)
        except DriverError as exc:
            return ToolResult(
                success=False,
                tool=self.name,
                message=f"Failed to close {args.application}: {exc}",
                error="driver_error",
            )
        if not closed:
            return ToolResult(
                success=False,
                tool=self.name,
                message=f"{args.application} doesn't appear to be running, Sir.",
                error="not_running",
            )
        return ToolResult(
            success=True,
            tool=self.name,
            message=f"Closed {args.application}.",
            data={"process_name": process_name},
        )

    def verify(self, args: BaseModel, result: ToolResult) -> ToolResult:
        if not result.success:
            return result
        process_name = result.data.get("process_name", "")
        if self._driver.is_process_running(process_name):
            return ToolResult(
                success=False,
                tool=self.name,
                message=f"Asked {process_name} to close, but it's still running, Sir.",
                error="verification_failed",
            )
        return result


# --- focus_window / switch_window ---------------------------------------


class WindowTitleArgs(BaseModel):
    title: str

    model_config = {"extra": "forbid"}


class FocusWindowTool(Tool):
    name = "focus_window"
    description = "Bring a window to the foreground by (partial) title."
    permission_level = PermissionLevel.SAFE
    args_model = WindowTitleArgs

    def __init__(self, driver: ComputerDriver) -> None:
        self._driver = driver

    def run(self, args: BaseModel) -> ToolResult:
        assert isinstance(args, WindowTitleArgs)
        found = self._driver.focus_window(args.title)
        if not found:
            return ToolResult(
                success=False,
                tool=self.name,
                message=f"No window matching {args.title!r} was found, Sir.",
                error="window_not_found",
            )
        return ToolResult(
            success=True, tool=self.name, message=f"Focused {args.title}."
        )

    def verify(self, args: BaseModel, result: ToolResult) -> ToolResult:
        if not result.success:
            return result
        active = self._driver.get_active_window_title() or ""
        if args.title.lower() not in active.lower():
            return ToolResult(
                success=False,
                tool=self.name,
                message=f"Tried to focus {args.title}, but it isn't the active window, Sir.",
                error="verification_failed",
            )
        return result


class SwitchWindowTool(Tool):
    name = "switch_window"
    description = "Switch focus to a different open window by (partial) title."
    permission_level = PermissionLevel.SAFE
    args_model = WindowTitleArgs

    def __init__(self, driver: ComputerDriver) -> None:
        self._driver = driver

    def run(self, args: BaseModel) -> ToolResult:
        assert isinstance(args, WindowTitleArgs)
        found = self._driver.switch_window(args.title)
        if not found:
            return ToolResult(
                success=False,
                tool=self.name,
                message=f"No window matching {args.title!r} was found, Sir.",
                error="window_not_found",
            )
        return ToolResult(
            success=True, tool=self.name, message=f"Switched to {args.title}."
        )

    def verify(self, args: BaseModel, result: ToolResult) -> ToolResult:
        if not result.success:
            return result
        active = self._driver.get_active_window_title() or ""
        if args.title.lower() not in active.lower():
            return ToolResult(
                success=False,
                tool=self.name,
                message=f"Tried to switch to {args.title}, but it isn't active, Sir.",
                error="verification_failed",
            )
        return result


# --- type_text / press_key / hotkey --------------------------------------


class TypeTextArgs(BaseModel):
    text: str

    model_config = {"extra": "forbid"}

    @field_validator("text")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("text must not be empty")
        return value


class TypeTextTool(Tool):
    name = "type_text"
    description = "Type text into whatever application currently has focus."
    permission_level = PermissionLevel.LOW
    args_model = TypeTextArgs

    def __init__(self, driver: ComputerDriver) -> None:
        self._driver = driver

    def run(self, args: BaseModel) -> ToolResult:
        assert isinstance(args, TypeTextArgs)
        self._driver.type_text(args.text)
        return ToolResult(
            success=True,
            tool=self.name,
            message=f"Typed {len(args.text)} character(s).",
        )

    def verify(self, args: BaseModel, result: ToolResult) -> ToolResult:
        # No reliable read-back exists for typed keystrokes; success here
        # reflects that the driver call completed without error, not
        # that the correct field received the text.
        return result


class PressKeyArgs(BaseModel):
    key: str

    model_config = {"extra": "forbid"}


class PressKeyTool(Tool):
    name = "press_key"
    description = "Press a single key (e.g. 'enter', 'esc', 'tab')."
    permission_level = PermissionLevel.LOW
    args_model = PressKeyArgs

    def __init__(self, driver: ComputerDriver) -> None:
        self._driver = driver

    def run(self, args: BaseModel) -> ToolResult:
        assert isinstance(args, PressKeyArgs)
        self._driver.press_key(args.key)
        return ToolResult(
            success=True, tool=self.name, message=f"Pressed {args.key}."
        )


class HotkeyArgs(BaseModel):
    keys: list[str] = Field(min_length=2)

    model_config = {"extra": "forbid"}


class HotkeyTool(Tool):
    name = "hotkey"
    description = "Press a key combination, e.g. ['ctrl', 'c']."
    permission_level = PermissionLevel.LOW
    args_model = HotkeyArgs

    def __init__(self, driver: ComputerDriver) -> None:
        self._driver = driver

    def run(self, args: BaseModel) -> ToolResult:
        assert isinstance(args, HotkeyArgs)
        self._driver.hotkey(args.keys)
        combo = "+".join(args.keys)
        return ToolResult(success=True, tool=self.name, message=f"Pressed {combo}.")


# --- take_screenshot -------------------------------------------------------


class TakeScreenshotArgs(BaseModel):
    model_config = {"extra": "forbid"}


class TakeScreenshotTool(Tool):
    name = "take_screenshot"
    description = "Capture a screenshot of the current screen."
    permission_level = PermissionLevel.SAFE
    args_model = TakeScreenshotArgs

    def __init__(
        self, driver: ComputerDriver, screenshot_directory: str = "screenshots"
    ) -> None:
        self._driver = driver
        self._screenshot_directory = Path(screenshot_directory)

    def run(self, args: BaseModel) -> ToolResult:
        try:
            image_bytes = self._driver.take_screenshot()
        except DriverError as exc:
            return ToolResult(
                success=False,
                tool=self.name,
                message=f"Failed to capture screenshot: {exc}",
                error="driver_error",
            )
        try:
            self._screenshot_directory.mkdir(parents=True, exist_ok=True)
            filename = datetime.now().strftime("screenshot_%Y%m%d_%H%M%S_%f.png")
            path = self._screenshot_directory / filename
            path.write_bytes(image_bytes)
        except OSError as exc:
            return ToolResult(
                success=False,
                tool=self.name,
                message=f"Screenshot captured but could not be saved: {exc}",
                error="os_permission_denied"
                if isinstance(exc, PermissionError)
                else "save_failed",
            )
        return ToolResult(
            success=True,
            tool=self.name,
            message=f"Screenshot saved to {path}.",
            data={
                "size_bytes": len(image_bytes),
                "format": "png",
                "path": str(path),
            },
        )

    def verify(self, args: BaseModel, result: ToolResult) -> ToolResult:
        if not result.success:
            return result
        if result.data.get("size_bytes", 0) <= 0:
            return ToolResult(
                success=False,
                tool=self.name,
                message="Screenshot came back empty, Sir.",
                error="verification_failed",
            )
        return result
