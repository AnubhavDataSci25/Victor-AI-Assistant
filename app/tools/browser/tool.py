"""
Browser tools (spec section 24). Thin, validated wrappers around a
BrowserDriver call - no Playwright-specific code here, matching the
computer-control tools' separation.

Permission levels, consistent with the risk philosophy established in
Phase 4/5 (read-only = SAFE, real-but-bounded side effect = LOW,
possible data loss = MEDIUM):

- open_url, search_web, read_page, extract_text, scroll_page,
  go_back, go_forward, open_tab, screenshot_page: SAFE. None of these
  destroy anything; open_tab only adds.
- click_element, type_into_page: LOW. A click or typed input has a
  real effect (could submit a form, trigger a purchase flow) but
  matches the same risk tier as computer control's type_text/press_key
  - not classified as destructive by default.
- close_tab: MEDIUM. Closing a tab can lose an unsubmitted form or
  unsaved state, the same reasoning as close_application in Phase 4.
  Denied by default until Phase 12's confirmation flow exists.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.tools.base import Tool
from app.tools.browser.driver import BrowserDriver, BrowserDriverError
from app.tools.models import ToolResult
from app.tools.permissions import PermissionLevel


# --- open_url ------------------------------------------------------------


class OpenUrlArgs(BaseModel):
    url: str

    model_config = {"extra": "forbid"}


class OpenUrlTool(Tool):
    name = "open_url"
    description = "Navigate the active browser tab to a URL."
    permission_level = PermissionLevel.SAFE
    args_model = OpenUrlArgs

    def __init__(self, driver: BrowserDriver) -> None:
        self._driver = driver

    def run(self, args: BaseModel) -> ToolResult:
        assert isinstance(args, OpenUrlArgs)
        try:
            self._driver.open_url(args.url)
        except BrowserDriverError as exc:
            return ToolResult(
                success=False, tool=self.name, message=f"Failed to open {args.url}: {exc}",
                error="driver_error",
            )
        return ToolResult(success=True, tool=self.name, message=f"Opened {args.url}.")

    def verify(self, args: BaseModel, result: ToolResult) -> ToolResult:
        if not result.success:
            return result
        active = self._driver.get_active_url() or ""
        if not active or active == "about:blank":
            return ToolResult(
                success=False, tool=self.name,
                message="Navigation could not be verified, Sir.",
                error="verification_failed",
            )
        return result


# --- search_web -----------------------------------------------------------


class SearchWebArgs(BaseModel):
    query: str

    model_config = {"extra": "forbid"}


class SearchWebTool(Tool):
    name = "search_web"
    description = "Search the web and return a list of results."
    permission_level = PermissionLevel.SAFE
    args_model = SearchWebArgs

    def __init__(self, driver: BrowserDriver) -> None:
        self._driver = driver

    def run(self, args: BaseModel) -> ToolResult:
        assert isinstance(args, SearchWebArgs)
        try:
            results = self._driver.search_web(args.query)
        except BrowserDriverError as exc:
            return ToolResult(
                success=False, tool=self.name, message=f"Search failed: {exc}",
                error="driver_error",
            )
        return ToolResult(
            success=True, tool=self.name,
            message=f"Found {len(results)} result(s) for {args.query!r}.",
            data={"results": results},
        )


# --- read_page / extract_text --------------------------------------------


class ReadPageArgs(BaseModel):
    model_config = {"extra": "forbid"}


class ReadPageTool(Tool):
    name = "read_page"
    description = "Read the title and visible text of the active page."
    permission_level = PermissionLevel.SAFE
    args_model = ReadPageArgs

    def __init__(self, driver: BrowserDriver) -> None:
        self._driver = driver

    def run(self, args: BaseModel) -> ToolResult:
        page = self._driver.read_page()
        return ToolResult(
            success=True, tool=self.name,
            message=f"Read page: {page.get('title', '')}.",
            data=page,
        )


class ExtractTextArgs(BaseModel):
    selector: str

    model_config = {"extra": "forbid"}


class ExtractTextTool(Tool):
    name = "extract_text"
    description = "Extract the text content of a specific element by CSS selector."
    permission_level = PermissionLevel.SAFE
    args_model = ExtractTextArgs

    def __init__(self, driver: BrowserDriver) -> None:
        self._driver = driver

    def run(self, args: BaseModel) -> ToolResult:
        assert isinstance(args, ExtractTextArgs)
        text = self._driver.extract_text(args.selector)
        if text is None:
            return ToolResult(
                success=False, tool=self.name,
                message=f"No element matching {args.selector!r} was found, Sir.",
                error="element_not_found",
            )
        return ToolResult(
            success=True, tool=self.name, message="Extracted text.",
            data={"selector": args.selector, "text": text},
        )


# --- click_element / type_into_page (LOW) ----------------------------------


class ClickElementArgs(BaseModel):
    selector: str

    model_config = {"extra": "forbid"}


class ClickElementTool(Tool):
    name = "click_element"
    description = "Click an element on the page by CSS selector."
    permission_level = PermissionLevel.LOW
    args_model = ClickElementArgs

    def __init__(self, driver: BrowserDriver) -> None:
        self._driver = driver

    def run(self, args: BaseModel) -> ToolResult:
        assert isinstance(args, ClickElementArgs)
        clicked = self._driver.click_element(args.selector)
        if not clicked:
            return ToolResult(
                success=False, tool=self.name,
                message=f"No element matching {args.selector!r} was found, Sir.",
                error="element_not_found",
            )
        return ToolResult(success=True, tool=self.name, message=f"Clicked {args.selector}.")


class TypeIntoPageArgs(BaseModel):
    selector: str
    text: str

    model_config = {"extra": "forbid"}


class TypeIntoPageTool(Tool):
    name = "type_into_page"
    description = "Type text into a page element by CSS selector."
    permission_level = PermissionLevel.LOW
    args_model = TypeIntoPageArgs

    def __init__(self, driver: BrowserDriver) -> None:
        self._driver = driver

    def run(self, args: BaseModel) -> ToolResult:
        assert isinstance(args, TypeIntoPageArgs)
        typed = self._driver.type_into_page(args.selector, args.text)
        if not typed:
            return ToolResult(
                success=False, tool=self.name,
                message=f"No element matching {args.selector!r} was found, Sir.",
                error="element_not_found",
            )
        return ToolResult(
            success=True, tool=self.name,
            message=f"Typed into {args.selector}.",
        )


# --- scroll_page / go_back / go_forward --------------------------------


class ScrollPageArgs(BaseModel):
    direction: str = Field(pattern="^(up|down)$")
    amount: int = Field(default=500, ge=1, le=10_000)

    model_config = {"extra": "forbid"}


class ScrollPageTool(Tool):
    name = "scroll_page"
    description = "Scroll the active page up or down."
    permission_level = PermissionLevel.SAFE
    args_model = ScrollPageArgs

    def __init__(self, driver: BrowserDriver) -> None:
        self._driver = driver

    def run(self, args: BaseModel) -> ToolResult:
        assert isinstance(args, ScrollPageArgs)
        self._driver.scroll_page(args.direction, args.amount)
        return ToolResult(
            success=True, tool=self.name, message=f"Scrolled {args.direction}."
        )


class _NoArgs(BaseModel):
    model_config = {"extra": "forbid"}


class GoBackTool(Tool):
    name = "go_back"
    description = "Navigate back to the previous page."
    permission_level = PermissionLevel.SAFE
    args_model = _NoArgs

    def __init__(self, driver: BrowserDriver) -> None:
        self._driver = driver

    def run(self, args: BaseModel) -> ToolResult:
        moved = self._driver.go_back()
        if not moved:
            return ToolResult(
                success=False, tool=self.name, message="No previous page, Sir.",
                error="no_history",
            )
        return ToolResult(success=True, tool=self.name, message="Went back.")


class GoForwardTool(Tool):
    name = "go_forward"
    description = "Navigate forward to the next page."
    permission_level = PermissionLevel.SAFE
    args_model = _NoArgs

    def __init__(self, driver: BrowserDriver) -> None:
        self._driver = driver

    def run(self, args: BaseModel) -> ToolResult:
        moved = self._driver.go_forward()
        if not moved:
            return ToolResult(
                success=False, tool=self.name, message="No forward page, Sir.",
                error="no_history",
            )
        return ToolResult(success=True, tool=self.name, message="Went forward.")


# --- open_tab (SAFE) / close_tab (MEDIUM) ----------------------------------


class OpenTabArgs(BaseModel):
    url: str | None = None

    model_config = {"extra": "forbid"}


class OpenTabTool(Tool):
    name = "open_tab"
    description = "Open a new browser tab, optionally navigating it to a URL."
    permission_level = PermissionLevel.SAFE
    args_model = OpenTabArgs

    def __init__(self, driver: BrowserDriver) -> None:
        self._driver = driver

    def run(self, args: BaseModel) -> ToolResult:
        assert isinstance(args, OpenTabArgs)
        try:
            tab_id = self._driver.open_tab(args.url)
        except BrowserDriverError as exc:
            return ToolResult(
                success=False, tool=self.name, message=f"Failed to open tab: {exc}",
                error="driver_error",
            )
        return ToolResult(
            success=True, tool=self.name, message=f"Opened tab {tab_id}.",
            data={"tab_id": tab_id},
        )


class CloseTabArgs(BaseModel):
    tab_id: int

    model_config = {"extra": "forbid"}


class CloseTabTool(Tool):
    name = "close_tab"
    description = "Close a browser tab by id."
    permission_level = PermissionLevel.MEDIUM
    args_model = CloseTabArgs

    def __init__(self, driver: BrowserDriver) -> None:
        self._driver = driver

    def run(self, args: BaseModel) -> ToolResult:
        assert isinstance(args, CloseTabArgs)
        closed = self._driver.close_tab(args.tab_id)
        if not closed:
            return ToolResult(
                success=False, tool=self.name,
                message=f"Couldn't close tab {args.tab_id}, Sir - it may be the only tab open.",
                error="close_failed",
            )
        return ToolResult(success=True, tool=self.name, message=f"Closed tab {args.tab_id}.")


# --- screenshot_page (SAFE) ------------------------------------------------


class ScreenshotPageTool(Tool):
    name = "screenshot_page"
    description = "Capture a screenshot of the active browser tab."
    permission_level = PermissionLevel.SAFE
    args_model = _NoArgs

    def __init__(self, driver: BrowserDriver) -> None:
        self._driver = driver

    def run(self, args: BaseModel) -> ToolResult:
        image_bytes = self._driver.screenshot_page()
        return ToolResult(
            success=True, tool=self.name, message="Screenshot captured.",
            data={"size_bytes": len(image_bytes), "format": "png"},
        )

    def verify(self, args: BaseModel, result: ToolResult) -> ToolResult:
        if not result.success:
            return result
        if result.data.get("size_bytes", 0) <= 0:
            return ToolResult(
                success=False, tool=self.name, message="Screenshot came back empty, Sir.",
                error="verification_failed",
            )
        return result