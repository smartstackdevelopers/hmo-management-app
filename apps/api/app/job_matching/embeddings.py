"""Deterministic local embeddings for job/tenant text (no separate vector DB).

Uses a hashing trick over tokens so rankings stay stable without an external
embedding model. When job content is unchanged (same content_hash), embeddings
are not regenerated.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Iterable

from app.job_matching.constants import EMBEDDING_DIM

_TOKEN_RE = re.compile(r"[a-z0-9+]{2,}")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall((text or "").lower())


def embed_text(text: str, *, dim: int = EMBEDDING_DIM) -> list[float]:
    vec = [0.0] * dim
    tokens = tokenize(text)
    if not tokens:
        return vec
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "big") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vec[idx] += sign
    # L2 normalise
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine_similarity(a: Iterable[float], b: Iterable[float]) -> float:
    a_list = list(a)
    b_list = list(b)
    if not a_list or not b_list or len(a_list) != len(b_list):
        return 0.0
    return float(sum(x * y for x, y in zip(a_list, b_list, strict=True)))


def content_hash(parts: Iterable[str]) -> str:
    blob = "\n".join(p or "" for p in parts)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
