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
    text = (text or "")
    text = text.replace("İ", "i").replace("I", "i").replace("ı", "i")
    text = text.lower()
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
    "konusalim", "sohbet", "napıyorsun", "napıyosun", "napıyorsun",
}

CODE_STRONG = {
    "kod", "kodu", "code", "script", "program", "fonksiyon", "function",
    "class", "algoritma", "snippet",
}
CODE_WRITE = {"yaz", "write", "olustur", "uret", "generate"}
CODE_EXAMPLE = {"ornek", "ornegi", "ornekleri", "example", "goster", "show", "sample", "config", "konfig"}
CODE_LANGS = {
    "python", "js", "javascript", "sql", "sqlite", "html", "css", "java",
    "cpp", "typescript", "ts", "flask", "django", "react", "node", "docker",
    "yaml", "pandas", "numpy", "nginx", "usestate", "useeffect", "hook", "hooks",
    "promise", "fastapi", "redis", "postgres", "postgresql",
}

RESEARCH_EXPLICIT = (
    "nedir", "kimdir", "ne demek", "hakkinda", "tarihi",
    "ne zaman", "nerede", "neresi", "neden", "niye",
    "nasil calisir", "nasil olusur", "ozellikleri", "anlami",
    "who is", "what is", "what are", "when was", "where is",
    "arastir", "araştir", "googlela", "internetten bak", "kaynak bul",
    "anlat", "kisaca", "ozetle", "bilgi ver", "aciklar misin",
    "nufus", "nufusu", "population", "kac kisi", "kac milyon",
    " vs ", " versus ", "farki", "farkı", "arasindaki fark", "arasındaki fark",
)

