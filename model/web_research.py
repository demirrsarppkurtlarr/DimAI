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

HEADERS = {"User-Agent": "DimAI/1.0 (https://dimai-vlw9.onrender.com; learning assistant)"}
TIMEOUT = float(os.environ.get("DIMAI_WEB_TIMEOUT", "5"))

STOPWORDS = {
    "nedir", "ne", "nasil", "kim", "kimdir", "hakkinda", "bilgi", "ver",
    "anlat", "bana", "bir", "the", "what", "is", "who", "ile", "mi", "mu",
    "midir", "acaba", "ki", "ya", "ve", "de", "da", "icin", "yaz",
    "neresi", "nerede", "nerededir", "kac", "kactir", "kacdir",
    "hangisi", "hangi", "neden", "niye", "zaman", "kadar", "soyle", "bul",
    "peki", "o", "bu", "su", "onun", "bunun",
    # soru fiilleri — arama motorunu kirletiyorlar ("atatürk ne zaman doğdu")
    "dogdu", "oldu", "olmustur", "kuruldu", "yapildi", "basladi", "bitti",
    "gerceklesti", "yasadi", "geldi", "gitti",
}


def _norm(text: str) -> str:
    text = text or ""
    text = text.replace("İ", "i").replace("I", "i").replace("ı", "i")
    text = text.lower()
    text = text.translate(str.maketrans("çğıöşü", "cgiosu"))
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _keywords(text: str) -> set[str]:
    return {w for w in _norm(text).split() if w not in STOPWORDS and len(w) > 1}


