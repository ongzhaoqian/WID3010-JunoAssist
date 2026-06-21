from __future__ import annotations
import asyncio
import logging

_log = logging.getLogger("juno.playwright_game")


class PlaywrightGamePlayer:
    """Opens a Chromium browser via Playwright to the destressing game site.

    Keeps a single browser instance alive, separate from the music player's
    browser, so opening the game does not interrupt playing music and vice versa.
    """

    def __init__(self) -> None:
        self._playwright = None
        self._browser = None
        self._page = None
        self._lock = asyncio.Lock()

    async def play(self, game_url: str) -> None:
        async with self._lock:
            await self._close_browser()
            try:
                from playwright.async_api import async_playwright
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(headless=False)
                self._page = await self._browser.new_page()
                await self._page.goto(game_url, wait_until="networkidle", timeout=20000)
                _log.info("Playwright opened destressing game for: %s", game_url)
            except Exception:
                _log.exception("Playwright game open failed")
                await self._close_browser()

    async def stop(self) -> None:
        async with self._lock:
            await self._close_browser()
            _log.info("Playwright game stopped.")

    async def _close_browser(self) -> None:
        if self._page:
            try:
                await self._page.close()
            except Exception:
                pass
            self._page = None
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None


playwright_game = PlaywrightGamePlayer()
