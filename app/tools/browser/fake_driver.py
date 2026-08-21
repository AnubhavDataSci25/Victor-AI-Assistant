"""
FakeBrowserDriver - an in-memory stand-in for a real browser, used by
tests to exercise browser tool logic deterministically. Not used in
production; app/tools/factory.py selects PlaywrightBrowserDriver there.

Simulates a minimal multi-tab browser: each tab has a URL, title,
page text, an "elements" map (selector -> text, for click/extract/type
simulation), and back/forward history stacks.
"""

from __future__ import annotations

from app.tools.browser.driver import BrowserDriverError, SearchResult


class _Tab:
    def __init__(self, url: str = "about:blank", title: str = "", text: str = "") -> None:
        self.url = url
        self.title = title
        self.text = text
        self.elements: dict[str, str] = {}
        self.history: list[str] = []
        self.future: list[str] = []


class FakeBrowserDriver:
    def __init__(self) -> None:
        self._tabs: dict[int, _Tab] = {0: _Tab()}
        self._active_tab_id = 0
        self._next_tab_id = 1

        # Test control knobs
        self.canned_search_results: list[SearchResult] = []
        self.page_registry: dict[str, dict] = {}  # url -> {title, text, elements}
        self.fail_open: bool = False

    @property
    def _active(self) -> _Tab:
        return self._tabs[self._active_tab_id]

    def open_url(self, url: str) -> None:
        if self.fail_open:
            raise BrowserDriverError(f"Failed to load {url}")
        tab = self._active
        if tab.url != "about:blank":
            tab.history.append(tab.url)
        tab.future.clear()
        self._load(tab, url)

    def _load(self, tab: _Tab, url: str) -> None:
        page = self.page_registry.get(url, {})
        tab.url = url
        tab.title = page.get("title", url)
        tab.text = page.get("text", "")
        tab.elements = dict(page.get("elements", {}))

    def search_web(self, query: str) -> list[SearchResult]:
        return list(self.canned_search_results)

    def read_page(self) -> dict[str, str]:
        tab = self._active
        return {"url": tab.url, "title": tab.title, "text": tab.text}

    def extract_text(self, selector: str) -> str | None:
        return self._active.elements.get(selector)

    def click_element(self, selector: str) -> bool:
        return selector in self._active.elements

    def type_into_page(self, selector: str, text: str) -> bool:
        if selector not in self._active.elements:
            return False
        self._active.elements[selector] = text
        return True

    def scroll_page(self, direction: str, amount: int) -> None:
        pass  # no observable state to simulate

    def go_back(self) -> bool:
        tab = self._active
        if not tab.history:
            return False
        tab.future.append(tab.url)
        previous = tab.history.pop()
        self._load(tab, previous)
        return True

    def go_forward(self) -> bool:
        tab = self._active
        if not tab.future:
            return False
        tab.history.append(tab.url)
        next_url = tab.future.pop()
        self._load(tab, next_url)
        return True

    def open_tab(self, url: str | None) -> int:
        tab_id = self._next_tab_id
        self._next_tab_id += 1
        tab = _Tab()
        self._tabs[tab_id] = tab
        self._active_tab_id = tab_id
        if url:
            self._load(tab, url)
        return tab_id

    def close_tab(self, tab_id: int) -> bool:
        if tab_id not in self._tabs or len(self._tabs) <= 1:
            return False
        del self._tabs[tab_id]
        if self._active_tab_id == tab_id:
            self._active_tab_id = next(iter(self._tabs))
        return True

    def screenshot_page(self) -> bytes:
        return b"\x89PNG\r\n\x1a\n" + b"\x00" * 8

    def get_active_url(self) -> str | None:
        return self._active.url

    def get_active_title(self) -> str | None:
        return self._active.title