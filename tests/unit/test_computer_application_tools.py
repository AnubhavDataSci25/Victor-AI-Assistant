from app.tools.computer.driver import DriverError
from app.tools.computer.fake_driver import FakeComputerDriver
from app.tools.computer.tool import (
    CloseApplicationArgs,
    CloseApplicationTool,
    OpenApplicationArgs,
    OpenApplicationTool,
)

APPLICATIONS = {"notepad": "notepad.exe"}


def test_open_whitelisted_application_succeeds():
    driver = FakeComputerDriver()
    tool = OpenApplicationTool(driver, APPLICATIONS, verify_poll_interval=0.01, verify_max_wait=0.05)

    result = tool.run(OpenApplicationArgs(application="notepad"))
    result = tool.verify(OpenApplicationArgs(application="notepad"), result)

    assert result.success is True
    assert driver.is_process_running("notepad.exe")


def test_open_non_whitelisted_application_is_refused():
    driver = FakeComputerDriver()
    tool = OpenApplicationTool(driver, APPLICATIONS)

    result = tool.run(OpenApplicationArgs(application="some_random_exe"))

    assert result.success is False
    assert result.error == "application_not_whitelisted"


def test_open_application_case_insensitive_lookup():
    driver = FakeComputerDriver()
    tool = OpenApplicationTool(driver, APPLICATIONS, verify_poll_interval=0.01, verify_max_wait=0.05)

    result = tool.run(OpenApplicationArgs(application="NotePad"))
    assert result.success is True


def test_open_application_driver_failure_is_captured():
    driver = FakeComputerDriver()
    driver.fail_open = True
    tool = OpenApplicationTool(driver, APPLICATIONS)

    result = tool.run(OpenApplicationArgs(application="notepad"))

    assert result.success is False
    assert result.error == "driver_error"


def test_open_application_verification_fails_if_process_never_starts():
    driver = FakeComputerDriver()
    driver.open_launch_delay_ticks = 999  # never actually starts
    tool = OpenApplicationTool(driver, APPLICATIONS, verify_poll_interval=0.01, verify_max_wait=0.03)

    result = tool.run(OpenApplicationArgs(application="notepad"))
    result = tool.verify(OpenApplicationArgs(application="notepad"), result)

    assert result.success is False
    assert result.error == "verification_failed"


def test_close_running_application_succeeds():
    driver = FakeComputerDriver()
    driver.running_processes.add("notepad.exe")
    tool = CloseApplicationTool(driver, APPLICATIONS)

    result = tool.run(CloseApplicationArgs(application="notepad"))
    result = tool.verify(CloseApplicationArgs(application="notepad"), result)

    assert result.success is True
    assert not driver.is_process_running("notepad.exe")


def test_close_application_not_running_fails_cleanly():
    driver = FakeComputerDriver()
    tool = CloseApplicationTool(driver, APPLICATIONS)

    result = tool.run(CloseApplicationArgs(application="notepad"))

    assert result.success is False
    assert result.error == "not_running"


def test_close_non_whitelisted_application_is_refused():
    driver = FakeComputerDriver()
    tool = CloseApplicationTool(driver, APPLICATIONS)

    result = tool.run(CloseApplicationArgs(application="not_configured"))

    assert result.success is False
    assert result.error == "application_not_whitelisted"


def test_close_application_driver_failure_is_captured():
    driver = FakeComputerDriver()
    driver.running_processes.add("notepad.exe")
    driver.fail_close = True
    tool = CloseApplicationTool(driver, APPLICATIONS)

    result = tool.run(CloseApplicationArgs(application="notepad"))

    assert result.success is False
    assert result.error == "driver_error"