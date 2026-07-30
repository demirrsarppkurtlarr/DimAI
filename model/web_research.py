"""DimAI web research — free sources (Wikipedia, DuckDuckGo), no API keys.

Answers found online are saved to a learned-knowledge store so DimAI can
answer the same (or similar) questions offline next time — self-learning
at the knowledge level.
"""
from __future__ import annotations

import difflib
import json
import os
import re
import threading
import time
import unicodedata
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parents[1]
LEARNED_PATH = ROOT / "data" / "learned.json"

# Optional Supabase persistence (survives Render restarts/deploys)
SUPABASE_URL = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY") or ""
SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "learned")


def _sb_headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }

HEADERS = {"User-Agent": "DimAI/1.0 (self-hosted learning assistant)"}
TIMEOUT = 4

STOPWORDS = {
    "nedir", "ne", "nasil", "kim", "kimdir", "hakkinda", "bilgi", "ver",
    "anlat", "bana", "bir", "the", "what", "is", "who", "ile", "mi", "mu",
    "midir", "acaba", "ki", "ya", "ve", "de", "da", "icin", "yaz",
    "neresi", "nerede", "nerededir", "nerededir", "kac", "kactir", "kacdir",
    "hangisi", "hangi", "neden", "niye", "zaman", "kadar", "soyle", "bul",
}


def _norm(text: str) -> str:
    text = text.lower()
    text = text.translate(str.maketrans("çğıöşü", "cgiosu"))
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _keywords(text: str) -> set[str]:
    return {w for w in _norm(text).split() if w not in STOPWORDS and len(w) > 1}


def _clean_query(text: str) -> str:
    """Strip question words so search engines get the core topic."""
    words = [w for w in text.strip().rstrip("?!.").split() if _norm(w) not in STOPWORDS]
    return " ".join(words) or text


# ---------------------------------------------------------------------------
# Learned knowledge store
# ---------------------------------------------------------------------------

class LearnedStore:
    """Learned web knowledge. Persists to Supabase when configured, else local JSON."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: list[dict] = []
        self.configured = bool(SUPABASE_URL and SUPABASE_KEY)
        self.backend = "supabase" if self.configured else "file"
        self._load()

    # ---------- persistence backends ----------

    def _load(self) -> None:
        if self.backend == "supabase":
            try:
                r = requests.get(
                    f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}",
                    params={"select": "q,kw,a,url", "order": "id.desc", "limit": "2000"},
                    headers=_sb_headers(),
                    timeout=8,
                )
                r.raise_for_status()
                self._items = list(reversed(r.json()))
                return
            except Exception:
                self.backend = "file"  # graceful fallback
        if LEARNED_PATH.exists():
            try:
                self._items = json.loads(LEARNED_PATH.read_text(encoding="utf-8"))
            except Exception:
                self._items = []

    def _save_file(self) -> None:
        LEARNED_PATH.parent.mkdir(parents=True, exist_ok=True)
        LEARNED_PATH.write_text(
            json.dumps(self._items, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )

    def _save_supabase(self, entry: dict) -> None:
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}",
            headers={**_sb_headers(), "Prefer": "return=minimal"},
            json={
                "q": entry["q"],
                "kw": entry["kw"],
                "a": entry["a"],
                "url": entry["url"],
            },
            timeout=8,
        )
        r.raise_for_status()

    def add(self, question: str, answer: str, url: str = "") -> None:
        with self._lock:
            entry = {
                "q": question.strip()[:300],
                "kw": sorted(_keywords(question)),
                "a": answer.strip()[:3000],
                "url": url,
                "t": time.time(),
            }
            self._items.append(entry)
            if len(self._items) > 2000:
                self._items = self._items[-2000:]
            # Self-healing: if Supabase is configured, keep trying it even after
            # an earlier failure (e.g. table created after boot).
            if self.configured:
                try:
                    self._save_supabase(entry)
                    self.backend = "supabase"
                    return
                except Exception:
                    self.backend = "file"
            self._save_file()

    def lookup(self, question: str) -> Optional[dict]:
        kw = _keywords(question)
        if not kw:
            return None
        best, best_score = None, 0.0
        with self._lock:
            for item in self._items:
                item_kw = set(item.get("kw", []))
                if not item_kw:
                    continue
                inter = len(kw & item_kw)
                if inter == 0:
                    # No shared topic words -> never match on phrasing alone
                    continue
                union = len(kw | item_kw)
                score = inter / union if union else 0.0
                # similarity of topic keywords (stopwords already removed)
                ratio = difflib.SequenceMatcher(
                    None, " ".join(sorted(kw)), " ".join(sorted(item_kw))
                ).ratio()
                score = max(score, ratio)
                if score > best_score:
                    best, best_score = item, score
        if best and best_score >= 0.6:
            return best
        return None

    def count(self) -> int:
        return len(self._items)


# ---------------------------------------------------------------------------
# Free web sources
# ---------------------------------------------------------------------------

def wikipedia_lookup(query: str, lang: str = "tr") -> Optional[tuple[str, str]]:
    try:
        r = requests.get(
            f"https://{lang}.wikipedia.org/w/api.php",
            params={
                "action": "opensearch",
                "search": query,
                "limit": 1,
                "namespace": 0,
                "format": "json",
            },
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        titles = r.json()[1]
        if not titles:
            return None
        title = titles[0]
        s = requests.get(
            f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(title)}",
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        data = s.json()
        extract = (data.get("extract") or "").strip()
        if len(extract) < 40:
            return None
        url = (
            data.get("content_urls", {}).get("desktop", {}).get("page", "")
            or f"https://{lang}.wikipedia.org/wiki/{quote(title)}"
        )
        return extract, url
    except Exception:
        return None


def duckduckgo_lookup(query: str) -> Optional[tuple[str, str]]:
    try:
        r = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        data = r.json()
        text = (data.get("AbstractText") or data.get("Answer") or "").strip()
        if text and len(text) >= 40:
            return text, data.get("AbstractURL", "")
        for topic in (data.get("RelatedTopics") or [])[:3]:
            if isinstance(topic, dict) and topic.get("Text"):
                t = topic["Text"].strip()
                if len(t) >= 40:
                    return t, topic.get("FirstURL", "")
    except Exception:
        pass
    return None


def research(question: str) -> Optional[dict]:
    """Try free sources in order; return {'answer','url','provider'} or None."""
    query = _clean_query(question)
    for provider, fn in (
        ("Wikipedia (TR)", lambda: wikipedia_lookup(query, "tr")),
        ("Wikipedia (EN)", lambda: wikipedia_lookup(query, "en")),
        ("DuckDuckGo", lambda: duckduckgo_lookup(query)),
    ):
        found = fn()
        if found:
            answer, url = found
            # keep answers concise
            if len(answer) > 1200:
                cut = answer[:1200]
                answer = cut[: cut.rfind(".") + 1] or cut
            return {"answer": answer, "url": url, "provider": provider}
    return None


learned = LearnedStore()
