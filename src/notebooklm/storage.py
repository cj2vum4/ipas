"""Persist extracted notebooks to JSON on disk."""
from __future__ import annotations

import json
from pathlib import Path

from . import config
from .models import Notebook


def _safe_name(text: str, fallback: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in "-_ " else "_" for c in text).strip()
    cleaned = cleaned.replace(" ", "_")
    return cleaned[:80] or fallback


def save_notebook(notebook: Notebook) -> Path:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    name = _safe_name(notebook.title, notebook.id)
    out = config.DATA_DIR / f"{name}__{notebook.id}.json"
    out.write_text(
        json.dumps(notebook.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out


def save_index(records: list[dict]) -> Path:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = config.DATA_DIR / "notebooks_index.json"
    out.write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return out
