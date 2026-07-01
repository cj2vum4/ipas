"""Interactive login using a real browser + persistent profile.

NotebookLM has no public API, so we authenticate the way a human does. To avoid
Google's "this browser or app may not be secure" block, we drive a *genuine*
installed browser (Edge/Chrome via ``BROWSER_CHANNEL``) with a persistent
profile directory. You sign in once; the session lives in the profile and every
later extraction reuses it headlessly.
"""
from __future__ import annotations

from . import config
from .browser import persistent_context


def login() -> None:
    """Open a real browser, let the user sign in, persist the profile.

    We do NOT try to guess when sign-in finished from the URL (that was flaky
    and saved empty sessions). Instead you drive the Google flow in the window
    and press ENTER here once you can see your notebooks.
    """
    channel = config.BROWSER_CHANNEL or "bundled Chromium"
    print(
        f"Launching {channel} with a persistent profile at:\n"
        f"  {config.USER_DATA_DIR}\n"
    )
    print(
        "IMPORTANT: sign in *inside the window that just opened* — not in your\n"
        "normal browser. A separate login elsewhere will NOT be picked up.\n"
    )

    with persistent_context(headless=False) as context:
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(config.BASE_URL)

        print(f"Opened {config.BASE_URL}. Complete the Google sign-in there.")
        try:
            input(
                "\n>>> When you can SEE YOUR NOTEBOOKS, come back here and press "
                "ENTER to save... "
            )
        except (EOFError, KeyboardInterrupt):
            print("\nAborted; nothing new saved.")
            return

        # Persistent context flushes the profile to disk on close.
        print(f"\nSaved session to profile: {config.USER_DATA_DIR}")
        print("You can now run:  python main.py list")
