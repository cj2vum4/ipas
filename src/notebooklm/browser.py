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
def persistent_context(*, headless: bool) -> Iterator[BrowserContext]:
    """Yield a BrowserContext backed by a persistent, real-browser profile.

    This is the reliable path for NotebookLM: it drives a genuine installed
    browser (Edge/Chrome via ``BROWSER_CHANNEL``) with a persistent profile
    directory, so a one-time sign-in survives across runs and Google is far
    less likely to block login as "insecure".
    """
    config.USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        kwargs: dict = {
            "user_data_dir": str(config.USER_DATA_DIR),
            "headless": headless,
            "user_agent": config.USER_AGENT,
            # Hide the navigator.webdriver flag that trips Google's automation
            # detection.
            "args": ["--disable-blink-features=AutomationControlled"],
        }
        if config.BROWSER_CHANNEL:
            # Drive the user's real Edge/Chrome install.
            kwargs["channel"] = config.BROWSER_CHANNEL
        elif config.CHROMIUM_EXECUTABLE:
            kwargs["executable_path"] = config.CHROMIUM_EXECUTABLE

        context = pw.chromium.launch_persistent_context(**kwargs)
        context.set_default_navigation_timeout(config.NAV_TIMEOUT_MS)
        context.set_default_timeout(config.ACTION_TIMEOUT_MS)
        try:
            yield context
        finally:
            context.close()


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