WEATHER_HINTS = (
    "hava durumu", "hava nasil", "hava rapor", "weather", "forecast", "yagmur",
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
    "ornek", "ornegi", "ornekler", "ornekleri", "example", "goster", "sample",
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
        name_intro = re.search(r"(?:benim )?(?:adim|ismim)\s+([a-zçğıöşü]+)", text)
        if any(p in text for p in PERSONAL) or (
            name_intro
            and name_intro.group(1) not in ("ne", "neydi", "nedir", "sayisi", "sayi")
            and not name_intro.group(1).isdigit()
        ):
            return Decision(
                intent="personal", allow_web=False, allow_memory=True, allow_kb=False,
                tools=["memory", "chat"], reason="kişisel / isim",
                context_summary=ctx.get("summary", ""), topic=topic,
            )

        # --- math / units / clock / meta (local skills) ---
        try:
            from model import skills as _skills
        except ImportError:
            import skills as _skills  # type: ignore

        if _skills.looks_like_noise(raw):
            return Decision(
                intent="chat", allow_web=False, allow_memory=False, allow_kb=False,
                tools=["chat"], reason="gürültü / boş mesaj",
                context_summary=ctx.get("summary", ""), topic=topic,
            )
        if _skills.looks_like_special_code(raw):
            return Decision(
                intent="chat", allow_web=False, allow_memory=False, allow_kb=False,
                tools=["chat"], reason="özel kod",
                context_summary=ctx.get("summary", ""), topic=topic,
            )
        if _skills.looks_like_math(raw) or _skills.convert_units(raw):
            return Decision(
                intent="math", allow_web=False, allow_memory=False, allow_kb=False,
                tools=["math"], reason="matematik / birim",
                context_summary=ctx.get("summary", ""), topic=topic,
            )
        if _skills.looks_like_time(raw):
            return Decision(
                intent="math", allow_web=False, allow_memory=False, allow_kb=False,
                tools=["math"], reason="saat / tarih",
                context_summary=ctx.get("summary", ""), topic=topic,
            )
        if _skills.looks_like_translate(raw):
            return Decision(
                intent="chat", allow_web=False, allow_memory=False, allow_kb=True,
                tools=["chat"], reason="çeviri",
                context_summary=ctx.get("summary", ""), topic=topic,
            )
        if _skills.looks_like_affirm(raw):
            return Decision(
                intent="chat", allow_web=False, allow_memory=True, allow_kb=False,
                tools=["chat"], reason="kısa onay / ret",
                context_summary=ctx.get("summary", ""), topic=topic,
            )
        if _skills.looks_like_casual(raw):
            return Decision(
                intent="chat", allow_web=False, allow_memory=False, allow_kb=False,
                tools=["chat"], reason="günlük tepki",
                context_summary=ctx.get("summary", ""), topic=topic,
            )
        if _skills.looks_like_meta(raw):
            return Decision(
                intent="help", allow_web=False, allow_memory=False, allow_kb=True,
                tools=["chat"], reason="DimAI meta / adım sorusu",
                context_summary=ctx.get("summary", ""), topic=topic,
            )
        if _skills.looks_like_weather(raw) or any(h in text for h in WEATHER_HINTS):
            return Decision(
                intent="research", allow_web=True, allow_memory=False, allow_kb=False,
                tools=["web"], reason="hava durumu",
                research_query=_skills.weather_query(raw),
                context_summary=ctx.get("summary", ""), topic=topic,
            )

        # Tek başına "neden/daha anlat" geçmiş yoksa web'e gitme
        if text in {"neden", "niye", "daha", "daha anlat", "devam", "anlat"} and not topic:
            return Decision(
                intent="chat", allow_web=False, allow_memory=True, allow_kb=True,
                tools=["chat"], reason="bağlamsız kısa soru",
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

        # --- followup BEFORE generic research ("daha anlat" ≠ film ara) ---
        if history and self._looks_followup(text, words, topic):
            main = " ".join(topic[:2])
            wants_ex = any(w in text for w in ("ornek", "ornegi", "goster", "example", "sample", "yaz"))
            if wants_ex and len(words) <= 5:
                rq = f"{main} yaz ornek".strip()
            elif words <= {"daha", "anlat", "devam", "acikla", "detay", "neden", "niye"} or text in {
                "daha anlat", "devam", "devam et", "anlat", "detay", "neden", "neden kullanilir",
            }:
                rq = f"{main} nedir ne ise yarar programming".strip()
            else:
                rq = f"{main} {raw}".strip()
            return Decision(
                intent="followup", allow_web=True, allow_memory=True, allow_kb=True,
                tools=["memory", "kb", "web"],
                reason=f"önceki konuya bağlı: «{main}»",
                research_query=rq,
                context_summary=ctx.get("summary", ""), topic=topic,
            )

        # --- research BEFORE code: "React nedir" ≠ kod örneği ---
        if self._looks_research(text, words) and not self._explicit_code_request(text, words):
            return Decision(
                intent="research", allow_web=True, allow_memory=True, allow_kb=True,
                tools=["memory", "kb", "web"],
                reason="bilgi / olgu sorusu",
                research_query=raw,
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

        # --- research (kalan olgu kalıpları) ---
        if self._looks_research(text, words):
            return Decision(
                intent="research", allow_web=True, allow_memory=True, allow_kb=True,
                tools=["memory", "kb", "web"],
                reason="bilgi / olgu sorusu",
                research_query=raw,
                context_summary=ctx.get("summary", ""), topic=topic,
            )

        # Soru gibi duran belirsiz mesaj → araştır (eskiden "anlamadım" oluyordu)
        if self._looks_question(text, words):
            return Decision(
                intent="research", allow_web=True, allow_memory=True, allow_kb=True,
                tools=["memory", "kb", "web"],
                reason="soru kalıbı → araştırma",
                research_query=raw,
                context_summary=ctx.get("summary", ""), topic=topic,
            )

        # default: conversational + KB; web yok
        return Decision(
            intent="chat", allow_web=False, allow_memory=True, allow_kb=True,
            tools=["chat", "kb"], reason="belirsiz → sohbet",
            context_summary=ctx.get("summary", ""), topic=topic,
        )

    # -------------------- classifiers --------------------

    @staticmethod
    def _looks_math(raw: str) -> bool:
        try:
            from model.skills import looks_like_math
        except ImportError:
            from skills import looks_like_math  # type: ignore
        return looks_like_math(raw)

    @staticmethod
    def _looks_question(text: str, words: set[str]) -> bool:
        """Factual/general questions that should not die as 'anlamadım'."""
        # Tek kelimelik bağlamsız sorular web spam'i yapar
        if len(words) <= 1:
            return False
        q_marks = "?" in text or text.endswith(" mi") or text.endswith(" mu")
        q_words = {
            "nedir", "kimdir", "nasil", "neden", "niye", "nerede", "ne", "kim",
            "hangi", "kac", "neydi", "midir", "mudur", "anlat", "acikla",
            "what", "who", "why", "where", "when", "how", "nufus", "nufusu",
        }
        # "neden/nasıl" tek başına yetmez — en az bir içerik kelimesi iste
        content = words - q_words - {"bir", "ve", "ile", "icin", "bu", "cok", "daha", "mi", "mu"}
        if (words & q_words) and content:
            return True
        if q_marks and len(words) >= 2 and content:
            return True
        if "hakkinda" in text or ("bilgi" in words and content):
            return True
        # "İstanbul nüfusu" gibi isim + olgu
        if content and words & {"nufus", "nufusu", "population", "tarihi", "baskenti"}:
            return True
        return False

    @staticmethod
    def _looks_chat(text: str, words: set[str]) -> bool:
        # "hello ne demek" / "write hello world" → sohbet değil
        if any(x in text for x in ("ne demek", "write ", "kod", "python", "javascript", "world")):
            if words & (CODE_WRITE | CODE_STRONG | CODE_LANGS | {"world", "demek", "english", "ingilizce"}):
                return False
        if text in CHAT_WORDS:
            return True
        social = CHAT_WORDS | {
            "misin", "musun", "miyim", "iyi", "gunun", "nasilsin",
            "konusalim", "sohbet", "muhabbet", "napıyorsun", "napıyosun",
            "ne", "yapiyorsun", "yapıyorsun", "bosum", "sikildim",
        }
        if words and words <= social:
            return True
        if len(words) <= 4 and words & CHAT_WORDS and not (words & (CODE_WRITE | CODE_STRONG | CODE_LANGS)):
            return True
        if any(p in text for p in ("konusalim", "konusuruz", "sohbet edelim", "muhabbet")):
            return True
        # "ne düşünüyorsun / ne haber" gibi sohbet — filme sapmasın
        if any(p in text for p in ("ne dusunuyorsun", "ne dusunuyon", "aklindan ne", "ne yapiyorsun")):
            return True
        return False

    @staticmethod
    def _explicit_code_request(text: str, words: set[str]) -> bool:
        """True only when user clearly wants code, not a definition."""
        if words & CODE_WRITE or words & CODE_EXAMPLE or words & CODE_STRONG:
            return True
        if any(p in text for p in ("kod yaz", "write code", "python kod", "js kod", "ornek ver", "örnek ver")):
            return True
        return False

    @staticmethod
    def _looks_code(text: str, words: set[str]) -> bool:
        # Tanım / bilgi sorusu → kod yolu değil
        if any(h in text for h in RESEARCH_EXPLICIT) and not (
            words & (CODE_WRITE | CODE_EXAMPLE | CODE_STRONG)
        ):
            return False
        if words & CODE_STRONG:
            return True
        if (words & CODE_WRITE) and (words & (CODE_EXAMPLE | CODE_LANGS | CODE_STRONG)):
            return True
        if any(p in text for p in ("kod yaz", "write code", "python kod", "js kod", "hello world")):
            return True
        if (words & CODE_EXAMPLE) and (words & (CODE_LANGS | CODE_STRONG | {"liste", "dosya", "class", "component", "nginx", "dockerfile"})):
            return True
        # "X yaz" / "write X" — kısa uygulama istekleri
        if (words & CODE_WRITE) and len(words) <= 8:
            return True
        if text.startswith("write ") and len(words) <= 10:
            return True
        # "X nasıl yazılır/yapılır" programming how-to — still code-ish if lang present
        if (words & CODE_LANGS) and any(x in text for x in ("nasil", "yazilir", "yapilir", "kullanilir", "ornegi", "ornek")):
            return True
        # React/component/hooks yalnızca yazma/örnek isteğinde kod
        if ("react" in words or "component" in words or "usestate" in words or "useeffect" in words or "hook" in words or "hooks" in words) and (
            words & (CODE_WRITE | CODE_EXAMPLE | CODE_STRONG) or "ornek" in text or "ornegi" in text
        ):
            return True
        if "nginx" in words and (words & (CODE_WRITE | CODE_EXAMPLE | {"config", "konfig", "conf"})):
            return True
        return False

    @staticmethod
    def _looks_research(text: str, words: set[str]) -> bool:
        if any(h in text for h in RESEARCH_EXPLICIT):
            return True
        if any(h in text for h in WEATHER_HINTS):
            return True
        # "X nedir" already covered; also "en büyük …", "ilk …"
        if words & {"en", "ilk", "kac"} and len(words) >= 3:
            return True
        return False

    @staticmethod
    def _looks_followup(text: str, words: set[str], topic: list[str]) -> bool:
        if not topic:
            return False

        stop = FOLLOWUP_HINTS | {
            "nedir", "kimdir", "ne", "bir", "ve", "demek", "who", "what", "is", "are",
            "ver", "yaz", "kod", "code", "lutfen", "please",
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
            "daha", "anlat", "devam", "acikla", "detay", "neden", "niye", "kullanilir",
            "kullanılır", "neydi", "midir", "mudur", "misin", "musun",
        }
        follow_only = {"daha", "anlat", "devam", "acikla", "detay", "neden", "niye", "peki", "baska"}
        for msg in reversed(users):
            n = _norm(msg)
            words = n.split()
            # skip pure followups — previous real topic'i koru
            content = [w for w in words if w not in follow_only and w not in stop]
            if not content and (set(words) <= (follow_only | stop | {"mi", "mu", "miyim"})):
                continue
            if len(words) <= 5 and any(q in n for q in ("neden", "nasil", "ne zaman", "hangisi")):
                if not any(h in n for h in ("nedir", "kimdir")) and not content:
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