def _clean_query(text: str) -> str:
    """Strip question words so search engines get the core topic."""
    n = _norm(text)
    # Hava: "hava nasıl" → RAF gibi yanlış sayfaları engellemek için İngilizce net sorgu
    if "hava" in n.split() or "weather" in n or "sicaklik" in n:
        city = None
        for c in ("istanbul", "ankara", "izmir", "bursa", "antalya", "adana"):
            if c in n:
                city = c
                break
        return f"{city} weather temperature Celsius" if city else "Turkey weather today temperature"
    # Tech disambiguation — mitoloji / yanlış Wikipedia sayfalarını engelle
    tech_map = {
        "zod": "Zod TypeScript validation library",
        "prisma": "Prisma ORM Node.js",
        "prometheus": "Prometheus monitoring software",
        "cors": "CORS Cross-Origin Resource Sharing web",
        "closure": "closure programming JavaScript",
        "useeffect": "React useEffect hook",
        "ci cd": "CI CD continuous integration continuous delivery",
        "cicd": "CI CD continuous integration",
        "tailwind": "Tailwind CSS framework",
        "graphql": "GraphQL API query language",
        "jwt": "JWT JSON Web Token authentication",
        "redis": "Redis in-memory database",
        "kubernetes": "Kubernetes container orchestration",
        "nginx": "Nginx web server",
        "mongodb": "MongoDB NoSQL database",
        "oauth": "OAuth 2.0 authorization",
        "websocket": "WebSocket protocol",
        "nextjs": "Next.js React framework",
        "next js": "Next.js React framework",
    }
    for key, rewrite in tech_map.items():
        if key in n:
            return rewrite
    # "X kim buldu/yarattı"
    if "kim buldu" in n or "kim yaratti" in n or "who invented" in n or "who created" in n:
        topic = re.sub(r"\b(kim buldu|kim yaratti|who invented|who created)\b", " ", n)
        topic = re.sub(r"\s+", " ", topic).strip()
        return f"{topic} inventor creator".strip()
    # başkent
    if "baskent" in n or "capital" in n:
        if "turkiye" in n or "turkey" in n:
            return "Türkiye başkenti Ankara"
    # nüfus
    if "nufus" in n or "population" in n:
        if "istanbul" in n:
            return "İstanbul nüfusu"
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
        payload = {
            "q": entry["q"],
            "kw": entry["kw"],
            "a": entry["a"],
            "url": entry["url"],
        }
        # quality kolonu yoksa geriye uyumlu: önce dener, 400'de kalitesiz tekrarlar
        if entry.get("quality") is not None:
            payload["quality"] = entry["quality"]
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}",
            headers={**_sb_headers(), "Prefer": "return=minimal"},
            json=payload,
            timeout=8,
        )
        if r.status_code >= 400 and "quality" in payload:
            payload.pop("quality", None)
            r = requests.post(
                f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}",
                headers={**_sb_headers(), "Prefer": "return=minimal"},
                json=payload,
                timeout=8,
            )
        r.raise_for_status()

    @staticmethod
    def _clean_answer(text: str) -> str:
        """Eski kayıtlardaki '🔎 Çoklu kaynak…' başlığını ve kaynak listesini sil."""
        if not text:
            return text
        text = re.sub(
            r"^🔎\s*\*?\*?Çoklu kaynak araştırması\*?\*?\s*\([^)]*\)\s*\n+",
            "",
            text.strip(),
            flags=re.I,
        )
        text = re.sub(r"\n*📚\s*\*?\*?Kaynaklar[^\n]*\n(?:•[^\n]*\n?)*", "", text)
        return text.strip()

    def add(self, question: str, answer: str, url: str = "", quality: Optional[float] = None) -> None:
        with self._lock:
            entry = {
                "q": question.strip()[:300],
                "kw": sorted(_keywords(question)),
                "a": self._clean_answer(answer.strip())[:3000],
                "url": url,
                "t": time.time(),
            }
            if quality is not None:
                entry["quality"] = float(quality)
            self._items.append(entry)
            if len(self._items) > 5000:
                self._items = self._items[-5000:]
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

    def seed_from_file(self, path: Path, limit: int = 1500) -> int:
        """Load curated Q&A seed (e.g. Tulu chat) into memory without flooding Supabase."""
        path = Path(path)
        if not path.exists():
            return 0
        try:
            items = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return 0
        added = 0
        with self._lock:
            existing_q = { (it.get("q") or "")[:80].lower() for it in self._items }
            for raw in items[:limit]:
                q = str(raw.get("q") or "").strip()
                a = str(raw.get("a") or "").strip()
                if len(q) < 8 or len(a) < 20:
                    continue
                key = q[:80].lower()
                if key in existing_q:
                    continue
                entry = {
                    "q": q[:300],
                    "kw": sorted(_keywords(q)),
                    "a": self._clean_answer(a)[:3000],
                    "url": str(raw.get("url") or "")[:300],
                    "t": time.time(),
                    "quality": float(raw.get("quality") or 0.8),
                }
                self._items.append(entry)
                existing_q.add(key)
                added += 1
            if len(self._items) > 5000:
                self._items = self._items[-5000:]
            if added and self.backend == "file":
                self._save_file()
        return added

    def lookup(self, question: str) -> Optional[dict]:
        """Match only when the stored entry answers (nearly) the SAME question.

        Keyword stems (first 5 chars, Turkish suffix tolerant) must cover
        both sides; partial topic overlap ("karadelik nedir" vs "karadelik
        nasıl oluşur") triggers fresh research instead of a stale answer.
        """
        kw = _keywords(question)
        if not kw:
            return None
        q_stems = {w[: min(len(w), 5)] for w in kw}
        best, best_score = None, 0.0
        with self._lock:
            for item in self._items:
                item_kw = set(item.get("kw", []))
                if not item_kw:
                    continue
                item_stems = {w[: min(len(w), 5)] for w in item_kw}
                inter = len(q_stems & item_stems)
                if inter == 0:
                    continue
                score = inter / max(len(q_stems), len(item_stems))
                # kaliteli kayıtları hafifçe öne al (self-improvement)
                qboost = 0.05 * float(item.get("quality") or 0)
                score = score + qboost
                if score > best_score:
                    best, best_score = item, score
        if best and best_score >= 0.75:
            return {
                **best,
                "a": self._clean_answer(best.get("a", "")),
            }
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
        # tek kelimelik sorgu mutlaka geçmeli; çok kelimelide yarısı yeterli
        # (Türkçe ekler yüzünden tam eşleşme her zaman mümkün olmuyor)
        if hits == 0 or (len(kws) == 1 and ratio < 1.0) or ratio < 0.5:
            return 0.0
    else:
        ratio = 1.0
    score = ratio
    if qnorm.replace(" ", "") in tns:
        score += 1.0  # tam ifade eşleşmesi
    score += difflib.SequenceMatcher(None, _norm(title), qnorm).ratio() * 0.5
    # sorgu kelimeleri başlıkta geçiyorsa güçlü sinyal (doğru sayfa)
    if kws:
        title_ns = _norm(title).replace(" ", "")
        title_hits = sum(1 for w in kws if w[: min(len(w), 5)] in title_ns)
        score += 0.4 * title_hits / len(kws)
    return score


