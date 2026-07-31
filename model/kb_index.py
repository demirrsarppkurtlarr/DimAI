"""DimAI knowledge index — hot local + cold Supabase retrieval.

Goal: use ALL curated knowledge the right way:
  - Index chunks (not dump entire corpora into one lookup)
  - Hybrid score: local embedding cosine + stem overlap
  - Top-k retrieval (multi-hit), never force a weak single match
  - Optional Supabase pgvector cold tier when SUPABASE_* is set

This does NOT replace invent/codegen for coding — it grounds Q&A and
supplies code exemplars only when the hit is strong and relevant.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
HOT_PATH = DATA / "kb_hot_chunks.json"
VECTOR_CACHE = DATA / "kb_hot_vectors.npz"

SUPABASE_URL = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
SUPABASE_KEY = (
    os.environ.get("SUPABASE_SERVICE_KEY")
    or os.environ.get("SUPABASE_KEY")
    or ""
)
KB_TABLE = os.environ.get("SUPABASE_KB_TABLE", "kb_chunks")

STOP = frozenset({
    "nedir", "ne", "nasil", "nasıl", "kim", "kimdir", "hakkinda", "hakkında", "bilgi", "ver",
    "anlat", "bana", "bir", "the", "what", "is", "who", "ile", "mi", "mu",
    "ve", "de", "da", "icin", "için", "yaz", "kod", "code", "lutfen", "lütfen",
    "peki", "o", "bu", "su", "onun", "bunun", "gibi", "olan", "orda", "burda",
    "orada", "burada", "şey", "sey", "bazi", "bazı", "cok", "çok", "daha",
    "miyim", "misin", "about", "info", "information", "please", "tell", "me",
    "how", "to", "do", "can", "you", "give", "some",
    # continuation fillers — must never match knowledge chunks by themselves
    "fazla", "devam", "et", "biraz", "tekrar", "yine", "baska", "başka",
    "detay", "detayli", "detaylı", "more", "continue", "again", "further",
})

# Chat/roleplay corpora — never answer factual asks from these alone.
_CHATTY_SOURCES = (
    "sohbet", "turkce-sohbet", "alpaca-turkish", "turkish-alpaca",
    "tulu", "bahadir26", "saillab", "tflai",
)

_JUNK_OPENERS = re.compile(
    r"^\s*(haha|hahaha|lan |ula |oğlum|oglum|abi |yaw+|yaa+|evet ya|vallahi)",
    re.I,
)


def _norm(text: str) -> str:
    text = (text or "").replace("İ", "i").replace("I", "i").replace("ı", "i")
    text = text.lower().translate(str.maketrans("çğıöşü", "cgiosu"))
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _keywords(text: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for w in _norm(text).split():
        if w in STOP or len(w) < 2 or w.isdigit():
            continue
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out[:24]


def _stems(words: Iterable[str]) -> set[str]:
    return {w[: min(len(w), 5)] for w in words if len(w) >= 2}


def _content_stems(text: str) -> set[str]:
    return _stems(_keywords(text))


def is_factual_ask(text: str) -> bool:
    t = _norm(text)
    return any(
        x in t
        for x in (
            "nedir", "ne demek", "hakkinda", "bilgi", "kimdir", "nasil",
            "what is", "about", "explain", "acikla", "anlat", "tanimi",
        )
    )


def is_settings_howto(text: str) -> bool:
    t = _norm(text)
    return any(x in t for x in ("ayar", "settings", "menu", "menü", "nasil gir", "nereden"))


def chunk_is_chatty(ch: "Chunk") -> bool:
    if ch.kind == "chat":
        return True
    src = (ch.source or "").casefold()
    return any(s in src for s in _CHATTY_SOURCES)


def hit_supports_query(query: str, ch: "Chunk") -> bool:
    """Require real topical overlap — stopwords alone must not match."""
    q_stems = _content_stems(query)
    if not q_stems:
        return False
    title_stems = _content_stems(f"{ch.title} {' '.join(ch.tags)}")
    blob = f"{ch.title} {ch.body[:500]} {ch.code[:200]} {' '.join(ch.tags)}"
    c_stems = _content_stems(blob)
    if not c_stems:
        return False
    inter = q_stems & c_stems
    if not inter:
        return False
    # Anti-hallucination: at least one content stem must appear in TITLE/tags,
    # not only buried in a long body.
    if not (q_stems & title_stems):
        return len(inter) >= 3
    cover = len(inter) / max(len(q_stems), 1)
    return cover >= 0.4 or len(inter) >= 2


def looks_like_junk_reply(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return True
    if _JUNK_OPENERS.search(t):
        return True
    # Roleplay / story dumps
    low = t.casefold()
    if any(x in low[:120] for x in ("bir zamanlar", "adında bir", "hikaye", "köyde yaşayan")):
        return True
    return False


def _chunk_id(kind: str, title: str, source: str) -> str:
    raw = f"{kind}|{source}|{title[:160]}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:20]


@dataclass
class Chunk:
    chunk_id: str
    kind: str  # qa | code | chat
    title: str
    body: str
    code: str = ""
    lang: str = ""
    tags: list[str] = field(default_factory=list)
    quality: float = 0.7
    source: str = ""
    url: str = ""

    def search_text(self) -> str:
        bits = [self.title, self.body[:800]]
        if self.code:
            bits.append(self.code[:400])
        if self.tags:
            bits.append(" ".join(self.tags[:12]))
        return "\n".join(b for b in bits if b)


@dataclass
class ChunkHit:
    chunk: Chunk
    score: float
    via: str  # local | supabase


class KnowledgeIndex:
    """In-process hot index + optional Supabase cold queries."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.chunks: list[Chunk] = []
        self._vectors: Optional[np.ndarray] = None
        self._stem_index: dict[str, set[int]] = {}
        self._ids: set[str] = set()
        self.backend = "memory"
        self.configured = bool(SUPABASE_URL and SUPABASE_KEY)
        self.booted = False
        self.stats: dict[str, Any] = {"local": 0, "supabase_pushed": 0, "queries": 0}

    # ------------------------------------------------------------------ boot
    def bootstrap(self, *, push_supabase: bool = False) -> dict[str, int]:
        """Load hot pack and/or seed files; encode embeddings once."""
        from model.nlu.embedding import embedding_engine

        t0 = time.time()
        added = 0
        with self._lock:
            if HOT_PATH.exists():
                added += self._ingest_file(HOT_PATH, limit=20000, source_label="hot")
            # Coding-first caps: ALL curated code seeds + quality-ranked rest.
            plan = [
                (DATA / "mega_code_seed.json", 5500, "mega_code", "code"),
                (DATA / "tr_code_learned_seed.json", 2700, "tr_code", "code"),
                (DATA / "code_learned_seed.json", 3500, "hf_code", "code"),
                (DATA / "huge_learned_seed.json", 3600, "huge", "qa"),
                (DATA / "tr_chat_learned_seed.json", 2400, "tr_chat", "chat"),
                (DATA / "tulu_learned_seed.json", 700, "tulu", "chat"),
                (DATA / "learned.json", 900, "learned", "qa"),
            ]
            for path, limit, label, default_kind in plan:
                added += self._ingest_seed(path, limit=limit, source_label=label, default_kind=default_kind)

            self._rebuild_index()
            self.booted = True
            self.stats["local"] = len(self.chunks)
            if self.chunks:
                texts = [c.search_text() for c in self.chunks]
                ids = [c.chunk_id for c in self.chunks]
                loaded = self._try_load_vectors(ids)
                if loaded is not None:
                    self._vectors = loaded
                    self.stats["vectors"] = "cache"
                else:
                    # Stem index is enough to answer immediately; embeddings fill in.
                    self._vectors = None
                    self.stats["vectors"] = "pending"
                    threading.Thread(
                        target=self._encode_async,
                        args=(ids, texts),
                        daemon=True,
                        name="kb-encode",
                    ).start()
            else:
                self._vectors = np.zeros((0, embedding_engine.dim), dtype=np.float32)
                self.stats["vectors"] = "empty"
            self.stats["boot_sec"] = round(time.time() - t0, 2)

        if push_supabase and self.configured:
            pushed = self.push_all_to_supabase(limit=8000)
            self.stats["supabase_pushed"] = pushed

        # Pull a fresh cold slice if remote is configured (doesn't duplicate ids)
        if self.configured:
            remote = self._pull_supabase(limit=1500)
            if remote:
                with self._lock:
                    before = len(self.chunks)
                    for ch in remote:
                        self._add_chunk(ch)
                    if len(self.chunks) > before:
                        self._rebuild_index()
                        texts = [c.search_text() for c in self.chunks]
                        self._vectors = embedding_engine.encode_many(texts)
                    self.stats["local"] = len(self.chunks)
                    self.stats["remote_pulled"] = len(remote)

        self.backend = "supabase+memory" if self.configured else "memory"
        return {"chunks": len(self.chunks), "added": added, **{k: v for k, v in self.stats.items() if k != "local"}}

    def _try_load_vectors(self, ids: list[str]) -> Optional[np.ndarray]:
        try:
            if not VECTOR_CACHE.exists():
                return None
            data = np.load(VECTOR_CACHE, allow_pickle=True)
            cached_ids = [str(x) for x in data["ids"].tolist()]
            if cached_ids == ids and data["vectors"].shape[0] == len(ids):
                return data["vectors"].astype(np.float32)
        except Exception:
            return None
        return None

    def _encode_async(self, ids: list[str], texts: list[str]) -> None:
        from model.nlu.embedding import embedding_engine

        try:
            vectors = embedding_engine.encode_many(texts)
            with self._lock:
                # Only apply if chunk set unchanged
                if [c.chunk_id for c in self.chunks] == ids:
                    self._vectors = vectors
                    self.stats["vectors"] = "ready"
            try:
                DATA.mkdir(parents=True, exist_ok=True)
                np.savez_compressed(
                    VECTOR_CACHE,
                    ids=np.array(ids, dtype=object),
                    vectors=vectors,
                )
            except Exception:
                pass
        except Exception as exc:
            self.stats["vectors"] = f"error:{exc}"[:80]

    def _ingest_file(self, path: Path, *, limit: int, source_label: str) -> int:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return 0
        if not isinstance(raw, list):
            return 0
        n = 0
        for row in raw[:limit]:
            ch = self._row_to_chunk(row, source_label=source_label)
            if ch and self._add_chunk(ch):
                n += 1
        return n

    def _ingest_seed(
        self,
        path: Path,
        *,
        limit: int,
        source_label: str,
        default_kind: str,
    ) -> int:
        if not path.exists():
            return 0
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return 0
        if not isinstance(raw, list):
            return 0
        # Prefer code-bearing rows, then higher quality (coding-first knowledge)
        rows = sorted(
            raw,
            key=lambda r: (
                1 if (r or {}).get("c") or (r or {}).get("code") else 0,
                float((r or {}).get("quality") or 0.5),
            ),
            reverse=True,
        )
        n = 0
        for row in rows[:limit]:
            ch = self._row_to_chunk(row, source_label=source_label, default_kind=default_kind)
            if ch and self._add_chunk(ch):
                n += 1
        return n

    def _row_to_chunk(
        self,
        row: dict,
        *,
        source_label: str,
        default_kind: str = "qa",
    ) -> Optional[Chunk]:
        if not isinstance(row, dict):
            return None
        title = str(row.get("q") or row.get("title") or "").strip()
        body = str(row.get("a") or row.get("body") or "").strip()
        code = str(row.get("c") or row.get("code") or "").strip()
        if len(title) < 5 or (len(body) < 15 and len(code) < 20):
            return None
        kind = str(row.get("kind") or default_kind)
        if code and kind == "qa":
            kind = "code"
        source = str(row.get("source") or source_label)[:80]
        # Noisy chat roleplay dumps pollute factual RAG — keep them out of the hot index.
        src_l = source.casefold()
        if any(x in src_l for x in ("sohbet", "bahadir26", "roleplay")):
            return None
        lang = str(row.get("l") or row.get("lang") or ("python" if code else ""))[:40]
        tags = row.get("tags") or row.get("kw") or _keywords(title)
        if isinstance(tags, str):
            tags = [tags]
        tags = [str(t).casefold() for t in list(tags)[:16]]
        source = str(row.get("source") or source_label)[:80]
        cid = str(row.get("chunk_id") or _chunk_id(kind, title, source))
        return Chunk(
            chunk_id=cid,
            kind=kind,
            title=title[:400],
            body=body[:3500],
            code=code[:3500],
            lang=lang,
            tags=tags,
            quality=float(row.get("quality") or 0.75),
            source=source,
            url=str(row.get("url") or "")[:300],
        )

    def _add_chunk(self, ch: Chunk) -> bool:
        if ch.chunk_id in self._ids:
            return False
        self._ids.add(ch.chunk_id)
        self.chunks.append(ch)
        return True

    def _rebuild_index(self) -> None:
        idx: dict[str, set[int]] = {}
        for i, ch in enumerate(self.chunks):
            words = _keywords(ch.title) + list(ch.tags) + _keywords(ch.body[:240])
            for stem in _stems(words):
                idx.setdefault(stem, set()).add(i)
        self._stem_index = idx

    # ------------------------------------------------------------------ search
    def search(
        self,
        query: str,
        *,
        top_k: int = 6,
        kind: str | None = None,
        min_score: float = 0.28,
    ) -> list[ChunkHit]:
        """Hybrid local search; merges Supabase cold hits when configured."""
        q = (query or "").strip()
        if not q:
            return []
        self.stats["queries"] = int(self.stats.get("queries") or 0) + 1
        if not self.booted:
            self.bootstrap()

        local = self._search_local(q, top_k=top_k * 3, kind=kind, min_score=min_score)
        # Relevance gate — drop chatty/off-topic matches before merge
        local = [
            h for h in local
            if hit_supports_query(q, h.chunk) and not looks_like_junk_reply(h.chunk.body)
        ]
        if is_factual_ask(q):
            local = [h for h in local if not chunk_is_chatty(h.chunk)]
        if is_settings_howto(q) and "kod" not in _norm(q) and "css yaz" not in _norm(q):
            # "ayarlara nasıl girerim" is UX help, not a random CSS snippet farm
            local = [h for h in local if not (h.chunk.code and len(h.chunk.body) < 80)]

        remote: list[ChunkHit] = []
        if self.configured:
            try:
                remote = self._search_supabase(q, top_k=top_k, kind=kind)
                remote = [
                    h for h in remote
                    if hit_supports_query(q, h.chunk) and not looks_like_junk_reply(h.chunk.body)
                ]
                if is_factual_ask(q):
                    remote = [h for h in remote if not chunk_is_chatty(h.chunk)]
            except Exception:
                remote = []

        merged: dict[str, ChunkHit] = {}
        for hit in local + remote:
            prev = merged.get(hit.chunk.chunk_id)
            if not prev or hit.score > prev.score:
                merged[hit.chunk.chunk_id] = hit
        out = sorted(merged.values(), key=lambda h: -h.score)
        return [h for h in out if h.score >= min_score][:top_k]

    def _search_local(
        self,
        query: str,
        *,
        top_k: int,
        kind: str | None,
        min_score: float,
    ) -> list[ChunkHit]:
        from model.nlu.embedding import embedding_engine

        q_kw = _keywords(query)
        q_stems = _stems(q_kw)
        q_vec = embedding_engine.encode(query)

        with self._lock:
            if not self.chunks:
                return []
            cand: set[int] = set()
            for stem in q_stems:
                cand |= self._stem_index.get(stem, set())
            sims = None
            vectors_ready = (
                self._vectors is not None
                and len(self._vectors) == len(self.chunks)
                and len(self._vectors) > 0
            )
            if vectors_ready:
                if len(self.chunks) <= 5000:
                    sims = self._vectors @ q_vec
                    emb_top = np.argpartition(-sims, min(40, len(sims) - 1))[:40]
                    cand |= {int(i) for i in emb_top}
                elif not cand:
                    cand = set(range(min(len(self.chunks), 800)))
            elif not cand:
                # Embeddings not ready — fall back to broader stem scan of titles
                for i, ch in enumerate(self.chunks[:3000]):
                    if q_stems & _stems(_keywords(ch.title) + ch.tags):
                        cand.add(i)
                if not cand:
                    return []

            scored: list[ChunkHit] = []
            for i in cand:
                if i < 0 or i >= len(self.chunks):
                    continue
                ch = self.chunks[i]
                if kind == "code" and ch.kind not in {"code", "qa"} and not ch.code:
                    continue
                if kind == "chat" and ch.kind not in {"chat", "qa"}:
                    continue
                item_words = ch.tags + _keywords(ch.title) + _keywords(ch.body[:280])
                if ch.code:
                    item_words = item_words + _keywords(ch.code[:160])
                item_stems = _stems(item_words)
                inter = len(q_stems & item_stems) if q_stems else 0
                if q_stems:
                    cover = inter / max(len(q_stems), 1)
                    prec = inter / max(len(item_stems), 1)
                    stem_score = 0.75 * cover + 0.25 * prec
                else:
                    stem_score = 0.0
                if sims is not None:
                    cos = float(sims[i])
                elif vectors_ready and i < len(self._vectors):
                    cos = float(embedding_engine.cosine(q_vec, self._vectors[i]))
                else:
                    cos = 0.0
                # When embeddings pending, lean on stems; otherwise hybrid.
                if not vectors_ready:
                    score = 0.75 * stem_score + 0.25 * float(ch.quality)
                else:
                    score = 0.58 * max(cos, 0.0) + 0.32 * stem_score + 0.10 * float(ch.quality)
                if kind == "code" and ch.code:
                    score += 0.04
                if score < min_score:
                    continue
                scored.append(ChunkHit(chunk=ch, score=score, via="local"))
            scored.sort(key=lambda h: -h.score)
            return scored[:top_k]

    def best(self, query: str, *, kind: str | None = None) -> Optional[ChunkHit]:
        hits = self.search(query, top_k=1, kind=kind, min_score=0.32)
        return hits[0] if hits else None

    # -------------------------------------------------------------- supabase
    def _sb_headers(self) -> dict:
        return {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
        }

    def _pull_supabase(self, *, limit: int = 1500) -> list[Chunk]:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/{KB_TABLE}",
            params={
                "select": "chunk_id,kind,title,body,code,lang,tags,quality,source,url",
                "order": "quality.desc",
                "limit": str(limit),
            },
            headers=self._sb_headers(),
            timeout=12,
        )
        if r.status_code >= 400:
            return []
        out: list[Chunk] = []
        for row in r.json() or []:
            ch = self._row_to_chunk(
                {
                    "chunk_id": row.get("chunk_id"),
                    "kind": row.get("kind"),
                    "q": row.get("title"),
                    "a": row.get("body"),
                    "c": row.get("code"),
                    "l": row.get("lang"),
                    "tags": row.get("tags") or [],
                    "quality": row.get("quality"),
                    "source": row.get("source"),
                    "url": row.get("url"),
                },
                source_label=str(row.get("source") or "supabase"),
            )
            if ch:
                out.append(ch)
        return out

    def _search_supabase(
        self,
        query: str,
        *,
        top_k: int,
        kind: str | None,
    ) -> list[ChunkHit]:
        from model.nlu.embedding import embedding_engine

        vec = embedding_engine.encode(query).astype(float).tolist()
        payload = {
            "query_embedding": vec,
            "match_count": top_k,
            "filter_kind": kind,
            "min_quality": 0.0,
        }
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/rpc/match_kb_chunks",
            headers=self._sb_headers(),
            json=payload,
            timeout=10,
        )
        if r.status_code >= 400:
            return []
        hits: list[ChunkHit] = []
        for row in r.json() or []:
            ch = Chunk(
                chunk_id=str(row.get("chunk_id") or _chunk_id("qa", str(row.get("title") or ""), "sb")),
                kind=str(row.get("kind") or "qa"),
                title=str(row.get("title") or "")[:400],
                body=str(row.get("body") or "")[:3500],
                code=str(row.get("code") or "")[:3500],
                lang=str(row.get("lang") or "")[:40],
                tags=list(row.get("tags") or [])[:16],
                quality=float(row.get("quality") or 0.7),
                source=str(row.get("source") or "supabase"),
                url=str(row.get("url") or "")[:300],
            )
            score = float(row.get("score") or 0.0)
            if score >= 0.25:
                hits.append(ChunkHit(chunk=ch, score=score, via="supabase"))
        return hits

    def push_all_to_supabase(self, *, limit: int = 8000) -> int:
        """Upsert local hot chunks to Supabase (service role). Fail-soft."""
        if not self.configured:
            return 0
        from model.nlu.embedding import embedding_engine

        with self._lock:
            rows = list(self.chunks[:limit])
            vectors = self._vectors
        if vectors is None or len(vectors) == 0:
            return 0
        pushed = 0
        batch: list[dict] = []
        for i, ch in enumerate(rows):
            if i >= len(vectors):
                break
            batch.append({
                "chunk_id": ch.chunk_id,
                "kind": ch.kind,
                "title": ch.title,
                "body": ch.body,
                "code": ch.code,
                "lang": ch.lang,
                "tags": ch.tags,
                "quality": ch.quality,
                "source": ch.source,
                "url": ch.url,
                "embedding": vectors[i].astype(float).tolist(),
            })
            if len(batch) >= 80:
                pushed += self._upsert_batch(batch)
                batch = []
        if batch:
            pushed += self._upsert_batch(batch)
        return pushed

    def _upsert_batch(self, batch: list[dict]) -> int:
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/{KB_TABLE}",
            headers={
                **self._sb_headers(),
                "Prefer": "resolution=merge-duplicates,return=minimal",
            },
            params={"on_conflict": "chunk_id"},
            json=batch,
            timeout=30,
        )
        if r.status_code >= 400:
            return 0
        return len(batch)

    def add_learned(self, question: str, answer: str, *, url: str = "", code: str = "", lang: str = "") -> None:
        """Append a newly learned fact into the hot index (+ remote if configured)."""
        from model.nlu.embedding import embedding_engine

        ch = self._row_to_chunk(
            {
                "q": question,
                "a": answer,
                "c": code,
                "l": lang,
                "url": url,
                "quality": 0.85,
                "source": "live",
            },
            source_label="live",
            default_kind="code" if code else "qa",
        )
        if not ch:
            return
        with self._lock:
            if not self._add_chunk(ch):
                return
            vec = embedding_engine.encode(ch.search_text())
            if self._vectors is None or len(self._vectors) == 0:
                self._vectors = vec.reshape(1, -1)
            else:
                self._vectors = np.vstack([self._vectors, vec])
            i = len(self.chunks) - 1
            for stem in _stems(ch.tags + _keywords(ch.title)):
                self._stem_index.setdefault(stem, set()).add(i)
            self.stats["local"] = len(self.chunks)
        if self.configured:
            try:
                self._upsert_batch([{
                    "chunk_id": ch.chunk_id,
                    "kind": ch.kind,
                    "title": ch.title,
                    "body": ch.body,
                    "code": ch.code,
                    "lang": ch.lang,
                    "tags": ch.tags,
                    "quality": ch.quality,
                    "source": ch.source,
                    "url": ch.url,
                    "embedding": embedding_engine.encode(ch.search_text()).astype(float).tolist(),
                }])
            except Exception:
                pass

    def count(self) -> int:
        return len(self.chunks)


