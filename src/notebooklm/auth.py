"""Interactive login: open a real browser, let the user sign in, save session.

NotebookLM has no public API, so we authenticate the way a human does — through
the Google sign-in flow — and persist the resulting cookies/localStorage to
``auth_state.json``. Every later extraction reuses that state headlessly.
"""
from __future__ import annotations

from playwright.sync_api import sync_playwright

from . import config


def login(timeout_seconds: int = 300) -> None:
    """Open a headed browser and wait until the user has reached NotebookLM.

    We consider the login complete once the page URL is on the NotebookLM app
    (not accounts.google.com) and the notebook list has rendered. The user
    drives the actual Google authentication (password, 2FA, consent).
    """
    if config.HEADLESS_DEFAULT:
        print(
            "NOTE: login needs a visible browser. If you are on a headless "
            "server, run with NBLM_HEADLESS=0 and an X display / VNC, or copy "
            "an auth_state.json produced on a desktop machine.\n"
        )

    launch_kwargs: dict = {"headless": False}
    if config.CHROMIUM_EXECUTABLE:
        launch_kwargs["executable_path"] = config.CHROMIUM_EXECUTABLE

    with sync_playwright() as pw:
        browser = pw.chromium.launch(**launch_kwargs)
        context = browser.new_context(user_agent=config.USER_AGENT)
        page = context.new_page()
        page.set_default_navigation_timeout(config.NAV_TIMEOUT_MS)

        print(f"Opening {config.BASE_URL} — please sign in with your Google account...")
        page.goto(config.BASE_URL)

        print(
            f"Waiting up to {timeout_seconds}s for you to finish signing in.\n"
            "When you can see your notebooks, come back here — it saves "
            "automatically."
        )
        try:
            # Poll until we are on the NotebookLM origin and signed in.
            page.wait_for_url(
                lambda url: "notebooklm.google.com" in url
                and "accounts.google.com" not in url,
                timeout=timeout_seconds * 1000,
            )
            # Give the SPA a moment to hydrate the session in localStorage.
            page.wait_for_timeout(3000)
        except Exception:
            print(
                "Timed out waiting for sign-in. Saving whatever state exists — "
                "if extraction fails, re-run `login` and complete sign-in fully."
            )

        config.AUTH_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        context.storage_state(path=str(config.AUTH_STATE_PATH))
        print(f"\nSaved session to {config.AUTH_STATE_PATH}")
        context.close()
        browser.close()