def wikipedia_lookup(query: str, lang: str = "tr") -> Optional[tuple[str, str]]:
    """Single-request Wikipedia search: 3 candidates with intro extracts.

    generator=search + prop=extracts keeps this to ONE HTTP round-trip, which
    matters on slow hosts (Render free tier) where 5 sequential requests
    would blow the research time budget.
    """
    try:
        r = requests.get(
            f"https://{lang}.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "generator": "search",
                "gsrsearch": query,
                "gsrlimit": 3,
                "prop": "extracts",
                "exintro": 1,
                "explaintext": 1,
                "exchars": 1200,
                "format": "json",
            },
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        pages = (r.json().get("query") or {}).get("pages") or {}
    except Exception:
        return None
    best, best_score = None, 0.0
    for page in pages.values():
        title = page.get("title", "")
        extract = (page.get("extract") or "").strip()
        if len(extract) < 40:
            continue
        score = _relevance_score(query, title, extract)
        if score <= 0:
            continue
        # Wikipedia'nın kendi sıralamasına küçük bonus (1. sonuç en alakalı)
        score += max(0, 3 - int(page.get("index", 3))) * 0.25
        if score > best_score:
            url = f"https://{lang}.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"
            best_score, best = score, (extract, url)
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


def google_news_lookup(query: str) -> Optional[tuple[str, str]]:
    """Google News RSS — güncel haberler (ücretsiz, anahtar gerekmez)."""
    try:
        r = requests.get(
            "https://news.google.com/rss/search",
            params={"q": query, "hl": "tr", "gl": "TR", "ceid": "TR:tr"},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        items = re.findall(r"<item>(.*?)</item>", r.text, flags=re.S)[:4]
        lines, first_url = [], ""
        for it in items:
            tm = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", it, flags=re.S)
            lm = re.search(r"<link>(.*?)</link>", it, flags=re.S)
            if not tm:
                continue
            title = _strip_html(tm.group(1))
            if len(title) < 15:
                continue
            lines.append(f"• {title}")
            if not first_url and lm:
                first_url = lm.group(1).strip()
        if not lines:
            return None
        return "📰 Güncel haberler (Google News):\n" + "\n".join(lines[:3]), first_url
    except Exception:
        return None


def hackernews_lookup(query: str) -> Optional[tuple[str, str]]:
    """Hacker News (Algolia API) — teknik konular için tartışma/makaleler."""
    try:
        r = requests.get(
            "https://hn.algolia.com/api/v1/search",
            params={"query": query, "tags": "story", "hitsPerPage": 3},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        hits = [h for h in r.json().get("hits", []) if h.get("title")]
        lines, first_url = [], ""
        for h in hits[:3]:
            url = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID','')}"
            lines.append(f"• {h['title']}\n  {url}")
            if not first_url:
                first_url = url
        if not lines:
            return None
        return "Bu konuda faydalı kaynaklar (Hacker News):\n" + "\n".join(lines), first_url
    except Exception:
        return None


def wikidata_lookup(query: str) -> Optional[tuple[str, str]]:
    """Wikidata — kısa, yapılandırılmış tanımlar (son çare)."""
    try:
        r = requests.get(
            "https://www.wikidata.org/w/api.php",
            params={
                "action": "wbsearchentities",
                "search": query,
                "language": "tr",
                "uselang": "tr",
                "format": "json",
                "limit": 1,
            },
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        hits = r.json().get("search", [])
        if not hits:
            return None
        h = hits[0]
        label = h.get("label", "")
        desc = h.get("description", "")
        if not desc or len(desc) < 15:
            return None
        # etiket sorguyla gerçekten benzer olmalı
        sim = difflib.SequenceMatcher(None, _norm(label), _norm(query)).ratio()
        if sim < 0.6:
            return None
        url = "https:" + h["url"] if h.get("url", "").startswith("//") else h.get("url", "")
        return f"**{label}**: {desc}", url
    except Exception:
        return None


CODE_HINT = re.compile(
    r"(python|javascript|js|java|c\+\+|hata|error|exception|kod|modul|kutuphane|"
    r"library|install|pip|npm|import|function|fonksiyon|framework|api|sql|regex)"
)

NEWS_HINT = re.compile(
    r"(haber|son dakika|guncel|bugun|dun\b|20[2-9]\d|kim kazandi|"
    r"sonuc|skor|secim|fiyat|dolar|euro|deprem|maci|transfer)"
)


PROVIDERS = {
    "so": "Stack Overflow",
    "wiki_tr": "Wikipedia (TR)",
    "wiki_en": "Wikipedia (EN)",
    "ddg": "DuckDuckGo",
    "ddg_web": "Web araması",
    "ddg_raw": "Web araması (tam metin)",
    "gnews": "Google News",
    "hn": "Hacker News",
    "wikidata": "Wikidata",
}


def _gather(question: str, deep: bool = False) -> tuple[str, bool, bool, dict]:
    """Run all free sources in parallel; returns (query, code, news, results)."""
    from concurrent.futures import ThreadPoolExecutor

    query = _clean_query(question)
    qnorm = _norm(question)
    code_hint = bool(CODE_HINT.search(qnorm))
    news_hint = bool(NEWS_HINT.search(qnorm))

    tasks: dict = {
        "wiki_tr": lambda: wikipedia_lookup(query, "tr"),
        "wiki_en": lambda: wikipedia_lookup(query, "en"),
        "ddg": lambda: duckduckgo_lookup(query),
        "ddg_web": lambda: ddg_web_search(query),
        "gnews": lambda: google_news_lookup(query),
        "wikidata": lambda: wikidata_lookup(query),
    }
    if deep and query != question.strip().rstrip("?!."):
        # kullanıcının yazdığının AYNISI ile de ara
        tasks["ddg_raw"] = lambda: ddg_web_search(question.strip())
    if code_hint or deep:
        tasks["so"] = lambda: stackoverflow_lookup(query)
        tasks["hn"] = lambda: hackernews_lookup(query)

    results: dict = {}
    with ThreadPoolExecutor(max_workers=len(tasks)) as ex:
        futures = {name: ex.submit(fn) for name, fn in tasks.items()}
        for name, fut in futures.items():
            try:
                results[name] = fut.result(timeout=TIMEOUT + 4)
            except Exception:
                results[name] = None
    status = " ".join(f"{n}={'ok' if results.get(n) else '-'}" for n in tasks)
    print(f"[research] q={query!r} deep={deep} news={news_hint} code={code_hint} {status}", flush=True)
    return query, code_hint, news_hint, results


def research(question: str) -> Optional[dict]:
    """Query all free sources in parallel; pick the best answer, list extras."""
    query, code_hint, news_hint, results = _gather(question)

    providers = PROVIDERS
    # Google News yalnızca haber sorularında ana cevap olur; bilgi sorularında
    # sadece ek kaynak linki olarak kullanılır (haber spam'ini önler).
    if code_hint:
        order = ["so", "wiki_tr", "wiki_en", "ddg", "ddg_web", "hn", "wikidata"]
    elif news_hint:
        order = ["gnews", "wiki_tr", "wiki_en", "ddg", "ddg_web", "wikidata"]
    else:
        order = ["wiki_tr", "wiki_en", "ddg", "ddg_web", "wikidata"]

    primary_name = next((n for n in order if results.get(n)), None)
    if not primary_name:
        return None

    answer, url = results[primary_name]
    if len(answer) > 1200:
        cut = answer[:1200]
        answer = cut[: cut.rfind(".") + 1] or cut

    # ek kaynak linkleri (farklı URL'ler) — gnews/hn burada her zaman taranır
    extras = []
    extra_scan = order + [n for n in ("gnews", "hn") if n not in order]
    for name in extra_scan:
        if name == primary_name or not results.get(name):
            continue
        _, extra_url = results[name]
        if extra_url and extra_url != url and extra_url not in extras:
            extras.append(extra_url)
        if len(extras) >= 3:
            break
    if extras:
        answer += "\n\n📚 Diğer kaynaklar:\n" + "\n".join(f"• {u}" for u in extras)

    return {"answer": answer, "url": url, "provider": providers[primary_name]}


def _split_sentences(text: str) -> list[str]:
    text = re.sub(r"📰[^\n]*|📚[^\n]*|^•.*$", " ", text, flags=re.M)
    parts = re.split(r"(?<=[.!?])\s+", text)
    junk = re.compile(
        r"(provided to youtube|released on:|composer:|lyricist:|"
        r"diğer muhtemel|izle 1080|℗|pasaj|subscribe|cookie)",
        re.I,
    )
    out = []
    for p in parts:
        s = p.strip()
        if not (40 <= len(s) <= 400):
            continue
        if junk.search(s):
            continue
        out.append(s)
    return out


def research_deep(question: str) -> Optional[dict]:
    """Search MANY sources (5+) and synthesize a combined answer.

    Extractive synthesis: sentences from all successful sources are scored
    by query keyword coverage and cross-source agreement; the best distinct
    sentences form the answer, with every source listed.
    """
    query, code_hint, news_hint, results = _gather(question, deep=True)

    found = [(name, r[0], r[1]) for name, r in results.items() if r]
    if not found:
        return None

    # haber başlıkları/link listeleri sentez cümlesi olamaz
    text_sources = [
        (name, ans, url) for name, ans, url in found if name not in ("gnews", "hn")
    ]
    if len(text_sources) < 2:
        # sentezlenecek kadar metin yok → normal en-iyi-kaynak cevabı
        return research(question)

    qnorm = _norm(question)
    q_stems = {w[: min(len(w), 5)] for w in qnorm.split() if len(w) >= 3 and w not in STOPWORDS}

    # cümleleri topla ve puanla
    cands: list[dict] = []
    for idx, (name, ans, url) in enumerate(text_sources):
        for pos, sent in enumerate(_split_sentences(ans)):
            sns = _norm(sent).replace(" ", "")
            cover = (
                sum(1 for s in q_stems if s in sns) / len(q_stems) if q_stems else 0.5
            )
            cands.append({
                "sent": sent, "src": idx, "pos": pos,
                "score": cover + (0.3 if pos == 0 else 0.0),
            })
    # kaynaklar arası doğrulama: benzer cümle başka kaynakta da varsa güçlü sinyal
    for i, a in enumerate(cands):
        for b in cands[i + 1:]:
            if a["src"] != b["src"] and difflib.SequenceMatcher(
                None, _norm(a["sent"])[:200], _norm(b["sent"])[:200]
            ).ratio() > 0.6:
                a["score"] += 0.4
                b["score"] += 0.4

    picked: list[dict] = []
    for c in sorted(cands, key=lambda c: -c["score"]):
        if len(picked) >= 6:
            break
        if any(
            difflib.SequenceMatcher(None, _norm(c["sent"])[:200], _norm(p["sent"])[:200]).ratio() > 0.7
            for p in picked
        ):
            continue  # tekrar eden bilgiyi atla
        picked.append(c)
    if not picked:
        return research(question)
    picked.sort(key=lambda c: (c["src"], c["pos"]))

    summary = " ".join(c["sent"] for c in picked)[:1500]

    seen_urls: list[str] = []
    for name, _ans, url in found:
        if url and url not in seen_urls:
            seen_urls.append(url)
    # Başlık yok — sadece özet; kaynak linkleri UI'da "Kaynağı aç" ile gelir
    primary_url = text_sources[0][2] or (seen_urls[0] if seen_urls else "")
    return {
        "answer": summary,
        "url": primary_url,
        "provider": "web",
        "sources": seen_urls[:6],
    }


learned = LearnedStore()
