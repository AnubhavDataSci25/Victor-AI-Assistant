from app.tools.browser.fake_driver import FakeBrowserDriver
from app.tools.browser.tool import (
    ClickElementArgs,
    ClickElementTool,
    CloseTabArgs,
    CloseTabTool,
    GoBackTool,
    GoForwardTool,
    OpenTabArgs,
    OpenTabTool,
    ScreenshotPageTool,
    ScrollPageArgs,
    ScrollPageTool,
    TypeIntoPageArgs,
    TypeIntoPageTool,
    _NoArgs,
)


def _driver_with_button():
    driver = FakeBrowserDriver()
    driver.page_registry["https://example.com"] = {"elements": {"#submit": "Submit"}}
    driver.open_url("https://example.com")
    return driver


def test_click_element_found():
    driver = _driver_with_button()
    tool = ClickElementTool(driver)
    result = tool.run(ClickElementArgs(selector="#submit"))
    assert result.success is True


def test_click_element_not_found():
    driver = FakeBrowserDriver()
    tool = ClickElementTool(driver)
    result = tool.run(ClickElementArgs(selector="#missing"))
    assert result.success is False
    assert result.error == "element_not_found"


def test_type_into_page_found():
    driver = _driver_with_button()
    tool = TypeIntoPageTool(driver)
    result = tool.run(TypeIntoPageArgs(selector="#submit", text="hello"))
    assert result.success is True
    assert driver._active.elements["#submit"] == "hello"


def test_type_into_page_not_found():
    driver = FakeBrowserDriver()
    tool = TypeIntoPageTool(driver)
    result = tool.run(TypeIntoPageArgs(selector="#missing", text="hi"))
    assert result.success is False


def test_scroll_page_runs_without_error():
    driver = FakeBrowserDriver()
    tool = ScrollPageTool(driver)
    result = tool.run(ScrollPageArgs(direction="down", amount=300))
    assert result.success is True


def test_go_back_and_forward():
    driver = FakeBrowserDriver()
    driver.page_registry["https://a.com"] = {"title": "A"}
    driver.page_registry["https://b.com"] = {"title": "B"}
    driver.open_url("https://a.com")
    driver.open_url("https://b.com")

    back_tool = GoBackTool(driver)
    forward_tool = GoForwardTool(driver)

    back_result = back_tool.run(_NoArgs())
    assert back_result.success is True
    assert driver.get_active_url() == "https://a.com"

    forward_result = forward_tool.run(_NoArgs())
    assert forward_result.success is True
    assert driver.get_active_url() == "https://b.com"


def test_go_back_with_no_history_fails_cleanly():
    driver = FakeBrowserDriver()
    tool = GoBackTool(driver)
    result = tool.run(_NoArgs())
    assert result.success is False
    assert result.error == "no_history"


def test_open_and_close_tab():
    driver = FakeBrowserDriver()
    open_tool = OpenTabTool(driver)
    close_tool = CloseTabTool(driver)

    open_result = open_tool.run(OpenTabArgs(url=None))
    assert open_result.success is True
    tab_id = open_result.data["tab_id"]

    close_result = close_tool.run(CloseTabArgs(tab_id=tab_id))
    assert close_result.success is True


def test_close_tab_refuses_to_close_last_tab():
    driver = FakeBrowserDriver()
    tool = CloseTabTool(driver)
    # only tab 0 exists
    result = tool.run(CloseTabArgs(tab_id=0))
    assert result.success is False
    assert result.error == "close_failed"


def test_close_tab_is_medium_permission():
    from app.tools.permissions import PermissionLevel

    driver = FakeBrowserDriver()
    tool = CloseTabTool(driver)
    assert tool.permission_level == PermissionLevel.MEDIUM


def test_screenshot_page_returns_success_with_size():
    driver = FakeBrowserDriver()
    tool = ScreenshotPageTool(driver)
    result = tool.run(_NoArgs())
    result = tool.verify(_NoArgs(), result)
    assert result.success is True
    assert result.data["size_bytes"] > 0