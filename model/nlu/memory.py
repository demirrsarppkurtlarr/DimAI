"""Stage 6 — conversation memory + coreference resolution (RAG-style)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from .embedding import EmbeddingEngine, embedding_engine
from .types import Entity, EntityType, MemoryHit


_REF_RE = re.compile(
    r"\b("
    r"that|it|this|him|her|them|those|these|same(?:\s+one)?|again|continue|"
    r"onu|bunu|sunu|ona|buna|o|bu|su|ayni(?:si|sindan|sini)?|"
    r"tekrar|devam(?:\s+et)?|onun|bunun|ondan|bundan|"
    r"bahsettigin|dedigin|anlattigin"
    r")\b",
    re.I,
)


@dataclass
class MemoryStore:
    """Session + durable conversation memory."""

    turns: list[dict[str, Any]] = field(default_factory=list)
    embeddings: list[np.ndarray] = field(default_factory=list)
    topic: str = ""
    preferences: dict[str, str] = field(default_factory=dict)
    last_code: str = ""
    last_lang: str = ""
    unfinished_tasks: list[str] = field(default_factory=list)
    entities: list[Entity] = field(default_factory=list)
    project: str = ""


class MemoryEngine:
    def __init__(self, emb: EmbeddingEngine | None = None) -> None:
        self.emb = emb or embedding_engine
        self.store = MemoryStore()

    def ingest_history(self, history: Sequence[dict[str, Any]]) -> None:
        """Rebuild lightweight memory from client-provided history."""
        self.store.turns = []
        self.store.embeddings = []
        self.store.entities = []
        self.store.topic = ""
        self.store.last_code = ""
        self.store.last_lang = ""
        # Keep preferences across turns in-process, but topic/code come from history
        for h in history[-24:]:
            role = str(h.get("role") or "")
            content = str(h.get("content") or "").strip()
            if not content:
                continue
            self.store.turns.append({"role": role, "content": content})
            self.store.embeddings.append(self.emb.encode(content))
            if role in ("ai", "assistant") and "```" in content:
                m = re.search(r"```(?:\w+)?\n(.*?)```", content, re.S)
                if m:
                    self.store.last_code = m.group(1).strip()
            # Harvest likely topic entities from user turns (semantic bank score)
            if role == "user":
                try:
                    from .entity import entity_engine

                    ents = entity_engine.extract(content)
                    self.store.entities.extend(ents)
                except Exception:
                    pass
        if self.store.turns:
            for t in reversed(self.store.turns):
                if t["role"] == "user" and len(t["content"].split()) >= 2:
                    self.store.topic = t["content"][:160]
                    break

    def remember_turn(
        self,
        role: str,
        content: str,
        *,
        code: str = "",
        lang: str = "",
        entities: Optional[List[Entity]] = None,
    ) -> None:
        self.store.turns.append({"role": role, "content": content})
        self.store.embeddings.append(self.emb.encode(content))
        if code:
            self.store.last_code = code
            self.store.last_lang = lang
        if entities:
            self.store.entities.extend(entities[-12:])
        # Preferences: "adım X"
        m = re.search(r"(?:benim )?(?:adim|ismim)\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)", content, re.I)
        if m:
            self.store.preferences["name"] = m.group(1).capitalize()

    def retrieve(self, query: str, query_vec: np.ndarray | None = None, top_k: int = 6) -> List[MemoryHit]:
        hits: list[MemoryHit] = []
        qv = query_vec if query_vec is not None else self.emb.encode(query)
        for i, (turn, vec) in enumerate(zip(self.store.turns, self.store.embeddings)):
            score = self.emb.cosine(qv, vec)
            # Recency bonus
            recency = 0.05 * (i + 1) / max(len(self.store.turns), 1)
            hits.append(
                MemoryHit(
                    role=turn["role"],
                    content=turn["content"],
                    score=score + recency,
                    kind="turn",
                )
            )
        hits.sort(key=lambda h: -h.score)
        hits = [h for h in hits if h.score >= 0.15][:top_k]

        if self.store.topic:
            hits.append(
                MemoryHit(role="system", content=self.store.topic, score=0.9, kind="topic")
            )
        if self.store.last_code:
            hits.append(
                MemoryHit(
                    role="system",
                    content=self.store.last_code[:500],
                    score=0.85,
                    kind="code",
                    meta={"lang": self.store.last_lang},
                )
            )
        if self.store.preferences:
            pref = ", ".join(f"{k}={v}" for k, v in self.store.preferences.items())
            hits.append(MemoryHit(role="system", content=pref, score=0.8, kind="preference"))
        for task in self.store.unfinished_tasks[-3:]:
            hits.append(MemoryHit(role="system", content=task, score=0.7, kind="task"))
        return hits

    def resolve_references(
        self,
        text: str,
        entities: Sequence[Entity],
    ) -> tuple[str, dict[str, str], list[Entity]]:
        """Replace/annotate pronouns using recent entities & topic."""
        resolved: dict[str, str] = {}
        enriched = list(entities)

        def fold(s: str) -> str:
            s = (s or "").lower().replace("İ", "i").replace("I", "i").replace("ı", "i")
            return s.translate(str.maketrans("çğıöşü", "cgiosu"))

        folded = fold(text)
        if not _REF_RE.search(folded):
            return text, resolved, enriched

        # Candidate antecedents: recent typed entities + topic noun phrase
        candidates: list[str] = []
        for e in reversed(self.store.entities[-20:]):
            if e.type in {
                EntityType.PRODUCT,
                EntityType.LANGUAGE,
                EntityType.PROJECT,
                EntityType.TOPIC,
                EntityType.PERSON,
                EntityType.GAME,
                EntityType.COMPANY,
            }:
                candidates.append(e.normalized or e.text)
        if self.store.topic:
            parts = re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9_+#.-]+", self.store.topic)
            stop = {"nedir", "nasil", "yaz", "what", "is", "the", "a", "bir", "ne", "hakkinda"}
            parts = [p for p in parts if fold(p) not in stop]
            if parts:
                candidates.append(" ".join(parts[:3]))

        seen = set()
        uniq = []
        for c in candidates:
            k = fold(c)
            if k not in seen:
                seen.add(k)
                uniq.append(c)

        if not uniq:
            return text, resolved, enriched

        antecedent = uniq[0]
        for c in uniq:
            cl = fold(c)
            if cl in {"docker", "react", "python", "flask", "redis", "kubernetes", "nginx"}:
                antecedent = c
                break

        for m in _REF_RE.finditer(folded):
            ref = m.group(0)
            resolved[ref] = antecedent

        expanded = text
        if resolved:
            hint = antecedent
            expanded = f"{text} [ref:{hint}]"
            enriched.append(
                Entity(
                    text=hint,
                    type=EntityType.TOPIC,
                    start=0,
                    end=0,
                    score=0.8,
                    normalized=hint,
                    resolved_from="coref",
                )
            )
        return expanded, resolved, enriched


memory_engine = MemoryEngine()
