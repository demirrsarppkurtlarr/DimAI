"""Conversation understanding helpers — meaning, incomplete speech, personality.

Used by the NLU pipeline (Phase 2). Does not replace intent/discourse engines;
it expands underspecified utterances and keeps a stable DimAI voice.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional, Sequence

from .types import Entity, Intent, MemoryHit


def _fold(text: str) -> str:
    t = (text or "").lower().replace("İ", "i").replace("I", "i").replace("ı", "i")
    return t.translate(str.maketrans("çğıöşü", "cgiosu"))


# Bare fragments that usually continue the prior topic
_INCOMPLETE = re.compile(
    r"^(?:"
    r"ve\??|peki\??|ya\??|ee+\??|hmm+\??|hm+\??|"
    r"daha\??|daha\s+anlat\??|devam\??|devam\s+et\??|"
    r"ayni\??|ayni\s+proje\??|onceki\??|onceki\s+biri?\??|"
    r"onu\??|bunu\??|sunu\??|o\??|bu\??|"
    r"neden\??|nasil\??|ne\??|kim\??|"
    r"again\??|continue\??|more\??|and\??|so\??|ok\??|okay\??|"
    r"same\??|same\s+(?:one|project|thing)\??|previous\??|"
    r"tell\s+me\s+more\??|go\s+on\??|why\??|how\??|what\s+about\??"
    r")$",
    re.I,
)

_INDIRECT = (
    "acaba",
    "sence",
    "merak ediyorum",
    "merak ettim",
    "bilgin var mi",
    "haberin var mi",
    "ne dersin",
    "anlatabilir misin",
    "soyleyebilir misin",
    "yardimci olur musun",
    "i wonder",
    "do you know",
    "could you",
    "would you",
    "any idea",
    "curious about",
    "what about",
    "how about",
)

_CONTINUE = (
    "devam",
    "continue",
    "go on",
    "daha anlat",
    "tell me more",
    "more please",
    "devam et",
    "surdur",
)

_SAME_PROJECT = (
    "ayni proje",
    "same project",
    "bu proje",
    "this project",
    "onceki proje",
    "previous project",
    "ustundeki",
    "uzerinde calistigimiz",
)


@dataclass
class MeaningFrame:
    """Internal reading of what the user really wants."""

    expanded: str
    is_incomplete: bool = False
    is_indirect: bool = False
    wants_continue: bool = False
    same_project: bool = False
    implied_intent: Optional[Intent] = None
    notes: list[str] = field(default_factory=list)


def analyze_meaning(
    text: str,
    *,
    topic: str = "",
    last_code: str = "",
    entities: Sequence[Entity] | None = None,
    memory: Sequence[MemoryHit] | None = None,
) -> MeaningFrame:
    raw = (text or "").strip()
    folded = _fold(raw)
    notes: list[str] = []
    expanded = raw

    incomplete = bool(_INCOMPLETE.match(folded.strip(" .!?"))) or (
        len(raw.split()) <= 2 and folded in {
            "o", "bu", "su", "onu", "bunu", "peki", "ya", "ee", "hmm",
            "daha", "neden", "nasil", "again", "more", "ok", "okay",
        }
    )
    indirect = any(cue in folded for cue in _INDIRECT)
    wants_continue = any(cue in folded for cue in _CONTINUE) or incomplete
    same_project = any(cue in folded for cue in _SAME_PROJECT)

    ante = topic.strip()
    if not ante and memory:
        for h in memory:
            if h.kind == "topic" and h.content:
                ante = h.content.strip()
                break
    if not ante and entities:
        for e in reversed(list(entities)):
            if e.normalized or e.text:
                ante = e.normalized or e.text
                break

    if incomplete and ante:
        # Expand fragments into a full communicative intent
        if folded in {"neden", "why", "niye"}:
            expanded = f"{ante} neden böyle / why"
            notes.append("incomplete:why→topic")
        elif folded in {"nasil", "how"}:
            expanded = f"{ante} nasıl çalışır / how it works"
            notes.append("incomplete:how→topic")
        elif folded in {"ne", "what", "kim", "who"}:
            expanded = f"{ante} nedir"
            notes.append("incomplete:what→topic")
        elif any(x in folded for x in ("devam", "continue", "daha", "more", "go on")):
            expanded = f"{ante} hakkında daha anlat"
            notes.append("incomplete:continue→topic")
        elif any(x in folded for x in ("ayni", "same", "onceki", "previous")):
            expanded = f"{ante} ile devam et / continue same"
            notes.append("incomplete:same→topic")
        else:
            expanded = f"{ante} {raw}".strip()
            notes.append("incomplete:prepend-topic")
    elif wants_continue and ante and ante.lower() not in folded:
        expanded = f"{ante} hakkında daha anlat: {raw}"
        notes.append("continue+topic")

    if same_project and ante:
        expanded = f"{ante} projesi: {expanded}"
        notes.append("same-project")

    if last_code and any(x in folded for x in ("gelistir", "improve", "duzelt", "fix", "refactor")):
        notes.append("code-context-available")

    implied: Optional[Intent] = None
    if incomplete or wants_continue:
        implied = Intent.EXPLANATION
    if indirect and not incomplete:
        # Soft: curious phrasing often means question/search
        if any(x in folded for x in ("kim", "who", "nedir", "what is")):
            implied = Intent.SEARCH
        else:
            implied = Intent.QUESTION

    return MeaningFrame(
        expanded=expanded,
        is_incomplete=incomplete,
        is_indirect=indirect,
        wants_continue=wants_continue,
        same_project=same_project,
        implied_intent=implied,
        notes=notes,
    )


# Stable DimAI personality — short, warm, engineer-curious, never robotic lists
PERSONA_TR = {
    "greeting": (
        "Merhaba{name} — buradayım. "
        "Kod, kavram ya da sadece sohbet; senin temposunda ilerleriz."
    ),
    "thanks": "Rica ederim{name}. Takıldığın yer olursa hemen yaz.",
    "bye": "Görüşürüz{name}. İyi çalışmalar — kaldığın yerden devam ederiz.",
    "bored": (
        "Sıkıntıyı anlıyorum. İstersen küçük bir proje fikri çıkaralım "
        "ya da bir konuyu rahatça konuşalım."
    ),
    "whoami": (
        "Ben DimAI — seninle birlikte düşünen bir kod asistanıyım. "
        "Ezber cevap değil; senin bağlamına göre ilerlemeyi tercih ederim."
    ),
    "help": (
        "Şunlarda yanındayım: kavram açıklamak, sıfırdan kod tasarlamak, "
        "hata ayıklamak, çeviri, hava/saat ve proje planı. "
        "Ne üzerindeyiz?"
    ),
}

PERSONA_EN = {
    "greeting": (
        "Hey{name} — I'm here. "
        "Code, concepts, or just talk; we can move at your pace."
    ),
    "thanks": "Anytime{name}. Ping me when you're stuck.",
    "bye": "Catch you later{name}. We'll pick up where we left off.",
    "bored": (
        "I get that. Want a small project idea, or just a chill topic?"
    ),
    "whoami": (
        "I'm DimAI — a coding partner that thinks with you. "
        "I prefer context over canned answers."
    ),
    "help": (
        "I can explain ideas, design code from scratch, debug, translate, "
        "check weather/time, and sketch plans. What are we on?"
    ),
}


def detect_chitchat_key(text: str) -> Optional[str]:
    f = _fold(text)
    # Exact-ish short social acts (avoid matching inside longer tech asks)
    if len(f.split()) > 8:
        return None
    if re.search(r"\b(merhaba|selam|hello|hi|hey|slm|sa|gunaydin|good morning)\b", f):
        return "greeting"
    if re.search(r"\b(tesekkur|sagol|thanks|thank you|eyvallah)\b", f):
        return "thanks"
    if re.search(r"\b(gorusuruz|bye|goodbye|hosca kal|iyi geceler)\b", f):
        return "bye"
    if re.search(r"\b(sikildim|canim sikildi|bored|bunaldim)\b", f):
        return "bored"
    if re.search(r"\b(sen kimsin|who are you|ne yapabilirsin|what can you do|yardim)\b", f):
        if "ne yapabilirsin" in f or "what can you do" in f or f.strip() in {"yardim", "help"}:
            return "help"
        if "sen kimsin" in f or "who are you" in f:
            return "whoami"
    if f.strip() in {"yardim", "help", "?"}:
        return "help"
    return None


def persona_reply(key: str, *, language: str = "tr", name: str = "") -> str:
    bank = PERSONA_TR if language != "en" else PERSONA_EN
    tmpl = bank.get(key) or bank["help"]
    name_bit = f" {name}" if name else ""
    return tmpl.format(name=name_bit)


def memory_name(hits: Sequence[MemoryHit]) -> str:
    for h in hits:
        if h.kind == "preference" and "name=" in h.content:
            return h.content.split("name=")[-1].split(",")[0].strip()
    return ""


def weave_context_prefix(
    reply: str,
    *,
    topic: str = "",
    language: str = "tr",
    wants_continue: bool = False,
) -> str:
    """Light continuity cue — not a robotic 'As I said earlier…' monologue."""
    if not topic or not wants_continue:
        return reply
    t = topic.strip()
    if not t or _fold(t) in _fold(reply):
        return reply
    short = t if len(t) <= 48 else t[:45] + "…"
    if language == "en":
        prefix = f"On {short}: "
    else:
        prefix = f"{short} konusunda: "
    return prefix + reply.lstrip()


def anti_robotic(reply: str) -> str:
    """Strip stiff template openers that make replies feel canned."""
    r = (reply or "").strip()
    stiff = (
        r"^Tabii ki[,!]?\s*",
        r"^Elbette[,!]?\s*",
        r"^Of course[,!]?\s*",
        r"^Certainly[,!]?\s*",
        r"^As an AI[,^\n]*[,.]?\s*",
        r"^Bir yapay zeka olarak[,^\n]*[,.]?\s*",
        r"^I am an AI[,^\n]*[,.]?\s*",
    )
    for pat in stiff:
        r = re.sub(pat, "", r, flags=re.I)
    # Collapse triple newlines
    r = re.sub(r"\n{3,}", "\n\n", r)
    return r.strip()
