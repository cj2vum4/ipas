"""Smoke test for the extraction plumbing against a mock NotebookLM-like DOM.

This does NOT hit the real NotebookLM (that needs a signed-in session). It
loads HTML that mimics the notebook page structure and asserts that the
selector-matching, de-duplication and data shaping behave correctly.

Run with:  python tests/test_extraction.py
"""
from __future__ import annotations

import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from notebooklm import extractor  # noqa: E402
from notebooklm.browser import browser_context  # noqa: E402

MOCK_HTML = """
<html><body>
<div id="notebook-title">研究筆記本 A</div>
<notebook-guide>這是 NotebookLM 產生的總覽摘要。</notebook-guide>
<single-source-container><div>報告.pdf</div><div>2024 年度財報</div></single-source-container>
<single-source-container><div>外部文章</div><div>https://example.com</div></single-source-container>
<note-panel-item><div>重點一</div><div>第一條筆記內容</div></note-panel-item>
<note-panel-item><div>重點二</div><div>第二條筆記內容</div></note-panel-item>
</body></html>
"""


def main() -> int:
    data_url = "data:text/html;charset=utf-8," + urllib.parse.quote(MOCK_HTML)
    with browser_context(headless=True, use_auth=False) as ctx:
        page = ctx.new_page()
        page.goto(data_url)
        page.wait_for_timeout(300)

        title = extractor._first_text(page, extractor._TITLE_SELECTORS)
        summary = extractor._extract_summary(page)
        sources = extractor._extract_sources(page)
        notes = extractor._extract_notes(page)

    assert title == "研究筆記本 A", title
    assert "總覽摘要" in summary, summary
    assert [s.title for s in sources] == ["報告.pdf", "外部文章"], sources
    assert [n.title for n in notes] == ["重點一", "重點二"], notes
    print("OK: extraction plumbing verified against mock DOM")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
