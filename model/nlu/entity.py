"""Stage 5 — entity recognition (typed spans + semantic type scoring)."""
from __future__ import annotations

import re
from typing import Dict, List, Sequence

import numpy as np

from .embedding import EmbeddingEngine, embedding_engine
from .types import Entity, EntityType, Token


# Seed banks — matched via embedding similarity to surface forms, not if "python" in text alone
_BANK: Dict[EntityType, List[str]] = {
    EntityType.LANGUAGE: [
        "python", "javascript", "typescript", "java", "go", "rust", "c++", "c#",
        "ruby", "php", "kotlin", "swift", "sql", "bash", "html", "css",
    ],
    EntityType.PRODUCT: [
        "react", "vue", "angular", "django", "flask", "fastapi", "docker", "kubernetes",
        "redis", "postgres", "postgresql", "mongodb", "nginx", "nextjs", "vite",
        "supabase", "firebase", "tailwind", "prisma",
    ],
    EntityType.COMPANY: [
        "google", "microsoft", "amazon", "meta", "openai", "anthropic", "github",
        "gitlab", "vercel", "render", "cloudflare", "apple", "netflix",
    ],
    EntityType.GAME: [
        "minecraft", "valorant", "lol", "league of legends", "csgo", "fortnite",
        "gta", "xox", "hangman", "sudoku",
    ],
    EntityType.LOCATION: [
        "istanbul", "ankara", "izmir", "turkiye", "turkey", "london", "paris",
        "new york", "berlin", "tokyo",
    ],
    EntityType.PERSON: [
        "demir", "ali", "ayse", "mehmet", "elon musk", "guido van rossum",
    ],
}


_DATE_RE = re.compile(
    r"\b(\d{1,2}[./]\d{1,2}[./]\d{2,4}|bugun|yarin|dun|today|tomorrow|yesterday)\b",
    re.I,
)
_TIME_RE = re.compile(r"\b([01]?\d|2[0-3])[:.][0-5]\d\b|\b(saat kac|what time)\b", re.I)
_FILE_RE = re.compile(r"\b[\w.-]+\.(py|js|ts|tsx|json|yaml|yml|md|txt|csv|html|css)\b", re.I)
_NUM_RE = re.compile(r"\b\d+(?:[.,]\d+)?\b")
_VAR_RE = re.compile(r"\b[a-z_][a-z0-9_]{2,}\b", re.I)


class EntityEngine:
    def __init__(self, emb: EmbeddingEngine | None = None) -> None:
        self.emb = emb or embedding_engine
        self._bank_vecs: Dict[EntityType, List[tuple[str, np.ndarray]]] = {}
        for etype, names in _BANK.items():
            self._bank_vecs[etype] = [(n, self.emb.encode(n)) for n in names]

    def extract(self, text: str, tokens: Sequence[Token] | None = None) -> List[Entity]:
        text = text or ""
        found: list[Entity] = []

        def add(span: str, etype: EntityType, start: int, end: int, score: float, norm: str = "") -> None:
            if not span.strip():
                return
            found.append(
                Entity(
                    text=span,
                    type=etype,
                    start=start,
                    end=end,
                    score=score,
                    normalized=norm or span,
                )
            )

        for m in _DATE_RE.finditer(text):
            add(m.group(0), EntityType.DATE, m.start(), m.end(), 0.95)
        for m in _TIME_RE.finditer(text):
            add(m.group(0), EntityType.TIME, m.start(), m.end(), 0.9)
        for m in _FILE_RE.finditer(text):
            add(m.group(0), EntityType.FILE, m.start(), m.end(), 0.95)
        for m in _NUM_RE.finditer(text):
            add(m.group(0), EntityType.NUMBER, m.start(), m.end(), 0.99)

        # Sliding window phrases (1-3 tokens) scored against banks
        words = list(tokens) if tokens else []
        if not words:
            words = [
                Token(text=w, lemma=w.lower(), index=i)
                for i, w in enumerate(re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9_+#.-]+", text))
            ]
        content = [t for t in words if not t.is_punct]
        for n in (3, 2, 1):
            for i in range(0, max(0, len(content) - n + 1)):
                chunk_toks = content[i : i + n]
                phrase = " ".join(t.text for t in chunk_toks)
                if len(phrase) < 2:
                    continue
                vec = self.emb.encode(phrase)
                best_type, best_score, best_norm = None, 0.0, ""
                for etype, entries in self._bank_vecs.items():
                    for name, nv in entries:
                        sc = self.emb.cosine(vec, nv)
                        if sc > best_score:
                            best_type, best_score, best_norm = etype, sc, name
                if best_type and best_score >= 0.72:
                    # approximate offsets
                    start = text.lower().find(phrase.lower())
                    if start < 0:
                        start = 0
                    add(phrase, best_type, start, start + len(phrase), best_score, best_norm)

        # Deduplicate overlapping by higher score
        found.sort(key=lambda e: (-e.score, -(e.end - e.start)))
        kept: list[Entity] = []
        occupied: list[tuple[int, int]] = []
        for e in found:
            if any(not (e.end <= a or e.start >= b) for a, b in occupied):
                continue
            kept.append(e)
            occupied.append((e.start, e.end))
        return kept


entity_engine = EntityEngine()
