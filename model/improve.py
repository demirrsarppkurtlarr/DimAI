"""DimAI self-improvement loop — retrieve, evaluate, reflect, queue, promote.

Reuses LearnedStore for durable knowledge. Episodes + learning queue persist
to local JSON (always) and optionally to Supabase tables when available.
Does not replace brain/web_research; wraps the chat lifecycle.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Optional

import requests

ROOT = Path(__file__).resolve().parents[1]
EPISODES_PATH = ROOT / "data" / "episodes.json"
QUEUE_PATH = ROOT / "data" / "learning_queue.json"
PATTERNS_PATH = ROOT / "data" / "error_patterns.json"

SUPABASE_URL = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY") or ""
EPISODES_TABLE = os.environ.get("DIMAI_EPISODES_TABLE", "episodes")
QUEUE_TABLE = os.environ.get("DIMAI_QUEUE_TABLE", "learning_queue")

# Promotion / filter thresholds
PROMOTE_MIN = float(os.environ.get("DIMAI_PROMOTE_MIN", "0.68"))
RETRIEVE_MIN = float(os.environ.get("DIMAI_RETRIEVE_MIN", "0.72"))
MAX_EPISODES = 1500
MAX_QUEUE = 200

FAIL_MARKERS = (
    "tam anlayamadim",
    "tam anlayamadım",
    "sunlari deneyebilirsin",
    "şunları deneyebilirsin",
    "net bir sonuc",
    "net bir sonuç",
    "bir hata olustu",
    "bir hata oluştu",
)

JUNK_MARKERS = (
    "provided to youtube",
    "released on:",
    "cookie",
    "subscribe",
    "diğer muhtemel",
)


def _norm(text: str) -> str:
    text = (text or "").lower()
    text = text.translate(str.maketrans("çğıöşü", "cgiosu"))
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _keywords(text: str) -> set[str]:
    stop = {
        "nedir", "ne", "nasil", "kim", "kimdir", "bir", "ve", "ile", "icin",
        "the", "what", "is", "who", "mi", "mu", "ya", "de", "da", "bana",
        "peki", "bu", "o", "su", "neden", "niye", "hakkinda",
    }
    return {w for w in _norm(text).split() if len(w) > 2 and w not in stop}


def _stems(words: set[str]) -> set[str]:
    return {w[: min(len(w), 5)] for w in words}


def _sb_headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


def _overlap(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    sa, sb = _stems(a), _stems(b)
    return len(sa & sb) / max(len(sa), len(sb))


def _topic_coverage(question: str, answer: str) -> float:
    """Keyword overlap + compound tolerance (karadelik ≈ kara delik)."""
    q_kw = _keywords(question)
    if not q_kw:
        return 0.4
    an = _norm(answer)
    a_kw = _keywords(answer)
    compact = an.replace(" ", "")
    hits = 0
    for w in q_kw:
        stem = w[: min(len(w), 5)]
        if w in a_kw or stem in _stems(a_kw) or stem in compact or w in an:
            hits += 1
    return hits / len(q_kw)


class SelfImprove:
    """Self-improvement engine wired into the chat lifecycle."""

    def __init__(self, learned_store) -> None:
        self.learned = learned_store
        self._lock = threading.Lock()
        self.configured = bool(SUPABASE_URL and SUPABASE_KEY)
        self.backend = "supabase" if self.configured else "file"
        self.episodes: list[dict] = []
        self.queue: list[dict] = []
        self.error_patterns: list[dict] = []
        self.stats = {
            "episodes": 0,
            "promoted": 0,
            "rejected": 0,
            "retrieved": 0,
            "avg_score": 0.0,
        }
        self._load()

    # -------------------- persistence --------------------

    def _load(self) -> None:
        self.episodes = self._load_json(EPISODES_PATH, [])
        self.queue = self._load_json(QUEUE_PATH, [])
        self.error_patterns = self._load_json(PATTERNS_PATH, [])
        if self.configured:
            try:
                self._load_supabase()
            except Exception:
                self.backend = "file"
        self.stats["episodes"] = len(self.episodes)
        scores = [e.get("overall", 0) for e in self.episodes if e.get("overall") is not None]
        if scores:
            self.stats["avg_score"] = round(sum(scores) / len(scores), 3)

    @staticmethod
    def _load_json(path: Path, default):
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return default
        return default

    def _save_json(self, path: Path, data) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    def _load_supabase(self) -> None:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/{EPISODES_TABLE}",
            params={"select": "*", "order": "id.desc", "limit": "500"},
            headers=_sb_headers(),
            timeout=8,
        )
        if r.status_code == 200:
            rows = list(reversed(r.json()))
            if rows:
                # merge: prefer remote if richer
                self.episodes = rows[-MAX_EPISODES:]
                self.backend = "supabase"
        r2 = requests.get(
            f"{SUPABASE_URL}/rest/v1/{QUEUE_TABLE}",
            params={"select": "*", "status": "eq.pending", "order": "id.asc", "limit": "100"},
            headers=_sb_headers(),
            timeout=8,
        )
        if r2.status_code == 200:
            self.queue = r2.json()

    def _persist_episode_remote(self, ep: dict) -> None:
        if not self.configured:
            return
        try:
            payload = {
                "q": ep["q"],
                "a": ep["a"][:3000],
                "source": ep.get("source", ""),
                "accuracy": ep.get("accuracy"),
                "quality": ep.get("quality"),
                "completeness": ep.get("completeness"),
                "overall": ep.get("overall"),
                "success": ep.get("success"),
                "failure_reason": ep.get("failure_reason", ""),
                "reflection": ep.get("reflection", {}),
                "kw": ep.get("kw", []),
            }
            r = requests.post(
                f"{SUPABASE_URL}/rest/v1/{EPISODES_TABLE}",
                headers={**_sb_headers(), "Prefer": "return=minimal"},
                json=payload,
                timeout=8,
            )
            if r.status_code < 300:
                self.backend = "supabase"
        except Exception:
            self.backend = "file"

    def _persist_queue_remote(self, item: dict) -> None:
        if not self.configured:
            return
        try:
            requests.post(
                f"{SUPABASE_URL}/rest/v1/{QUEUE_TABLE}",
                headers={**_sb_headers(), "Prefer": "return=minimal"},
                json={
                    "q": item["q"],
                    "a": item["a"][:3000],
                    "url": item.get("url", ""),
                    "overall": item.get("overall"),
                    "status": item.get("status", "pending"),
                    "kw": item.get("kw", []),
                    "reflection": item.get("reflection", {}),
                },
                timeout=8,
            )
        except Exception:
            pass

    # -------------------- 3. Knowledge Retrieval --------------------

    def retrieve(self, question: str) -> Optional[dict]:
        """Past successful solutions first — before generating a new answer."""
        kw = _keywords(question)
        if not kw:
            return None

        # 1) High-quality learned memory (existing store)
        hit = self.learned.lookup(question)
        if hit:
            # prefer if it has a stored quality, else treat as decent
            qscore = float(hit.get("quality") or 0.75)
            if qscore >= RETRIEVE_MIN * 0.9:
                self.stats["retrieved"] += 1
                return {
                    "reply": hit["a"],
                    "url": hit.get("url", ""),
                    "source": "learned",
                    "overall": qscore,
                    "from": "learned_store",
                }

        # 2) Successful past episodes with strong keyword overlap
        best, best_score = None, 0.0
        with self._lock:
            for ep in reversed(self.episodes[-800:]):
                if not ep.get("success"):
                    continue
                if float(ep.get("overall") or 0) < RETRIEVE_MIN:
                    continue
                ov = _overlap(kw, set(ep.get("kw") or _keywords(ep.get("q", ""))))
                # boost exact-ish question match
                q_sim = _overlap(kw, _keywords(ep.get("q", "")))
                score = 0.55 * ov + 0.45 * q_sim
                if score > best_score:
                    best, best_score = ep, score
        if best and best_score >= 0.70:
            self.stats["retrieved"] += 1
            return {
                "reply": best["a"],
                "url": best.get("url", ""),
                "source": "memory",
                "overall": best.get("overall"),
                "from": "episode",
                "match": round(best_score, 3),
            }
        return None

    # -------------------- 4. Self Evaluation --------------------

    def evaluate(self, question: str, answer: str, source: str, meta: Optional[dict] = None) -> dict:
        """Score accuracy, quality, completeness → overall + success flag."""
        meta = meta or {}
        ans = (answer or "").strip()
        qn = _norm(question)
        an = _norm(ans)

        # --- accuracy: question keywords covered by answer ---
        coverage = _topic_coverage(question, ans)
        source_boost = {
            "kb": 0.15, "learned": 0.12, "memory": 0.12, "web": 0.10,
            "math": 0.2, "chat": 0.05, "fallback": -0.25,
        }.get(source, 0.0)
        accuracy = max(0.0, min(1.0, coverage + source_boost))

        # --- quality: structure / junk / emptiness ---
        quality = 0.5
        if len(ans) >= 80:
            quality += 0.15
        if len(ans) >= 200:
            quality += 0.1
        if "```" in ans or "def " in ans or "class " in ans:
            quality += 0.15  # code-bearing answers
        if any(m in an for m in JUNK_MARKERS):
            quality -= 0.35
        if ans.count("http") > 5:
            quality -= 0.1
        if source in ("kb", "learned", "memory"):
            quality += 0.1
        quality = max(0.0, min(1.0, quality))

        # --- completeness ---
        completeness = 0.45
        if len(ans) < 40:
            completeness = 0.15
        elif len(ans) < 100:
            completeness = 0.4
        else:
            completeness = 0.7
        if any(m in an for m in FAIL_MARKERS):
            completeness = min(completeness, 0.2)
            accuracy = min(accuracy, 0.25)
            quality = min(quality, 0.3)
        if source == "fallback":
            completeness = min(completeness, 0.2)
            accuracy = min(accuracy, 0.2)
        # code intent — reply veya ayrı code alanında
        has_code = (
            "```" in ans or "def " in ans or "function " in ans
            or "class " in ans or bool((meta or {}).get("code"))
        )
        if any(w in qn for w in ("kod", "yaz", "ornek", "code", "write")):
            if has_code:
                completeness = max(completeness, 0.85)
                quality = max(quality, 0.7)
            else:
                completeness = min(completeness, 0.45)

        overall = round(0.4 * accuracy + 0.3 * quality + 0.3 * completeness, 3)
        success = (
            overall >= 0.55
            and source not in ("fallback",)
            and not any(m in an for m in FAIL_MARKERS)
        )

        failure_reason = ""
        if not success:
            if any(m in an for m in FAIL_MARKERS) or source == "fallback":
                failure_reason = "cevap_uretilemedi"
            elif accuracy < 0.35:
                failure_reason = "konu_disi_veya_alakasiz"
            elif completeness < 0.4:
                failure_reason = "eksik_cevap"
            elif quality < 0.4:
                failure_reason = "dusuk_kalite"
            else:
                failure_reason = "esik_alti"

        return {
            "accuracy": round(accuracy, 3),
            "quality": round(quality, 3),
            "completeness": round(completeness, 3),
            "overall": overall,
            "success": success,
            "failure_reason": failure_reason,
        }

    # -------------------- 1. Reflection System --------------------

    def reflect(self, question: str, answer: str, evaluation: dict, repeated: list) -> dict:
        """AI asks itself: where wrong, how better, what to change next time."""
        reason = evaluation.get("failure_reason") or ""
        success = evaluation.get("success")

        if success:
            where = "Belirgin bir hata yok; cevap eşiği geçti."
            better = "Benzer sorularda bu çözümü doğrudan memory'den sun."
            next_time = "Başarılı kalıbı koru; gereksiz web araması yapma."
        else:
            where_map = {
                "cevap_uretilemedi": "Soruyu çözemedim / fallback'e düştüm.",
                "konu_disi_veya_alakasiz": "Cevap sorunun anahtar kelimeleriyle örtüşmedi.",
                "eksik_cevap": "Cevap çok kısa veya görev tamamlanmadı.",
                "dusuk_kalite": "Cevapta gürültü / düşük kalite işaretleri var.",
                "esik_alti": "Genel skor yeterince yüksek değil.",
            }
            where = where_map.get(reason, "Beklenmeyen bir zayıflık.")
            better = (
                "Önce geçmiş başarılı çözümleri ara; yoksa konuyu netleştirip "
                "daha odaklı araştırma yap."
            )
            next_time = (
                f"'{reason or 'genel'}' tipindeki hatalarda önce memory retrieval, "
                "sonra gerekirse web; düşük kaliteli sonucu kaydetme."
            )

        if repeated:
            patterns = ", ".join(sorted({r.get("failure_reason", "?") for r in repeated}))
            next_time += f" Tekrarlayan hata deseni tespit edildi: {patterns}."

        return {
            "where_wrong": where,
            "how_better": better,
            "next_change": next_time,
            "repeated_error": bool(repeated),
        }

    # -------------------- repeated errors --------------------

    def detect_repeated_errors(self, question: str, evaluation: dict) -> list:
        if evaluation.get("success"):
            return []
        reason = evaluation.get("failure_reason") or ""
        kw = _keywords(question)
        found = []
        with self._lock:
            for ep in reversed(self.episodes[-300:]):
                if ep.get("success"):
                    continue
                if (ep.get("failure_reason") or "") != reason:
                    continue
                if _overlap(kw, set(ep.get("kw") or [])) >= 0.5:
                    found.append(ep)
                if len(found) >= 3:
                    break
        if len(found) >= 2:
            # record pattern
            pattern = {
                "failure_reason": reason,
                "kw": sorted(kw)[:8],
                "count": len(found) + 1,
                "t": time.time(),
                "sample_q": question[:200],
            }
            with self._lock:
                self.error_patterns.append(pattern)
                self.error_patterns = self.error_patterns[-100:]
                try:
                    self._save_json(PATTERNS_PATH, self.error_patterns)
                except Exception:
                    pass
        return found

    # -------------------- log + 2. Learning Queue --------------------

    def log_episode(
        self,
        question: str,
        answer: str,
        source: str,
        evaluation: dict,
        reflection: dict,
        url: str = "",
    ) -> dict:
        ep = {
            "q": question.strip()[:300],
            "a": (answer or "")[:3000],
            "url": url or "",
            "source": source,
            "kw": sorted(_keywords(question)),
            "accuracy": evaluation.get("accuracy"),
            "quality": evaluation.get("quality"),
            "completeness": evaluation.get("completeness"),
            "overall": evaluation.get("overall"),
            "success": bool(evaluation.get("success")),
            "failure_reason": evaluation.get("failure_reason", ""),
            "reflection": reflection,
            "t": time.time(),
        }
        with self._lock:
            self.episodes.append(ep)
            if len(self.episodes) > MAX_EPISODES:
                self.episodes = self.episodes[-MAX_EPISODES:]
            self.stats["episodes"] = len(self.episodes)
            scores = [e.get("overall", 0) or 0 for e in self.episodes[-100:]]
            if scores:
                self.stats["avg_score"] = round(sum(scores) / len(scores), 3)
            try:
                self._save_json(EPISODES_PATH, self.episodes[-500:])
            except Exception:
                pass
        # remote async-ish (same thread but swallow errors)
        self._persist_episode_remote(ep)
        return ep

    def enqueue(self, question: str, answer: str, evaluation: dict, reflection: dict, url: str = "") -> None:
        """Queue candidate knowledge — do NOT write to memory yet."""
        if not evaluation.get("success"):
            return
        if float(evaluation.get("overall") or 0) < PROMOTE_MIN * 0.9:
            return
        # skip trivial chat
        if evaluation.get("source") == "chat" and len(answer or "") < 80:
            return
        item = {
            "q": question.strip()[:300],
            "a": (answer or "")[:3000],
            "url": url or "",
            "kw": sorted(_keywords(question)),
            "overall": evaluation.get("overall"),
            "quality": evaluation.get("quality"),
            "reflection": reflection,
            "status": "pending",
            "t": time.time(),
        }
        with self._lock:
            # dedupe pending queue
            qn = _norm(item["q"])
            self.queue = [x for x in self.queue if _norm(x.get("q", "")) != qn]
            self.queue.append(item)
            if len(self.queue) > MAX_QUEUE:
                self.queue = self.queue[-MAX_QUEUE:]
            try:
                self._save_json(QUEUE_PATH, self.queue)
            except Exception:
                pass
        self._persist_queue_remote(item)

    def _validate_queue_item(self, item: dict) -> tuple[bool, str]:
        """Learning Queue gate: verify before promoting to memory."""
        a = (item.get("a") or "").strip()
        q = (item.get("q") or "").strip()
        if len(a) < 60:
            return False, "too_short"
        if len(a) > 3500:
            return False, "too_long"
        if any(m in _norm(a) for m in set(FAIL_MARKERS) | set(JUNK_MARKERS)):
            return False, "junk_or_fail"
        if float(item.get("overall") or 0) < PROMOTE_MIN:
            return False, "score_low"
        # must overlap with question
        if _topic_coverage(q, a) < 0.25 and "```" not in a:
            return False, "low_relevance"
        # already in learned?
        existing = self.learned.lookup(q)
        if existing and _norm(existing.get("a", ""))[:120] == _norm(a)[:120]:
            return False, "duplicate"
        return True, "ok"

    def process_queue(self, limit: int = 8) -> dict:
        """Validate pending items; promote winners into LearnedStore."""
        promoted = rejected = 0
        with self._lock:
            pending = [x for x in self.queue if x.get("status", "pending") == "pending"]
        for item in pending[:limit]:
            ok, why = self._validate_queue_item(item)
            if ok:
                try:
                    # quality-aware add (LearnedStore accepts optional quality)
                    self.learned.add(
                        item["q"],
                        item["a"],
                        item.get("url", ""),
                        quality=float(item.get("overall") or 0),
                    )
                    item["status"] = "promoted"
                    promoted += 1
                    self.stats["promoted"] += 1
                except TypeError:
                    # older signature without quality=
                    self.learned.add(item["q"], item["a"], item.get("url", ""))
                    item["status"] = "promoted"
                    promoted += 1
                    self.stats["promoted"] += 1
                except Exception:
                    item["status"] = "error"
                    rejected += 1
            else:
                item["status"] = f"rejected:{why}"
                rejected += 1
                self.stats["rejected"] += 1
        with self._lock:
            # keep pending + recent resolved
            self.queue = [
                x for x in self.queue
                if x.get("status") == "pending" or x.get("t", 0) > time.time() - 86400
            ][-MAX_QUEUE:]
            try:
                self._save_json(QUEUE_PATH, self.queue)
            except Exception:
                pass
        return {"promoted": promoted, "rejected": rejected}

    # -------------------- 5. Continuous Improvement orchestrator --------------------

    def after_chat(self, question: str, result: dict) -> dict:
        """Run evaluate → reflect → log → enqueue → process queue.

        Returns enrichment fields safe to merge into the API response.
        Designed to be fast (no blocking web I/O beyond optional short posts).
        """
        answer = result.get("reply") or ""
        if result.get("code"):
            answer = f"{answer}\n```\n{result['code']}\n```"
        source = result.get("source") or "unknown"
        url = result.get("url") or ""

        evaluation = self.evaluate(question, answer, source, result)
        repeated = self.detect_repeated_errors(question, evaluation)
        reflection = self.reflect(question, answer, evaluation, repeated)
        self.log_episode(question, answer, source, evaluation, reflection, url=url)

        # Only queue NEW durable knowledge from the web (KB already permanent;
        # learned/memory already in store — avoid duplicates).
        if evaluation["success"] and source == "web" and len(answer) >= 60:
            evaluation_for_q = dict(evaluation)
            evaluation_for_q["source"] = source
            self.enqueue(question, answer, evaluation_for_q, reflection, url=url)

        # drain a few queue items each turn (continuous improvement)
        queue_result = self.process_queue(limit=5)

        return {
            "evaluation": {
                "accuracy": evaluation["accuracy"],
                "quality": evaluation["quality"],
                "completeness": evaluation["completeness"],
                "overall": evaluation["overall"],
                "success": evaluation["success"],
            },
            "reflection": reflection,
            "improve": {
                "promoted": queue_result["promoted"],
                "rejected": queue_result["rejected"],
                "repeated_error": bool(repeated),
            },
        }

    def status(self) -> dict:
        with self._lock:
            pending = sum(1 for x in self.queue if x.get("status", "pending") == "pending")
            recent = self.episodes[-20:]
            success_rate = (
                sum(1 for e in recent if e.get("success")) / len(recent) if recent else 0.0
            )
            top_failures = Counter(
                e.get("failure_reason") for e in self.episodes[-100:] if not e.get("success")
            ).most_common(5)
        return {
            "backend": self.backend,
            "episodes": self.stats["episodes"],
            "avg_score": self.stats["avg_score"],
            "promoted": self.stats["promoted"],
            "rejected": self.stats["rejected"],
            "retrieved": self.stats["retrieved"],
            "queue_pending": pending,
            "recent_success_rate": round(success_rate, 3),
            "top_failures": [{"reason": r or "?", "n": n} for r, n in top_failures],
            "error_patterns": len(self.error_patterns),
        }


# singleton wired in server.py after learned is imported
improve: Optional[SelfImprove] = None


def init_improve(learned_store) -> SelfImprove:
    global improve
    improve = SelfImprove(learned_store)
    return improve
