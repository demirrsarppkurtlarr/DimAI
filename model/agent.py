"""DimAI Agent — decision, planning, tool policy, context packing.

Central router used by brain/server. Does not call the web itself; it only
decides WHICH tool path is allowed. Keeps DimAI from researching greetings,
writing essays instead of code, or dropping conversation context.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional


def _norm(text: str) -> str:
    text = (text or "").lower()
    text = text.translate(str.maketrans("çğıöşü", "cgiosu"))
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^a-z0-9+\-*/=<>.,!?'\"\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# -------------------- intent vocabulary --------------------

Intent = str  # chat | code | research | followup | personal | math | refuse | analyze | help

CHAT_WORDS = {
    "merhaba", "selam", "hello", "hi", "hey", "slm", "sa",
    "nasilsin", "naber", "tesekkur", "sagol", "thanks", "eyvallah",
    "gorusuruz", "bye", "gunaydin", "iyi geceler", "iyi aksamlar",
}

CODE_STRONG = {
    "kod", "kodu", "code", "script", "program", "fonksiyon", "function",
    "class", "algoritma", "snippet",
}
CODE_WRITE = {"yaz", "write", "olustur", "uret", "generate"}
CODE_EXAMPLE = {"ornek", "ornegi", "example", "goster", "show", "sample"}
CODE_LANGS = {"python", "js", "javascript", "sql", "html", "css", "java", "cpp", "typescript"}

RESEARCH_EXPLICIT = (
    "nedir", "kimdir", "ne demek", "hakkinda", "tarihi",
    "ne zaman", "nerede", "neresi", "neden", "niye",
    "nasil calisir", "nasil olusur", "ozellikleri", "anlami",
    "who is", "what is", "what are", "when was", "where is",
    "arastir", "araştir", "googlela", "internetten bak", "kaynak bul",
)

REFUSE_SEARCH = (
    "arastirma yapma", "arama yapma", "aramasin", "arastirmasin",
    "internetten bakma", "internete bakma", "dont search", "no search",
)

PERSONAL = (
    "ben kimim", "kimim ben", "ben kim", "who am i",
    "beni taniyor", "beni biliyor", "beni hatirliyor",
)

ANALYZE = (
    "analiz et", "incele", "gozden gecir", "review", "debug",
    "hata bul", "neden calismiyor", "acikla su kodu", "bu kod",
)

FOLLOWUP_HINTS = {
    "peki", "onu", "bunu", "sunu", "devam", "baska", "daha", "tekrar",
    "detay", "acikla", "anlatsana", "onun", "bunun", "ya", "ama",
    "sonra", "bahsettigin", "dedigin",
}


@dataclass
class Decision:
    intent: Intent
    allow_web: bool
    allow_memory: bool
    allow_kb: bool
    tools: list[str] = field(default_factory=list)
    plan: list[str] = field(default_factory=list)
    reason: str = ""
    context_summary: str = ""
    research_query: str = ""
    topic: list[str] = field(default_factory=list)


class Agent:
    """Decide intent + tool policy before any answer is produced."""

    def decide(self, message: str, history: Optional[list] = None) -> Decision:
        history = history or []
        raw = (message or "").strip()
        text = _norm(raw)
        words = set(text.split())
        ctx = self.pack_context(history)
        topic = ctx.get("topic") or []

        # --- refuse / personal ---
        if any(p in text for p in REFUSE_SEARCH):
            return Decision(
                intent="refuse", allow_web=False, allow_memory=False, allow_kb=True,
                tools=["chat"], reason="kullanıcı araştırmayı reddetti",
                context_summary=ctx.get("summary", ""), topic=topic,
            )
        if any(p in text for p in PERSONAL) or re.search(r"(?:benim )?(?:adim|ismim)\s+\w+", text):
            return Decision(
                intent="personal", allow_web=False, allow_memory=True, allow_kb=False,
                tools=["memory", "chat"], reason="kişisel / isim",
                context_summary=ctx.get("summary", ""), topic=topic,
            )

        # --- math ---
        if self._looks_math(raw):
            return Decision(
                intent="math", allow_web=False, allow_memory=False, allow_kb=False,
                tools=["math"], reason="matematik ifadesi",
                context_summary=ctx.get("summary", ""), topic=topic,
            )

        # --- chat / greetings (before code: 'nasılsın' ≠ code) ---
        if self._looks_chat(text, words):
            return Decision(
                intent="chat", allow_web=False, allow_memory=False, allow_kb=False,
                tools=["chat"], reason="sohbet / selamlaşma",
                context_summary=ctx.get("summary", ""), topic=topic,
            )

        # --- help ---
        if words & {"yardim", "help", "yetenekler", "ozelliklerin"} or "ne yapabilirsin" in text:
            return Decision(
                intent="help", allow_web=False, allow_memory=False, allow_kb=True,
                tools=["chat", "kb"], reason="yetenek / yardım sorusu",
                context_summary=ctx.get("summary", ""), topic=topic,
            )

        # --- code ---
        if self._looks_code(text, words):
            plan = self._code_plan(text)
            return Decision(
                intent="code", allow_web=False, allow_memory=True, allow_kb=True,
                tools=["kb", "memory", "code"], plan=plan,
                reason="kod / örnek isteği",
                context_summary=ctx.get("summary", ""), topic=topic,
            )

        # --- analyze ---
        if any(p in text for p in ANALYZE) or ("```" in raw and len(raw) > 40):
            return Decision(
                intent="analyze", allow_web=False, allow_memory=True, allow_kb=True,
                tools=["kb", "chat"], plan=["kodu oku", "sorunu bul", "düzeltme öner"],
                reason="analiz / debug",
                context_summary=ctx.get("summary", ""), topic=topic,
            )

        # --- followup (needs prior topic) ---
        if history and self._looks_followup(text, words, topic):
            main = " ".join(topic[:2])
            return Decision(
                intent="followup", allow_web=True, allow_memory=True, allow_kb=True,
                tools=["memory", "kb", "web"],
                reason=f"önceki konuya bağlı: «{main}»",
                research_query=f"{main} {raw}".strip(),
                context_summary=ctx.get("summary", ""), topic=topic,
            )

        # --- research (strict) ---
        if self._looks_research(text, words):
            return Decision(
                intent="research", allow_web=True, allow_memory=True, allow_kb=True,
                tools=["memory", "kb", "web"],
                reason="bilgi / olgu sorusu",
                research_query=raw,
                context_summary=ctx.get("summary", ""), topic=topic,
            )

        # default: conversational, NO web
        return Decision(
            intent="chat", allow_web=False, allow_memory=True, allow_kb=True,
            tools=["chat", "kb"], reason="belirsiz → sohbet (web yok)",
            context_summary=ctx.get("summary", ""), topic=topic,
        )

    # -------------------- classifiers --------------------

    @staticmethod
    def _looks_math(raw: str) -> bool:
        cleaned = raw.lower()
        for w in ["kac eder", "kaç eder", "hesapla", "sonucu ne", "=", "?"]:
            cleaned = cleaned.replace(w, " ")
        cleaned = cleaned.replace("x", "*").replace("çarpı", "*").replace("carpi", "*")
        cleaned = cleaned.replace("artı", "+").replace("arti", "+")
        cleaned = cleaned.replace("eksi", "-").replace("bölü", "/").replace("bolu", "/")
        cleaned = cleaned.strip()
        if not re.fullmatch(r"[\d\s+\-*/().%]+", cleaned or ""):
            return False
        return bool(re.search(r"\d", cleaned) and re.search(r"[+\-*/%]", cleaned))

    @staticmethod
    def _looks_chat(text: str, words: set[str]) -> bool:
        if words & CHAT_WORDS:
            return True
        if text in CHAT_WORDS:
            return True
        # short social phrases
        if len(words) <= 3 and words <= (CHAT_WORDS | {"misin", "musun", "miyim", "iyi", "gunun"}):
            return True
        return False

    @staticmethod
    def _looks_code(text: str, words: set[str]) -> bool:
        if words & CODE_STRONG:
            return True
        if (words & CODE_WRITE) and (words & (CODE_EXAMPLE | CODE_LANGS | CODE_STRONG)):
            return True
        if any(p in text for p in ("kod yaz", "write code", "python kod", "js kod")):
            return True
        if (words & CODE_EXAMPLE) and (words & (CODE_LANGS | CODE_STRONG | {"liste", "dosya", "class"})):
            return True
        # "X nasıl yazılır/yapılır" programming how-to — still code-ish if lang present
        if (words & CODE_LANGS) and any(x in text for x in ("nasil", "yazilir", "yapilir", "kullanilir")):
            return True
        return False

    @staticmethod
    def _looks_research(text: str, words: set[str]) -> bool:
        if any(h in text for h in RESEARCH_EXPLICIT):
            return True
        # multi-word named topic without code/chat — weak research signal only
        # if it looks like an entity question with 2+ content words
        stop = {
            "bir", "ve", "ile", "icin", "bu", "o", "su", "de", "da", "mi", "mu",
            "ben", "sen", "bana", "cok", "daha", "gibi",
        }
        content = [w for w in words if len(w) >= 4 and w not in stop]
        # require explicit question mark style OR 'hakkinda bilgi' already covered
        # Without explicit marker, do NOT research bare nouns (prevents spam).
        return False

    @staticmethod
    def _looks_followup(text: str, words: set[str], topic: list[str]) -> bool:
        if not topic:
            return False

        stop = FOLLOWUP_HINTS | {
            "nedir", "kimdir", "ne", "bir", "ve", "demek", "who", "what", "is", "are",
        }
        nouns = [w for w in words if len(w) >= 4 and w not in stop]

        # Açık yeni konu: "X nedir/kimdir" ve X önceki konuda yok
        if any(h in text for h in ("nedir", "kimdir", "ne demek", "who is", "what is", "hakkinda")):
            if nouns and not any(n in topic for n in nouns):
                return False

        if words & FOLLOWUP_HINTS:
            return True

        if len(words) <= 6 and any(q in text for q in (
            "neden", "niye", "nasil", "ne zaman", "nerede", "kac", "hangi",
            "ne kadar", "boyutu",
        )):
            return True

        # kısa mesaj + yeni isim yok → takip
        if len(words) <= 5 and not (set(nouns) - set(topic)):
            return True
        return False

    @staticmethod
    def _code_plan(text: str) -> list[str]:
        plan = ["isteği anla"]
        if any(w in text for w in ("oyun", "game", "web", "api", "flask", "bot")):
            plan += ["yapıyı tasarla", "temel kodu yaz", "kısa kullanım notu ekle"]
        else:
            plan += ["uygun örneği seç veya yaz", "çalışır kod ver"]
        return plan

    # -------------------- context --------------------

    def pack_context(self, history: list, limit_turns: int = 8) -> dict:
        """Compress recent history into topic + name + short summary."""
        users, ais = [], []
        for h in history[-limit_turns * 2:]:
            role = h.get("role")
            content = str(h.get("content", "")).strip()
            if not content:
                continue
            if role == "user":
                users.append(content)
            elif role in ("ai", "assistant"):
                ais.append(content)

        name = None
        for msg in reversed(users):
            m = re.search(r"(?:benim )?(?:adım|adim|ismim)\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)", msg, re.I)
            if m and m.group(1).lower() not in ("ne", "neydi", "nedir"):
                name = m.group(1).capitalize()
                break

        topic: list[str] = []
        stop = {
            "nedir", "ne", "nasil", "kim", "kimdir", "bir", "ve", "ile", "icin",
            "peki", "bu", "o", "su", "yaz", "kod", "ornek", "bana", "hakkinda",
        }
        for msg in reversed(users):
            n = _norm(msg)
            # skip followup-shaped
            words = n.split()
            if len(words) <= 5 and any(q in n for q in ("neden", "nasil", "ne zaman", "hangisi")):
                if not any(h in n for h in ("nedir", "kimdir")):
                    continue
            nouns = [w for w in words if len(w) >= 4 and w not in stop]
            if nouns:
                topic = nouns[:3]
                break

        parts = []
        if name:
            parts.append(f"kullanıcı_adı={name}")
        if topic:
            parts.append(f"konu={' '.join(topic)}")
        if users:
            parts.append(f"son_soru={users[-1][:80]}")
        if ais:
            parts.append(f"son_cevap={ais[-1][:100]}")

        return {
            "name": name,
            "topic": topic,
            "summary": " | ".join(parts),
            "user_count": len(users),
        }


agent = Agent()
