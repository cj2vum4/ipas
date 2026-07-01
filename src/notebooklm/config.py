"""Central configuration for the NotebookLM extractor.

Values can be overridden with environment variables so the same code runs
against a normal interactive machine and a headless CI/remote environment.
"""
from __future__ import annotations

import os
from pathlib import Path

# --- Paths -----------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("NBLM_DATA_DIR", PROJECT_ROOT / "data"))

# File that stores the logged-in browser session (cookies + localStorage).
# Produced by `login`, consumed by every extraction command.
AUTH_STATE_PATH = Path(
    os.environ.get("NBLM_AUTH_STATE", PROJECT_ROOT / "auth_state.json")
)

# --- NotebookLM URLs -------------------------------------------------------
BASE_URL = os.environ.get("NBLM_BASE_URL", "https://notebooklm.google.com")


def notebook_url(notebook_id: str) -> str:
    return f"{BASE_URL}/notebook/{notebook_id}"


# --- Browser behaviour -----------------------------------------------------
def _autodetect_chromium() -> str | None:
    """Find a pre-installed Chromium under PLAYWRIGHT_BROWSERS_PATH.

    Managed/remote environments often ship a Chromium build whose version does
    not match the pip-installed Playwright driver. Pointing ``executable_path``
    at that binary sidesteps Playwright's version check and avoids a redundant
    download.
    """
    root = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if not root:
        return None
    candidates = sorted(Path(root).glob("chromium-*/chrome-linux/chrome"))
    return str(candidates[-1]) if candidates else None


# Chromium binary shipped with the environment (falls back to Playwright's own
# managed download when neither the env var nor autodetection finds one).
CHROMIUM_EXECUTABLE = os.environ.get("NBLM_CHROMIUM_PATH") or _autodetect_chromium()

# Headless is fine for extraction, but the *first* login must be headed so the
# user can complete the Google sign-in flow (password, 2FA, consent).
HEADLESS_DEFAULT = os.environ.get("NBLM_HEADLESS", "1") not in ("0", "false", "False")

# Generous timeouts: NotebookLM is a heavy Angular app and answers stream in.
NAV_TIMEOUT_MS = int(os.environ.get("NBLM_NAV_TIMEOUT_MS", "60000"))
ACTION_TIMEOUT_MS = int(os.environ.get("NBLM_ACTION_TIMEOUT_MS", "30000"))

# A realistic desktop UA reduces the chance of being served a degraded page.
USER_AGENT = os.environ.get(
    "NBLM_USER_AGENT",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
)
