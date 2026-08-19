"""
FakeComputerDriver - an in-memory stand-in for real OS interaction,
used by tests to exercise tool logic (validation, permission,
verification, structured results) deterministically and without a
display.

Not used in production. app/tools/factory.py selects
WindowsComputerDriver there and only falls back to this for tests
that construct a registry directly with a driver override.
"""

from __future__ import annotations

from app.tools.computer.driver import DriverError


class FakeComputerDriver:
    def __init__(self) -> None:
        self.running_processes: set[str] = set()
        self.open_windows: dict[str, str] = {}  # title -> process_name
        self.active_window: str | None = None
        self.typed_text_log: list[str] = []
        self.pressed_keys_log: list[str] = []
        self.hotkey_log: list[list[str]] = []
        self.screenshot_calls: int = 0

        # Test control knobs
        self.fail_open: bool = False
        self.fail_close: bool = False
        self.open_launch_delay_ticks: int = 0  # simulate async startup

    def open_application(self, command: str) -> None:
        if self.fail_open:
            raise DriverError(f"Failed to launch: {command}")
        process_name = command.split()[0]
        if self.open_launch_delay_ticks > 0:
            self.open_launch_delay_ticks -= 1
            return  # process not "running" yet - simulates launch latency
        self.running_processes.add(process_name)
        self.open_windows[process_name] = process_name
        self.active_window = process_name

    def tick_process_startup(self) -> None:
        """Test helper: simulate the delayed process actually starting."""
        if self.open_launch_delay_ticks > 0:
            self.open_launch_delay_ticks -= 1

    def close_application(self, process_name: str) -> bool:
        if self.fail_close:
            raise DriverError(f"Failed to close: {process_name}")
        if process_name not in self.running_processes:
            return False
        self.running_processes.discard(process_name)
        self.open_windows.pop(process_name, None)
        if self.active_window == process_name:
            self.active_window = None
        return True

    def is_process_running(self, process_name: str) -> bool:
        return process_name in self.running_processes

    def focus_window(self, title: str) -> bool:
        for window_title in self.open_windows:
            if title.lower() in window_title.lower():
                self.active_window = window_title
                return True
        return False

    def switch_window(self, title: str) -> bool:
        return self.focus_window(title)

    def get_active_window_title(self) -> str | None:
        return self.active_window

    def type_text(self, text: str) -> None:
        self.typed_text_log.append(text)

    def press_key(self, key: str) -> None:
        self.pressed_keys_log.append(key)

    def hotkey(self, keys: list[str]) -> None:
        self.hotkey_log.append(keys)

    def take_screenshot(self) -> bytes:
        self.screenshot_calls += 1
        # Minimal valid PNG header + IEND so byte-level checks pass.
        return b"\x89PNG\r\n\x1a\n" + b"\x00" * 8