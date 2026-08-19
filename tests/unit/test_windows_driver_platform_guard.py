"""
These tests exercise WindowsComputerDriver's platform guard - the one
part of it we can actually verify from this (non-Windows) sandbox.
The OS-interaction logic (subprocess/psutil/pyautogui calls) is not
exercised here; see app/tools/computer/fake_driver.py and its tests
for the tool-logic coverage, and README.md for the manual
verification steps required on an actual Windows machine.
"""

import platform

import pytest

from app.tools.computer.driver import DriverError
from app.tools.computer.windows_driver import WindowsComputerDriver

pytestmark = pytest.mark.skipif(
    platform.system() == "Windows",
    reason="this test asserts the non-Windows refusal path",
)


def test_open_application_refuses_on_non_windows():
    driver = WindowsComputerDriver()
    with pytest.raises(DriverError, match="Windows"):
        driver.open_application("notepad.exe")


def test_take_screenshot_refuses_on_non_windows():
    driver = WindowsComputerDriver()
    with pytest.raises(DriverError, match="Windows"):
        driver.take_screenshot()


def test_is_process_running_refuses_on_non_windows():
    driver = WindowsComputerDriver()
    with pytest.raises(DriverError, match="Windows"):
        driver.is_process_running("notepad.exe")