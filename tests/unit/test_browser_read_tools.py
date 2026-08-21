from app.tools.browser.driver import BrowserDriverError
from app.tools.browser.fake_driver import FakeBrowserDriver
from app.tools.browser.tool import (
    ExtractTextArgs,
    ExtractTextTool,
    OpenUrlArgs,
    OpenUrlTool,
    ReadPageArgs,
    ReadPageTool,
    SearchWebArgs,
    SearchWebTool,
)


def test_open_url_succeeds_and_verifies():
    driver = FakeBrowserDriver()
    tool = OpenUrlTool(driver)
    args = OpenUrlArgs(url="https://example.com")

    result = tool.run(args)
    result = tool.verify(args, result)

    assert result.success is True
    assert driver.get_active_url() == "https://example.com"


def test_open_url_driver_failure_is_captured():
    driver = FakeBrowserDriver()
    driver.fail_open = True
    tool = OpenUrlTool(driver)

    result = tool.run(OpenUrlArgs(url="https://example.com"))

    assert result.success is False
    assert result.error == "driver_error"


def test_search_web_returns_results():
    driver = FakeBrowserDriver()
    driver.canned_search_results = [
        {"title": "Result 1", "url": "https://a.com", "snippet": "a"},
        {"title": "Result 2", "url": "https://b.com", "snippet": "b"},
    ]
    tool = SearchWebTool(driver)

    result = tool.run(SearchWebArgs(query="test query"))

    assert result.success is True
    assert len(result.data["results"]) == 2


def test_search_web_no_results():
    driver = FakeBrowserDriver()
    tool = SearchWebTool(driver)
    result = tool.run(SearchWebArgs(query="nothing"))
    assert result.success is True
    assert result.data["results"] == []


def test_read_page_returns_active_tab_content():
    driver = FakeBrowserDriver()
    driver.page_registry["https://example.com"] = {
        "title": "Example Domain",
        "text": "This domain is for illustrative use.",
    }
    driver.open_url("https://example.com")

    tool = ReadPageTool(driver)
    result = tool.run(ReadPageArgs())

    assert result.success is True
    assert result.data["title"] == "Example Domain"
    assert "illustrative" in result.data["text"]


def test_extract_text_found():
    driver = FakeBrowserDriver()
    driver.page_registry["https://example.com"] = {
        "elements": {"h1": "Welcome"},
    }
    driver.open_url("https://example.com")

    tool = ExtractTextTool(driver)
    result = tool.run(ExtractTextArgs(selector="h1"))

    assert result.success is True
    assert result.data["text"] == "Welcome"


def test_extract_text_not_found():
    driver = FakeBrowserDriver()
    tool = ExtractTextTool(driver)
    result = tool.run(ExtractTextArgs(selector="#missing"))
    assert result.success is False
    assert result.error == "element_not_found"