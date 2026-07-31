"""Stage 3 — semantic embedding engine (local, swappable).

Uses hashed character/word n-grams projected into a fixed vector space.
This is intentionally free of keyword if/else for meaning comparison.
Replace EmbeddingEngine.encode with OpenAI/local LLM embeddings later.
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import Iterable, List, Optional, Sequence

import numpy as np


def _fold(text: str) -> str:
    text = (text or "").lower().replace("İ", "i").replace("I", "i").replace("ı", "i")
    table = str.maketrans("çğıöşü", "cgiosu")
    return text.translate(table)


class EmbeddingEngine:
    """Deterministic local sentence encoder."""

    def __init__(self, dim: int = 384, seed: int = 7) -> None:
        self.dim = dim
        self.seed = seed

    def _bucket(self, feature: str) -> int:
        h = hashlib.blake2b(
            f"{self.seed}:{feature}".encode("utf-8"),
            digest_size=8,
        ).digest()
        return int.from_bytes(h, "little") % self.dim

    def _features(self, text: str) -> List[str]:
        t = _fold(text)
        t = re.sub(r"\s+", " ", t).strip()
        feats: list[str] = []
        # char n-grams (captures morphology / typos)
        padded = f"^{t}$"
        for n in (2, 3, 4):
            for i in range(max(0, len(padded) - n + 1)):
                feats.append(f"c{n}:{padded[i:i+n]}")
        # word unigrams + bigrams
        words = re.findall(r"[a-z0-9_]+", t)
        for w in words:
            feats.append(f"w:{w}")
        for a, b in zip(words, words[1:]):
            feats.append(f"b:{a}_{b}")
        # length / question cues as soft structure (not keyword intent)
        feats.append(f"len:{min(len(words), 40)}")
        if "?" in text:
            feats.append("struct:qmark")
        return feats

    def encode(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        feats = self._features(text)
        if not feats:
            return vec
        for f in feats:
            i = self._bucket(f)
            # signed hash trick
            sign = 1.0 if (self._bucket("s:" + f) % 2 == 0) else -1.0
            vec[i] += sign
        # TF log scale
        vec = np.sign(vec) * np.log1p(np.abs(vec))
        n = float(np.linalg.norm(vec))
        if n > 1e-8:
            vec /= n
        return vec

    def encode_many(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        return np.stack([self.encode(t) for t in texts], axis=0)

    @staticmethod
    def cosine(a: np.ndarray, b: np.ndarray) -> float:
        if a is None or b is None:
            return 0.0
        na = float(np.linalg.norm(a))
        nb = float(np.linalg.norm(b))
        if na < 1e-8 or nb < 1e-8:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    def most_similar(
        self,
        query: np.ndarray,
        corpus: Sequence[np.ndarray],
        top_k: int = 5,
    ) -> List[tuple[int, float]]:
        scored = [(i, self.cosine(query, v)) for i, v in enumerate(corpus)]
        scored.sort(key=lambda x: -x[1])
        return scored[:top_k]


# singleton default
embedding_engine = EmbeddingEngine()
