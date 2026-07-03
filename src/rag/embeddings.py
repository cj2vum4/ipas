"""Deterministic sparse embeddings shared by the builder and web app.

The vectorizer is intentionally small and dependency-free. It is not as
semantic as a transformer model, but it works offline, is reproducible in
Python and JavaScript, and is good enough for first-pass retrieval over exam
notes.
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections import defaultdict

DIMENSIONS = 2048
MAX_FEATURES = 256
TOKENIZER = "unicode-word-cjk-bigram-fnv1a-v1"

_TOKEN_RE = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]+", re.IGNORECASE)
_CJK_RE = re.compile(r"^[\u4e00-\u9fff]+$")


def _normalise(text: str) -> str:
    return unicodedata.normalize("NFKC", text).lower()


def _fnv1a32(text: str) -> int:
    value = 0x811C9DC5
    for byte in text.encode("utf-8"):
        value ^= byte
        value = (value * 0x01000193) & 0xFFFFFFFF
    return value


def _base_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for match in _TOKEN_RE.finditer(_normalise(text)):
        token = match.group(0)
        if _CJK_RE.match(token):
            chars = list(token)
            tokens.extend(chars)
            tokens.extend(chars[i] + chars[i + 1] for i in range(len(chars) - 1))
        else:
            tokens.append(token)
    return tokens


def tokenize(text: str) -> list[str]:
    """Return lexical features for mixed English/Chinese content."""
    tokens = _base_tokens(text)
    features = list(tokens)
    features.extend(f"{tokens[i]}_{tokens[i + 1]}" for i in range(len(tokens) - 1))
    return features


def embed_sparse(
    text: str,
    dimensions: int = DIMENSIONS,
    max_features: int = MAX_FEATURES,
) -> dict[str, list[float] | list[int]]:
    """Hash text into a normalised sparse vector.

    The returned shape is compact JSON:
    ``{"indices": [3, 19], "values": [0.25, -0.5]}``.
    """
    accum: dict[int, float] = defaultdict(float)
    for feature in tokenize(text):
        hashed = _fnv1a32(feature)
        index = hashed % dimensions
        sign = -1.0 if hashed & 0x80000000 else 1.0
        accum[index] += sign

    items = sorted(accum.items(), key=lambda item: (-abs(item[1]), item[0]))
    if max_features > 0:
        items = items[:max_features]
    items = sorted(items)

    norm = math.sqrt(sum(value * value for _, value in items))
    if not norm:
        return {"indices": [], "values": []}

    indices = [index for index, _ in items]
    values = [round(value / norm, 6) for _, value in items]
    return {"indices": indices, "values": values}


def sparse_dot(
    left: dict[str, list[float] | list[int]],
    right: dict[str, list[float] | list[int]],
) -> float:
    """Return cosine similarity for two vectors from :func:`embed_sparse`."""
    left_indices = left.get("indices", [])
    left_values = left.get("values", [])
    right_indices = right.get("indices", [])
    right_values = right.get("values", [])
    right_map = {
        int(index): float(value)
        for index, value in zip(right_indices, right_values, strict=False)
    }
    return sum(
        float(value) * right_map.get(int(index), 0.0)
        for index, value in zip(left_indices, left_values, strict=False)
    )