# Process singleton
knowledge_index = KnowledgeIndex()


def synthesize_hits(hits: Sequence[ChunkHit], *, language: str = "tr", query: str = "") -> Optional[dict]:
    """Turn top-k hits into a single grounded reply payload."""
    if not hits:
        return None
    # Keep only hits that still support the query
    if query:
        hits = [h for h in hits if hit_supports_query(query, h.chunk)]
        if is_factual_ask(query):
            hits = [h for h in hits if not chunk_is_chatty(h.chunk)]
    if not hits:
        return None
    best = hits[0]
    ch = best.chunk
    min_ok = 0.45 if chunk_is_chatty(ch) else 0.38
    if best.score < min_ok:
        return None
    if looks_like_junk_reply(ch.body) and not ch.code:
        return None

    reply = (ch.body or "").strip()
    if not reply and ch.code:
        reply = (
            "İlgili kod örneğini bilgiden çektim:"
            if language == "tr"
            else "Pulled a relevant code example from knowledge:"
        )

    # Extras only when they share content stems with the question (never random stories)
    extras: list[str] = []
    q_stems = _content_stems(query) if query else set()
    for h in hits[1:4]:
        if h.score < max(0.42, best.score - 0.08):
            continue
        if h.chunk.title.casefold() == ch.title.casefold():
            continue
        if query and not hit_supports_query(query, h.chunk):
            continue
        if looks_like_junk_reply(h.chunk.body):
            continue
        if q_stems and not (q_stems & _content_stems(h.chunk.title + " " + h.chunk.body[:200])):
            continue
        snippet = (h.chunk.body or "").strip().replace("\n", " ")
        if len(snippet) < 40:
            continue
        extras.append(f"• {h.chunk.title[:80]}: {snippet[:160]}")

    if extras and language == "tr":
        reply = reply.rstrip() + "\n\nİlgili ek bilgi:\n" + "\n".join(extras[:2])
    elif extras:
        reply = reply.rstrip() + "\n\nRelated:\n" + "\n".join(extras[:2])

    out: dict[str, Any] = {
        "reply": reply,
        "score": float(best.score),
        "source": f"kb_index:{best.via}",
        "url": ch.url,
        "meta": {
            "chunk_id": ch.chunk_id,
            "kind": ch.kind,
            "title": ch.title[:120],
            "hits": len(hits),
            "via": best.via,
            "has_code": bool(ch.code),
            "lang": ch.lang or "python",
            "grounded": True,
        },
    }
    if ch.code:
        out["code"] = ch.code
        out["lang"] = ch.lang or "python"
    return out
