"""Build a browser-readable RAG index from local documents."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha1
from pathlib import Path
from typing import Any

from notebooklm import config

from .embeddings import DIMENSIONS, MAX_FEATURES, TOKENIZER, embed_sparse
from .loaders import LoadIssue, discover_files, load_document

DEFAULT_CHUNK_SIZE = 1400
DEFAULT_CHUNK_OVERLAP = 180
DEFAULT_OUTPUT = config.PROJECT_ROOT / "docs" / "rag_index.json"


@dataclass
class BuildStats:
    output_path: Path
    files_seen: int = 0
    sources: int = 0
    chunks: int = 0
    skipped: list[LoadIssue] = field(default_factory=list)


def default_source_paths() -> list[Path]:
    paths = [config.PROJECT_ROOT / "iPAS教材", config.DATA_DIR]
    return [path for path in paths if path.exists()]


def build_index(
    source_paths: list[Path],
    output_path: Path = DEFAULT_OUTPUT,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    max_chunks: int = 0,
) -> BuildStats:
    if chunk_size < 200:
        raise ValueError("chunk_size must be at least 200 characters")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be >= 0 and smaller than chunk_size")

    files = discover_files(source_paths)
    stats = BuildStats(output_path=output_path, files_seen=len(files))
    sources: list[dict[str, Any]] = []
    chunks: list[dict[str, Any]] = []

    for path in files:
        try:
            document = load_document(path, config.PROJECT_ROOT)
        except Exception as exc:
            stats.skipped.append(LoadIssue(path=_display_path(path), reason=str(exc)))
            continue

        source_record = {
            "id": document.source_id,
            "path": document.path,
            "title": document.title,
            "kind": document.kind,
            "chars": len(document.text),
        }
        sources.append(source_record)

        for chunk_index, text in enumerate(chunk_text(document.text, chunk_size, chunk_overlap)):
            chunk_id = _chunk_id(document.source_id, chunk_index, text)
            chunks.append(
                {
                    "id": chunk_id,
                    "source_id": document.source_id,
                    "source_path": document.path,
                    "source_title": document.title,
                    "chunk_index": chunk_index,
                    "text": text,
                    "vector": embed_sparse(text),
                }
            )
            if max_chunks and len(chunks) >= max_chunks:
                break
        if max_chunks and len(chunks) >= max_chunks:
            break

    payload = {
        "schema": "ipas-rag-index-v1",
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "embedding": {
            "provider": "local-hash",
            "dimensions": DIMENSIONS,
            "max_features": MAX_FEATURES,
            "tokenizer": TOKENIZER,
        },
        "sources": sources,
        "chunks": chunks,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    stats.sources = len(sources)
    stats.chunks = len(chunks)
    return stats


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    text = _normalise_text(text)
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        hard_end = min(len(text), start + chunk_size)
        end = _find_breakpoint(text, start, hard_end)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def _normalise_text(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _find_breakpoint(text: str, start: int, hard_end: int) -> int:
    if hard_end >= len(text):
        return len(text)

    minimum = start + int((hard_end - start) * 0.55)
    window = text[minimum:hard_end]
    for pattern in ("\n\n", "\n", "。", "！", "？", ". ", "! ", "? ", "；", "; "):
        idx = window.rfind(pattern)
        if idx >= 0:
            return minimum + idx + len(pattern)
    return hard_end


def _chunk_id(source_id: str, chunk_index: int, text: str) -> str:
    digest = sha1(f"{source_id}:{chunk_index}:{text[:120]}".encode("utf-8")).hexdigest()
    return "chk_" + digest[:16]


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(config.PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)
