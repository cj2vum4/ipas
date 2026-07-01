"""Extract notebooks and their contents from NotebookLM via a signed-in browser.

Important: NotebookLM is a Google Angular SPA with no public API and no stable
DOM contract. Class names and element tags change without notice. To stay
resilient we:

  * try several candidate selectors for each piece of data,
  * fall back to structural/text heuristics when selectors miss,
  * and expose `debug_dump` so you can refresh selectors when Google ships a
    redesign.

Treat the selector lists below as the single place to update when extraction
starts returning empty results.
"""
from __future__ import annotations

import re
from typing import Optional

from playwright.sync_api import Page, TimeoutError as PWTimeout

from . import config
from .browser import persistent_context
from .models import Note, Notebook, NotebookRef, Source

# --- Candidate selectors (ordered by likelihood) ---------------------------
# Update these when NotebookLM changes its markup.
_NOTEBOOK_CARD_SELECTORS = [
    "a[href*='/notebook/']",
    "project-button a",
    "[data-testid='notebook-card']",
]
_SOURCE_ITEM_SELECTORS = [
    "single-source-container",
    "[data-testid='source-item']",
    ".source-item",
    "source-picker .source",
]
_NOTE_ITEM_SELECTORS = [
    "note-panel-item",
    "[data-testid='note-card']",
    ".note-card",
    "labs-tailwind-note",
]
_TITLE_SELECTORS = [
    "#notebook-title",
    "[data-testid='notebook-title']",
    "input.title-input",
    "h1",
]

_NOTEBOOK_ID_RE = re.compile(r"/notebook/([0-9a-f-]{16,})", re.IGNORECASE)


def _first_text(page_or_el, selectors: list[str]) -> str:
    """Return trimmed text of the first selector that matches, else ''."""
    for sel in selectors:
        try:
            loc = page_or_el.locator(sel).first
            if loc.count() > 0:
                txt = (loc.inner_text(timeout=2000) or "").strip()
                if txt:
                    return txt
        except PWTimeout:
            continue
        except Exception:
            continue
    return ""


def _is_signed_in(page: Page) -> bool:
    url = page.url
    if "accounts.google.com" in url or "ServiceLogin" in url:
        return False
    return "notebooklm.google.com" in url


def _require_auth() -> None:
    # The persistent profile holds the login; treat an empty/missing dir as
    # "not signed in yet".
    if not config.USER_DATA_DIR.exists() or not any(config.USER_DATA_DIR.iterdir()):
        raise RuntimeError(
            f"No signed-in profile at {config.USER_DATA_DIR}. Run `login` first."
        )


# --- Public API ------------------------------------------------------------
def list_notebooks(headless: Optional[bool] = None) -> list[NotebookRef]:
    """Return the notebooks visible on the NotebookLM home page."""
    headless = config.HEADLESS_DEFAULT if headless is None else headless
    _require_auth()
    with persistent_context(headless=headless) as context:
        page = context.new_page()
        page.goto(config.BASE_URL, wait_until="domcontentloaded")
        _settle(page)

        if not _is_signed_in(page):
            raise RuntimeError(
                "Session is not signed in (redirected to Google login). "
                "Run `login` again and sign in fully before pressing ENTER."
            )

        refs: dict[str, NotebookRef] = {}
        for sel in _NOTEBOOK_CARD_SELECTORS:
            links = page.locator(sel)
            for i in range(links.count()):
                el = links.nth(i)
                try:
                    href = el.get_attribute("href") or ""
                except Exception:
                    continue
                m = _NOTEBOOK_ID_RE.search(href)
                if not m:
                    continue
                nb_id = m.group(1)
                title = ""
                try:
                    title = (el.inner_text(timeout=1500) or "").strip()
                except Exception:
                    pass
                refs.setdefault(
                    nb_id,
                    NotebookRef(id=nb_id, title=title, url=config.notebook_url(nb_id)),
                )
            if refs:
                break
        return list(refs.values())


def extract_notebook(
    notebook_id: str, headless: Optional[bool] = None
) -> Notebook:
    """Open a single notebook and pull out title, summary, sources and notes."""
    headless = config.HEADLESS_DEFAULT if headless is None else headless
    _require_auth()
    with persistent_context(headless=headless) as context:
        page = context.new_page()
        page.goto(config.notebook_url(notebook_id), wait_until="domcontentloaded")
        _settle(page)

        if not _is_signed_in(page):
            raise RuntimeError(
                "Session is not signed in. Run `login` again to refresh auth."
            )

        notebook = Notebook(
            id=notebook_id,
            url=config.notebook_url(notebook_id),
            title=_first_text(page, _TITLE_SELECTORS),
            sources=_extract_sources(page),
            notes=_extract_notes(page),
        )
        notebook.summary = _extract_summary(page)
        return notebook


def debug_dump(notebook_id: Optional[str], headless: Optional[bool] = None) -> str:
    """Return the rendered page text — use it to rediscover selectors."""
    headless = config.HEADLESS_DEFAULT if headless is None else headless
    target = config.notebook_url(notebook_id) if notebook_id else config.BASE_URL
    with persistent_context(headless=headless) as context:
        page = context.new_page()
        page.goto(target, wait_until="domcontentloaded")
        _settle(page)
        return page.locator("body").inner_text(timeout=5000)


# --- Internal extraction helpers ------------------------------------------
def _settle(page: Page) -> None:
    """Wait for the SPA to stop loading, tolerating never-idle network."""
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except PWTimeout:
        pass
    page.wait_for_timeout(1500)


def _extract_sources(page: Page) -> list[Source]:
    sources: list[Source] = []
    seen: set[str] = set()
    for sel in _SOURCE_ITEM_SELECTORS:
        items = page.locator(sel)
        count = items.count()
        if count == 0:
            continue
        for i in range(count):
            el = items.nth(i)
            try:
                text = (el.inner_text(timeout=1500) or "").strip()
            except Exception:
                continue
            if not text or text in seen:
                continue
            seen.add(text)
            title = text.splitlines()[0][:200]
            sources.append(Source(title=title, preview=text[:500]))
        if sources:
            break
    return sources


def _extract_notes(page: Page) -> list[Note]:
    notes: list[Note] = []
    seen: set[str] = set()
    for sel in _NOTE_ITEM_SELECTORS:
        items = page.locator(sel)
        count = items.count()
        if count == 0:
            continue
        for i in range(count):
            el = items.nth(i)
            try:
                text = (el.inner_text(timeout=1500) or "").strip()
            except Exception:
                continue
            if not text or text in seen:
                continue
            seen.add(text)
            lines = text.splitlines()
            title = lines[0][:200] if lines else ""
            notes.append(Note(title=title, content=text))
        if notes:
            break
    return notes


def _extract_summary(page: Page) -> str:
    """NotebookLM shows a generated overview/summary; grab it if present."""
    for sel in [
        "[data-testid='notebook-summary']",
        "notebook-guide",
        ".notebook-overview",
    ]:
        txt = _first_text(page, [sel])
        if txt:
            return txt
    return ""
