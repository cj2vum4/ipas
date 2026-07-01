"""Typed data structures for extracted NotebookLM content."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Source:
    """A single source (uploaded doc, pasted text, URL, ...) inside a notebook."""

    title: str
    kind: str = "unknown"  # e.g. "pdf", "google_doc", "url", "text"
    preview: str = ""


@dataclass
class Note:
    """A saved note / response captured inside a notebook."""

    title: str = ""
    content: str = ""


@dataclass
class Notebook:
    """A NotebookLM notebook and everything we managed to pull out of it."""

    id: str
    title: str = ""
    url: str = ""
    summary: str = ""
    sources: list[Source] = field(default_factory=list)
    notes: list[Note] = field(default_factory=list)
    extracted_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NotebookRef:
    """Lightweight reference from the notebook-list page."""

    id: str
    title: str = ""
    url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
