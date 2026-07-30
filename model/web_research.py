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
    "neresi", "nerede", "nerededir", "kac", "kactir", "kacdir",
    "hangisi", "hangi", "neden", "niye", "zaman", "kadar", "soyle", "bul",
    "peki", "o", "bu", "su", "onun", "bunun",
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

def _strip_html(html: str) -> str:
    import html as html_mod

    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    html = re.sub(r"<[^>]+>", " ", html)
    html = html_mod.unescape(html)
    return re.sub(r"\s+", " ", html).strip()


def _relevance_score(query: str, title: str, text: str) -> float:
    """Score how well a page covers the query.

    Returns 0 when required keywords are missing. Turkish suffixes are handled
    with a crude prefix-stem match (first 5 normalized chars) on space-stripped
    text, e.g. 'karadelik' matches 'kara delik'.
    """
    qnorm = _norm(query)
    kws = [w for w in qnorm.split() if len(w) >= 3]
    tns = _norm(title + " " + text).replace(" ", "")
    if kws:
        hits = sum(1 for w in kws if w[: min(len(w), 5)] in tns)
        ratio = hits / len(kws)
        if (len(kws) <= 3 and hits < len(kws)) or ratio < 0.7:
            return 0.0
    else:
        ratio = 1.0
    score = ratio
    if qnorm.replace(" ", "") in tns:
        score += 1.0  # tam ifade eşleşmesi
    score += difflib.SequenceMatcher(None, _norm(title), qnorm).ratio() * 0.5
    return score


def _wiki_candidates(query: str, lang: str) -> list:
    titles: list = []
    try:
        r = requests.get(
            f"https://{lang}.wikipedia.org/w/api.php",
            params={
                "action": "opensearch",
                "search": query,
                "limit": 2,
                "namespace": 0,
                "format": "json",
            },
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        titles.extend(r.json()[1])
    except Exception:
        pass
    try:
        r = requests.get(
            f"https://{lang}.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": 2,
                "format": "json",
            },
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        titles.extend(h["title"] for h in r.json().get("query", {}).get("search", []))
    except Exception:
        pass
    seen, out = set(), []
    for t in titles:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:3]


def wikipedia_lookup(query: str, lang: str = "tr") -> Optional[tuple[str, str]]:
    best, best_score = None, 0.0
    for title in _wiki_candidates(query, lang):
        try:
            s = requests.get(
                f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(title)}",
                headers=HEADERS,
                timeout=TIMEOUT,
            )
            data = s.json()
            extract = (data.get("extract") or "").strip()
            if len(extract) < 40:
                continue
            score = _relevance_score(query, title, extract)
            if score <= 0:
                continue
            url = (
                data.get("content_urls", {}).get("desktop", {}).get("page", "")
                or f"https://{lang}.wikipedia.org/wiki/{quote(title)}"
            )
            if score > best_score:
                best_score, best = score, (extract, url)
        except Exception:
            continue
    return best


def duckduckgo_lookup(query: str) -> Optional[tuple[str, str]]:
    """DuckDuckGo Instant Answer API (free, keyless)."""
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


def ddg_web_search(query: str) -> Optional[tuple[str, str]]:
    """DuckDuckGo HTML web search — snippets from real search results.

    GET is bot-challenged (HTTP 202); the POST form endpoint works.
    """
    try:
        r = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        html = r.text
        links = re.findall(r'class="result__a"[^>]+href="([^"]+)"', html)
        snippets = re.findall(
            r'class="result__snippet"[^>]*>(.*?)</a>', html, flags=re.S
        )
        texts = []
        for sn in snippets[:3]:
            t = _strip_html(sn)
            if len(t) > 30:
                texts.append(t)
        if not texts:
            return None
        answer = "\n\n".join(texts)[:1000]
        url = ""
        if links:
            url = links[0]
            m = re.search(r"uddg=([^&]+)", url)
            if m:
                from urllib.parse import unquote
                url = unquote(m.group(1))
            if url.startswith("//"):
                url = "https:" + url
        return answer, url
    except Exception:
        return None


def stackoverflow_lookup(query: str) -> Optional[tuple[str, str]]:
    """Stack Overflow accepted answers (free API quota, keyless)."""
    try:
        r = requests.get(
            "https://api.stackexchange.com/2.3/search/advanced",
            params={
                "order": "desc",
                "sort": "relevance",
                "q": query,
                "site": "stackoverflow",
                "accepted": "True",
                "pagesize": 1,
            },
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        items = r.json().get("items", [])
        if not items:
            return None
        item = items[0]
        answer_id = item.get("accepted_answer_id")
        if not answer_id:
            return None
        a = requests.get(
            f"https://api.stackexchange.com/2.3/answers/{answer_id}",
            params={"site": "stackoverflow", "filter": "withbody"},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        answers = a.json().get("items", [])
        if not answers:
            return None
        body = _strip_html(answers[0].get("body", ""))[:900]
        if len(body) < 40:
            return None
        title = _strip_html(item.get("title", ""))
        return f"**{title}**\n\n{body}", item.get("link", "")
    except Exception:
        return None


CODE_HINT = re.compile(
    r"(python|javascript|js|java|c\+\+|hata|error|exception|kod|modul|kutuphane|"
    r"library|install|pip|npm|import|function|fonksiyon|framework|api|sql|regex)"
)


def research(question: str) -> Optional[dict]:
    """Query all free sources in parallel; pick the best answer, list extras."""
    from concurrent.futures import ThreadPoolExecutor

    query = _clean_query(question)
    code_hint = bool(CODE_HINT.search(_norm(question)))

    tasks: dict = {
        "wiki_tr": lambda: wikipedia_lookup(query, "tr"),
        "wiki_en": lambda: wikipedia_lookup(query, "en"),
        "ddg": lambda: duckduckgo_lookup(query),
        "ddg_web": lambda: ddg_web_search(query),
    }
    if code_hint:
        tasks["so"] = lambda: stackoverflow_lookup(query)

    results: dict = {}
    with ThreadPoolExecutor(max_workers=len(tasks)) as ex:
        futures = {name: ex.submit(fn) for name, fn in tasks.items()}
        for name, fut in futures.items():
            try:
                results[name] = fut.result(timeout=7)
            except Exception:
                results[name] = None

    providers = {
        "so": "Stack Overflow",
        "wiki_tr": "Wikipedia (TR)",
        "wiki_en": "Wikipedia (EN)",
        "ddg": "DuckDuckGo",
        "ddg_web": "Web araması",
    }
    order = ["so", "wiki_tr", "wiki_en", "ddg", "ddg_web"] if code_hint else \
            ["wiki_tr", "wiki_en", "ddg", "ddg_web", "so"]

    primary_name = next((n for n in order if results.get(n)), None)
    if not primary_name:
        return None

    answer, url = results[primary_name]
    if len(answer) > 1200:
        cut = answer[:1200]
        answer = cut[: cut.rfind(".") + 1] or cut

    # ek kaynak linkleri (farklı URL'ler)
    extras = []
    for name in order:
        if name == primary_name or not results.get(name):
            continue
        _, extra_url = results[name]
        if extra_url and extra_url != url and extra_url not in extras:
            extras.append(extra_url)
        if len(extras) >= 2:
            break
    if extras:
        answer += "\n\n📚 Diğer kaynaklar:\n" + "\n".join(f"• {u}" for u in extras)

    return {"answer": answer, "url": url, "provider": providers[primary_name]}


learned = LearnedStore()
