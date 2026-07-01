"""Playwright browser lifecycle helpers shared by auth and extraction."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from playwright.sync_api import Browser, BrowserContext, sync_playwright

from . import config


def _launch_kwargs(headless: bool) -> dict:
    kwargs: dict = {"headless": headless}
    if config.CHROMIUM_EXECUTABLE:
        kwargs["executable_path"] = config.CHROMIUM_EXECUTABLE
    return kwargs


@contextmanager
def browser_context(
    *,
    headless: bool,
    use_auth: bool = True,
) -> Iterator[BrowserContext]:
    """Yield a configured BrowserContext, tearing everything down on exit.

    When ``use_auth`` is true the saved storage state (cookies + localStorage)
    is loaded so NotebookLM treats us as an already signed-in user.
    """
    with sync_playwright() as pw:
        browser: Browser = pw.chromium.launch(**_launch_kwargs(headless))
        context_kwargs: dict = {"user_agent": config.USER_AGENT}
        if use_auth and config.AUTH_STATE_PATH.exists():
            context_kwargs["storage_state"] = str(config.AUTH_STATE_PATH)

        context = browser.new_context(**context_kwargs)
        context.set_default_navigation_timeout(config.NAV_TIMEOUT_MS)
        context.set_default_timeout(config.ACTION_TIMEOUT_MS)
        try:
            yield context
        finally:
            context.close()
            browser.close()
