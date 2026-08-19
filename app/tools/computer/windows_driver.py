"""
WindowsComputerDriver - the real OS-interaction backend for computer
control tools (spec section 20).

This module cannot be exercised in this development sandbox (Linux,
no display), so imports of psutil/pyautogui are deferred to first use
rather than module load time - the file can still be imported and
statically checked anywhere, but actually *using* a driver instance
on a non-Windows machine or without a display raises a clear
DriverError instead of an unhelpful ImportError deep in a call stack.

Design choices:
- open_application/close_application only ever receive a command or
  process name already resolved from the config whitelist by the
  calling tool - this module has no knowledge of "friendly names" and
  never invents a path.
- subprocess.Popen (not os.system/shell=True) is used for launching,
  so a whitelisted command string is passed as an argv list, not
  interpreted by a shell - this avoids shell-injection risk even
  though the command source is already trusted config, as defense in
  depth (rule 8: validate shell commands).
"""

from __future__ import annotations

import platform
import shlex
import subprocess

from app.tools.computer.driver import DriverError


def _require_windows() -> None:
    if platform.system() != "Windows":
        raise DriverError(
            "Computer control tools are implemented for Windows only. "
            f"This machine reports platform {platform.system()!r}."
        )


class WindowsComputerDriver:
    def __init__(self) -> None:
        self._psutil = None
        self._pyautogui = None

    # --- lazy, guarded imports -----------------------------------------

    def _psutil_module(self):
        if self._psutil is None:
            try:
                import psutil  # type: ignore[import-untyped]
            except ImportError as exc:
                raise DriverError(
                    "psutil is required for computer control tools but is "
                    "not installed. Run: pip install psutil"
                ) from exc
            self._psutil = psutil
        return self._psutil

    def _pyautogui_module(self):
        if self._pyautogui is None:
            try:
                import pyautogui  # type: ignore[import-untyped]
            except ImportError as exc:
                raise DriverError(
                    "pyautogui is required for keyboard/mouse/screenshot "
                    "tools but is not installed. Run: pip install pyautogui"
                ) from exc
            except Exception as exc:  # noqa: BLE001 - e.g. no display available
                raise DriverError(
                    f"pyautogui could not initialize: {exc}"
                ) from exc
            pyautogui.FAILSAFE = True  # moving mouse to a screen corner aborts
            self._pyautogui = pyautogui
        return self._pyautogui

    # --- process control -------------------------------------------------

    def open_application(self, command: str) -> None:
        _require_windows()
        try:
            subprocess.Popen(shlex.split(command, posix=False))
        except (OSError, ValueError) as exc:
            raise DriverError(f"Failed to launch {command!r}: {exc}") from exc

    def close_application(self, process_name: str) -> bool:
        _require_windows()
        psutil = self._psutil_module()
        found = False
        for proc in psutil.process_iter(["name"]):
            try:
                if (proc.info.get("name") or "").lower() == process_name.lower():
                    found = True
                    proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return found

    def is_process_running(self, process_name: str) -> bool:
        _require_windows()
        psutil = self._psutil_module()
        return any(
            (proc.info.get("name") or "").lower() == process_name.lower()
            for proc in psutil.process_iter(["name"])
        )

    # --- windows -----------------------------------------------------------

    def focus_window(self, title: str) -> bool:
        _require_windows()
        pyautogui = self._pyautogui_module()
        matches = pyautogui.getWindowsWithTitle(title)
        if not matches:
            return False
        window = matches[0]
        window.activate()
        return True

    def switch_window(self, title: str) -> bool:
        return self.focus_window(title)

    def get_active_window_title(self) -> str | None:
        _require_windows()
        pyautogui = self._pyautogui_module()
        active = pyautogui.getActiveWindow()
        return active.title if active else None

    # --- keyboard / mouse -------------------------------------------------

    def type_text(self, text: str) -> None:
        _require_windows()
        self._pyautogui_module().write(text)

    def press_key(self, key: str) -> None:
        _require_windows()
        self._pyautogui_module().press(key)

    def hotkey(self, keys: list[str]) -> None:
        _require_windows()
        self._pyautogui_module().hotkey(*keys)

    # --- screen -----------------------------------------------------------

    def take_screenshot(self) -> bytes:
        _require_windows()
        pyautogui = self._pyautogui_module()
        import io

        image = pyautogui.screenshot()
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()