from __future__ import annotations
import asyncio
import logging

_log = logging.getLogger("juno.playwright_music")

PLAY_BUTTON_SELECTOR = '[data-testid="play-pause-button"]'


class PlaywrightMusicPlayer:
    """Opens a Chromium browser via Playwright and clicks the Spotify embed play button.

    Keeps a single browser instance alive so switching genres closes the old one first.
    """

    def __init__(self) -> None:
        self._playwright = None
        self._browser = None
        self._page = None
        self._lock = asyncio.Lock()

    async def play(self, embed_url: str) -> None:
        async with self._lock:
            await self._close_browser()
            try:
                from playwright.async_api import async_playwright
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=False,
                    args=["--autoplay-policy=no-user-gesture-required"],
                )
                self._page = await self._browser.new_page()
                await self._page.goto(embed_url, wait_until="networkidle", timeout=20000)
                await self._page.wait_for_selector(PLAY_BUTTON_SELECTOR, timeout=10000)
                await self._page.locator(PLAY_BUTTON_SELECTOR).first.click()
                _log.info("Playwright clicked Spotify play button for: %s", embed_url)
            except Exception as exc:
                _log.error("Playwright music play failed: %s", exc)
                await self._close_browser()

    async def stop(self) -> None:
        async with self._lock:
            await self._close_browser()
            _log.info("Playwright music stopped.")

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


playwright_music = PlaywrightMusicPlayer()
