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
    r"that|it|this|him|her|them|those|these|same(?:\s+(?:one|project|thing))?|again|continue|"
    r"previous(?:\s+one)?|the\s+same|"
    r"onu|bunu|sunu|ona|buna|o|bu|su|ayni(?:si|sindan|sini|proje)?|"
    r"tekrar|devam(?:\s+et)?|onun|bunun|ondan|bundan|"
    r"bahsettigin|dedigin|anlattigin|"
    r"onceki(?:\s+(?:biri|proje|kod))?|ustteki|yukaridaki"
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
    recent_actions: list[str] = field(default_factory=list)
    personality_notes: list[str] = field(default_factory=list)


class MemoryEngine:
    def __init__(self, emb: EmbeddingEngine | None = None) -> None:
        self.emb = emb or embedding_engine
        self.store = MemoryStore()

    def ingest_history(self, history: Sequence[dict[str, Any]]) -> None:
        """Rebuild lightweight memory from client-provided history."""
        prefs = dict(self.store.preferences)
        project = self.store.project
        actions = list(self.store.recent_actions[-8:])
        persona = list(self.store.personality_notes[-6:])

        self.store.turns = []
        self.store.embeddings = []
        self.store.entities = []
        self.store.topic = ""
        self.store.last_code = ""
        self.store.last_lang = ""
        self.store.preferences = prefs
        self.store.project = project
        self.store.recent_actions = actions
        self.store.personality_notes = persona

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
            if role == "user":
                try:
                    from .entity import entity_engine

                    ents = entity_engine.extract(content)
                    self.store.entities.extend(ents)
                except Exception:
                    pass
                # Infer project label from coding asks
                folded = content.lower().replace("ı", "i")
                if any(k in folded for k in ("yaz", "write", "olustur", "proje", "project")):
                    if len(content) < 120:
                        self.store.project = content[:120]
        if self.store.turns:
            for t in reversed(self.store.turns):
                if t["role"] == "user" and len(t["content"].split()) >= 2:
                    self.store.topic = t["content"][:160]
                    break
        # Clean topical label once when ingesting history (do not mutate during coref)
        if self.store.topic:
            parts = re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9_+#.-]+", self.store.topic)
            stop = {
                "nedir", "nasil", "yaz", "what", "is", "the", "a", "bir", "ne",
                "hakkinda", "kod", "code", "write", "please", "lutfen",
                "anlat", "acikla", "neden", "how", "why", "about", "daha", "devam",
            }
            parts = [
                p
                for p in parts
                if p.lower().replace("ı", "i").translate(str.maketrans("çğıöşü", "cgiosu"))
                not in stop
            ]
            if parts:
                self.store.topic = " ".join(parts[:4])[:160]

    def remember_turn(
        self,
        role: str,
        content: str,
        *,
        code: str = "",
        lang: str = "",
        entities: Optional[List[Entity]] = None,
        action: str = "",
    ) -> None:
        self.store.turns.append({"role": role, "content": content})
        self.store.embeddings.append(self.emb.encode(content))
        if code:
            self.store.last_code = code
            self.store.last_lang = lang
            self.store.recent_actions.append(f"code:{lang or 'python'}")
        if action:
            self.store.recent_actions.append(action[:80])
            self.store.recent_actions = self.store.recent_actions[-12:]
        if entities:
            self.store.entities.extend(entities[-12:])
        # Preferences: "adım X" / "my name is X"
        m = re.search(
            r"(?:benim )?(?:adim|ismim)\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)"
            r"|my name is\s+([A-Za-z]+)",
            content,
            re.I,
        )
        if m:
            self.store.preferences["name"] = (m.group(1) or m.group(2)).capitalize()
        # Tone preference
        if re.search(r"\bkisa\s+yaz\b|\bbe concise\b|\bkisa tut\b", content, re.I):
            self.store.preferences["style"] = "concise"
        if re.search(r"\bdetayli\b|\bmore detail\b|\buzun anlat\b", content, re.I):
            self.store.preferences["style"] = "detailed"

    def retrieve(self, query: str, query_vec: np.ndarray | None = None, top_k: int = 6) -> List[MemoryHit]:
        hits: list[MemoryHit] = []
        qv = query_vec if query_vec is not None else self.emb.encode(query)
        for i, (turn, vec) in enumerate(zip(self.store.turns, self.store.embeddings)):
            score = self.emb.cosine(qv, vec)
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
        if self.store.project:
            hits.append(
                MemoryHit(
                    role="system",
                    content=self.store.project,
                    score=0.88,
                    kind="project",
                )
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
        for act in self.store.recent_actions[-3:]:
            hits.append(MemoryHit(role="system", content=act, score=0.65, kind="action"))
        return hits

    def resolve_references(
        self,
        text: str,
        entities: Sequence[Entity],
    ) -> tuple[str, dict[str, str], list[Entity]]:
        """Replace/annotate pronouns using recent entities, topic, and project."""
        resolved: dict[str, str] = {}
        enriched = list(entities)

        def fold(s: str) -> str:
            s = (s or "").lower().replace("İ", "i").replace("I", "i").replace("ı", "i")
            return s.translate(str.maketrans("çğıöşü", "cgiosu"))

        folded = fold(text)
        if not _REF_RE.search(folded):
            return text, resolved, enriched

        candidates: list[str] = []
        # Prefer project memory for "same project" / previous
        if self.store.project and any(
            x in folded for x in ("proje", "project", "ayni", "same", "onceki", "previous")
        ):
            candidates.append(self.store.project)

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
            stop = {
                "nedir", "nasil", "yaz", "what", "is", "the", "a", "bir", "ne",
                "hakkinda", "kod", "code", "write", "please", "lutfen",
                "anlat", "acikla", "neden", "how", "why", "about",
            }
            parts = [p for p in parts if fold(p) not in stop]
            if parts:
                candidates.append(" ".join(parts[:3]))

        # Person pronouns → last PERSON entity
        if re.search(r"\b(him|her|onu|ona|onun)\b", folded):
            for e in reversed(self.store.entities[-20:]):
                if e.type == EntityType.PERSON:
                    candidates.insert(0, e.normalized or e.text)
                    break

        seen = set()
        uniq = []
        for c in candidates:
            k = fold(c)
            if k and k not in seen:
                seen.add(k)
                uniq.append(c)

        if not uniq:
            return text, resolved, enriched

        antecedent = uniq[0]
        for c in uniq:
            cl = fold(c)
            if cl in {
                "docker", "react", "python", "flask", "redis", "kubernetes",
                "nginx", "fastapi", "nextjs",
            }:
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
