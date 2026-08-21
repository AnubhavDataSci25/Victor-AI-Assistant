"""
PlaywrightBrowserDriver - the real browser backend (spec section 24:
"Preferred tool: Playwright").

Cannot be exercised in this development sandbox: Playwright needs to
download browser binaries (`playwright install chromium`) from a CDN
this sandbox has no network access to. Imports are deferred to first
use, same pattern as WindowsComputerDriver in Phase 4, so this module
can still be imported and statically checked anywhere.

search_web uses DuckDuckGo's HTML-only endpoint
(html.duckduckgo.com/html/) rather than an API - no API key, no
paid service, consistent with the local-first/free-tooling policy
(rule 14/15). It's plain server-rendered HTML, so it doesn't need
JS execution to scrape, unlike DuckDuckGo's normal JS-heavy UI.
"""

from __future__ import annotations

from app.tools.browser.driver import BrowserDriverError, SearchResult

_SEARCH_URL = "https://www.bing.com/search?q={query}"


class PlaywrightBrowserDriver:
    def __init__(self, headless: bool = True, default_timeout_ms: int = 10_000) -> None:
        self._headless = headless
        self._default_timeout_ms = default_timeout_ms
        self._playwright = None
        self._browser = None
        self._context = None
        self._pages: dict[int, object] = {}
        self._active_tab_id = 0
        self._next_tab_id = 1

    def _ensure_started(self):
        if self._browser is not None:
            return
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise BrowserDriverError(
                "playwright is required for browser tools but is not "
                "installed. Run: pip install playwright && "
                "playwright install chromium"
            ) from exc

        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=self._headless)
            self._context = self._browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                )
            )
            page = self._context.new_page()
            page.set_default_timeout(self._default_timeout_ms)
            self._pages[0] = page
        except Exception as exc:  # noqa: BLE001
            raise BrowserDriverError(f"Failed to start browser: {exc}") from exc

    def _active_page(self):
        self._ensure_started()
        return self._pages[self._active_tab_id]

    def open_url(self, url: str) -> None:
        page = self._active_page()
        try:
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_load_state("networkidle", timeout=self._default_timeout_ms)
        except Exception as exc:  # noqa: BLE001
            raise BrowserDriverError(f"Failed to load {url}: {exc}") from exc

    def search_web(self, query: str) -> list[SearchResult]:
        page = self._active_page()
        try:
            page.goto(_SEARCH_URL.format(query=query), wait_until="domcontentloaded")
            page.wait_for_selector("li.b_algo", timeout=self._default_timeout_ms)
        except Exception as exc:  # noqa: BLE001
            raise BrowserDriverError(f"Search failed to load: {exc}") from exc

        try:
            # Bing's organic results are <li class="b_algo"> blocks, each
            # with an <h2><a> title/link and a snippet in .b_caption p
            # (or occasionally .b_snippet / .b_algoSlug depending on
            # result type).
            rows = page.eval_on_selector_all(
                "li.b_algo",
                """
                (items) => items.map(item => {
                    const link = item.querySelector('h2 a');
                    const snippetEl = item.querySelector('.b_caption p')
                        || item.querySelector('.b_snippet')
                        || item.querySelector('p');
                    return {
                        title: link ? link.innerText : '',
                        url: link ? (link.getAttribute('href') || '') : '',
                        snippet: snippetEl ? snippetEl.innerText : '',
                    };
                })
                """,
            )
        except Exception as exc:  # noqa: BLE001
            raise BrowserDriverError(f"Search result parsing failed: {exc}") from exc

        results: list[SearchResult] = []
        for row in rows[:10]:
            title = (row.get("title") or "").strip()
            url = (row.get("url") or "").strip()
            if not title or not url:
                continue
            results.append(
                SearchResult(title=title, url=url, snippet=(row.get("snippet") or "").strip())
            )
        return results

    def read_page(self) -> dict[str, str]:
        page = self._active_page()
        return {
            "url": page.url,
            "title": page.title(),
            "text": page.inner_text("body"),
        }

    def extract_text(self, selector: str) -> str | None:
        page = self._active_page()
        el = page.query_selector(selector)
        return el.inner_text() if el else None

    def click_element(self, selector: str) -> bool:
        page = self._active_page()
        el = page.query_selector(selector)
        if not el:
            return False
        el.click()
        return True

    def type_into_page(self, selector: str, text: str) -> bool:
        page = self._active_page()
        el = page.query_selector(selector)
        if not el:
            return False
        el.fill(text)
        return True

    def scroll_page(self, direction: str, amount: int) -> None:
        page = self._active_page()
        delta = amount if direction == "down" else -amount
        page.mouse.wheel(0, delta)

    def go_back(self) -> bool:
        page = self._active_page()
        response = page.go_back()
        return response is not None

    def go_forward(self) -> bool:
        page = self._active_page()
        response = page.go_forward()
        return response is not None

    def open_tab(self, url: str | None) -> int:
        self._ensure_started()
        page = self._context.new_page()
        page.set_default_timeout(self._default_timeout_ms)
        tab_id = self._next_tab_id
        self._next_tab_id += 1
        self._pages[tab_id] = page
        self._active_tab_id = tab_id
        if url:
            self.open_url(url)
        return tab_id

    def close_tab(self, tab_id: int) -> bool:
        if tab_id not in self._pages or len(self._pages) <= 1:
            return False
        self._pages[tab_id].close()
        del self._pages[tab_id]
        if self._active_tab_id == tab_id:
            self._active_tab_id = next(iter(self._pages))
        return True

    def screenshot_page(self) -> bytes:
        page = self._active_page()
        return page.screenshot(type="png")

    def get_active_url(self) -> str | None:
        return self._active_page().url

    def get_active_title(self) -> str | None:
        return self._active_page().title()

    def shutdown(self) -> None:
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()