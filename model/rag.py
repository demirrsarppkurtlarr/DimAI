"""Phase 6 — lightweight RAG over DimAI knowledge sources.

Ranks: internal KB → learned store → (optional) embedding similarity.
Retrieves only relevant hits; abstains when confidence is low.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class RagHit:
    reply: str
    score: float
    source: str  # kb | learned
    url: str = ""
    meta: dict[str, Any] | None = None


def retrieve(query: str, *, min_score: float = 2.0) -> Optional[RagHit]:
    """Return the best grounded answer or None (avoid hallucinated filler)."""
    q = (query or "").strip()
    if not q:
        return None

    # 1) Structured KB (brain)
    try:
        from model.brain import brain, _norm

        ranked = brain._rank_kb(_norm(q))
        if ranked and ranked[0][1] >= min_score:
            entry = ranked[0][0]
            return RagHit(
                reply=str(entry.get("a") or ""),
                score=float(ranked[0][1]),
                source="kb",
                meta={"keys": entry.get("k"), "has_code": bool(entry.get("c"))},
            )
    except Exception:
        pass

    # 2) Learned Q&A store
    try:
        from model.web_research import learned

        hit = learned.lookup(q)
        if hit and hit.get("a"):
            return RagHit(
                reply=str(hit["a"]),
                score=1.5,
                source="learned",
                url=str(hit.get("url") or ""),
            )
    except Exception:
        pass

    return None


def retrieve_for_tools(query: str, *, intent: str = "") -> Optional[dict]:
    """Shape a tool payload; skip code blobs unless coding intent."""
    hit = retrieve(query)
    if not hit or not hit.reply.strip():
        return None
    out: dict[str, Any] = {
        "reply": hit.reply,
        "score": hit.score,
        "source": hit.source,
    }
    if hit.url:
        out["url"] = hit.url
    if intent == "coding" and hit.meta and hit.meta.get("has_code"):
        try:
            from model.brain import brain, _norm

            ranked = brain._rank_kb(_norm(query))
            if ranked:
                entry = ranked[0][0]
                if entry.get("c"):
                    out["code"] = entry["c"]
                    out["lang"] = entry.get("l", "python")
        except Exception:
            pass
    return out
