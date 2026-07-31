"""Phase 6 — RAG over DimAI knowledge: structured KB → top-k index → learned.

Uses hybrid embedding+stem retrieval so curated seeds are actually findable,
not just loaded into RAM. Abstains when confidence is low.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class RagHit:
    reply: str
    score: float
    source: str  # kb | kb_index | learned
    url: str = ""
    meta: dict[str, Any] | None = None
    code: str = ""
    lang: str = ""


def retrieve(query: str, *, min_score: float = 2.0, intent: str = "") -> Optional[RagHit]:
    """Return the best grounded answer or None (avoid hallucinated filler)."""
    q = (query or "").strip()
    if not q:
        return None

    intent_l = (intent or "").lower()
    q_fold = q.casefold()

    # Make/build coding asks belong to invent/codegen — do not paste a generic
    # "kod yaz" KB starter or a random HF snippet as the product.
    try:
        from model.code_policy import is_capability_prompt, needs_topic_clarify

        make_verbs = (" yaz", "yap", "olustur", "oluştur", "write", "make", "create", "kodla")
        is_make = intent_l in {"coding", "code", "command"} and any(
            v.strip() in q_fold or q_fold.endswith(v.strip()) or f" {v.strip()} " in f" {q_fold} "
            for v in make_verbs
        )
        explainer = any(
            x in q_fold
            for x in ("nedir", "nasil", "nasıl", "what is", "how does", "acikla", "açıkla", "anlat", "why")
        )
        if (is_make or is_capability_prompt(q) or needs_topic_clarify(q)) and not explainer:
            return None
    except Exception:
        pass

    # 1) Structured KB (brain) — high-precision hand entries
    try:
        from model.brain import brain, _norm
        from model.kb_index import is_settings_howto

        # "css ayarlarına nasıl girerim" ≠ random CSS snippet / centering tip
        skip_brain = is_settings_howto(q) and intent_l not in {"coding", "code", "command"}
        if not skip_brain:
            ranked = brain._rank_kb(_norm(q))
            if ranked and ranked[0][1] >= min_score:
                entry = ranked[0][0]
                keys = " ".join(str(k) for k in (entry.get("k") or [])).casefold()
                # Require at least a soft key overlap for short howto asks
                qn = _norm(q)
                key_hit = any(len(k) > 2 and k in qn for k in _norm(keys).split())
                if key_hit or ranked[0][1] >= 6.0:
                    return RagHit(
                        reply=str(entry.get("a") or ""),
                        score=float(ranked[0][1]),
                        source="kb",
                        meta={"keys": entry.get("k"), "has_code": bool(entry.get("c"))},
                        code=str(entry.get("c") or ""),
                        lang=str(entry.get("l") or "python"),
                    )
    except Exception:
        pass

    # 2) Knowledge index — top-k hybrid over all seeded corpora (+ Supabase cold)
    try:
        from model.kb_index import (
            is_factual_ask,
            is_settings_howto,
            knowledge_index,
            synthesize_hits,
        )

        kind = None
        if intent_l in {"coding", "code", "command"}:
            kind = "code"
        elif intent_l in {"conversation", "chat"}:
            kind = "chat"
        # Factual asks must not browse chat/roleplay corpora
        if is_factual_ask(q) and kind is None:
            kind = "qa"
        hits = knowledge_index.search(q, top_k=6, kind=kind if kind != "qa" else None, min_score=0.32)
        if kind == "code" and (not hits or hits[0].score < 0.38):
            open_hits = knowledge_index.search(q, top_k=6, kind=None, min_score=0.32)
            if open_hits and (not hits or open_hits[0].score > hits[0].score):
                hits = open_hits
        # Settings howto without explicit coding → abstain (let WEB/CHAT explain UX)
        if is_settings_howto(q) and intent_l not in {"coding", "code", "command"}:
            hits = []
        payload = synthesize_hits(hits, query=q)
        if payload and float(payload.get("score") or 0) >= 0.42:
            return RagHit(
                reply=str(payload.get("reply") or ""),
                score=1.2 + float(payload["score"]),
                source=str(payload.get("source") or "kb_index"),
                url=str(payload.get("url") or ""),
                meta=payload.get("meta") if isinstance(payload.get("meta"), dict) else None,
                code=str(payload.get("code") or ""),
                lang=str(payload.get("lang") or "python"),
            )
    except Exception:
        pass

    # 3) Legacy learned store (exact-ish stem match) — write-path compatibility
    try:
        from model.web_research import learned

        hit = learned.lookup(q)
        if hit and hit.get("a"):
            return RagHit(
                reply=str(hit["a"]),
                score=1.5 + (0.4 if hit.get("c") else 0.0),
                source="learned",
                url=str(hit.get("url") or ""),
                meta={"has_code": bool(hit.get("c")), "lang": hit.get("l", "python")},
                code=str(hit.get("c") or ""),
                lang=str(hit.get("l") or "python"),
            )
    except Exception:
        pass

    return None


def retrieve_for_tools(query: str, *, intent: str = "") -> Optional[dict]:
    """Shape a tool payload; skip code blobs unless coding intent."""
    hit = retrieve(query, intent=intent)
    if not hit:
        return None
    if not (hit.reply or "").strip() and not hit.code:
        return None

    out: dict[str, Any] = {
        "reply": hit.reply or "",
        "score": hit.score,
        "source": hit.source,
    }
    if hit.url:
        out["url"] = hit.url
    if hit.meta:
        out["meta"] = hit.meta

    want_code = intent in {"coding", "code", "command"}
    if want_code and hit.code:
        out["code"] = hit.code
        out["lang"] = hit.lang or "python"
        if not out["reply"]:
            out["reply"] = "Bilgi indeksinden ilgili kod örneği:"
    elif want_code and hit.meta and hit.meta.get("has_code") and not hit.code:
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
    return out if out.get("reply") or out.get("code") else None
