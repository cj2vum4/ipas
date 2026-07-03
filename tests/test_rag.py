"""Smoke tests for the local RAG index primitives.

Run with:  python tests/test_rag.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag.builder import build_index, chunk_text  # noqa: E402
from rag.embeddings import embed_sparse, sparse_dot  # noqa: E402


def main() -> int:
    similar = sparse_dot(embed_sparse("機器學習 模型 驗證"), embed_sparse("模型驗證與機器學習"))
    unrelated = sparse_dot(embed_sparse("機器學習 模型 驗證"), embed_sparse("供應鏈倉儲盤點"))
    assert similar > unrelated, (similar, unrelated)

    chunks = chunk_text("A" * 500 + "\n\n" + "B" * 500, 600, 80)
    assert len(chunks) == 2, chunks

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        sample = root / "sample.txt"
        sample.write_text("人工智慧導入需要目標、資料、模型與治理。", encoding="utf-8")
        out = root / "rag_index.json"
        stats = build_index([sample], output_path=out, chunk_size=300, chunk_overlap=40)
        payload = json.loads(out.read_text(encoding="utf-8"))

    assert stats.sources == 1, stats
    assert stats.chunks == 1, stats
    assert payload["chunks"][0]["vector"]["indices"], payload
    print("OK: RAG primitives verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

