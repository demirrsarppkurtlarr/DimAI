"""Discourse-level overrides — grammatical / pragmatic cues.

These are not a keyword chatbot: they detect question forms, speech acts,
and repair requests that embedding centroids often miss on short Turkish
utterances (kimdir, araştır, geliştir…).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .types import Intent


def _fold(text: str) -> str:
    t = (text or "").lower().replace("İ", "i").replace("I", "i").replace("ı", "i")
    return t.translate(str.maketrans("çğıöşü", "cgiosu"))


@dataclass
class DiscourseDecision:
    intent: Optional[Intent] = None
    confidence: float = 0.0
    search_query: str = ""
    improve_code: bool = False
    reason: str = ""


_PERSON_Q = re.compile(
    r"(?P<name>[A-Za-zÇĞİÖŞÜçğıöşü][A-Za-zÇĞİÖŞÜçğıöşü'\-]+(?:\s+[A-Za-zÇĞİÖŞÜçğıöşü][A-Za-zÇĞİÖŞÜçğıöşü'\-]+){0,3})"
    r"\s+(?:kimdir|kim|who\s+is|who\s+was)\b",
    re.I,
)
_SEARCH = re.compile(
    r"\b(arastir|araştır|araştir|googlela|internetten\s+bak|web(?:de|den)?|search|research|bul)\b",
    re.I,
)
_IMPROVE = re.compile(
    r"\b(gelistir|geli[sş]tir|improve|refactor|optimize|optimize\s+et|"
    r"daha\s+iyi|daha\s+uzun|daha\s+gelismis|genislet|upgrade|"
    r"kodu\s+duzelt|kodu\s+iyi|uzat|enrich)\b",
    re.I,
)
_CONTINUE = re.compile(
    r"^(?:daha(?:\s+anlat)?|devam(?:\s+et)?|anlat|acikla|"
    r"continue|again|more|go\s+on|tell\s+me\s+more|elaborate)\s*[.?!]*$",
    re.I,
)
_INDIRECT_Q = re.compile(
    r"\b(acaba|sence|merak\s+ediyorum|merak\s+ettim|bilgin\s+var\s+mi|"
    r"i\s+wonder|do\s+you\s+know|could\s+you\s+tell|any\s+idea|"
    r"what\s+about|how\s+about|ne\s+dersin)\b",
    re.I,
)
_SAME_PROJECT = re.compile(
    r"\b(ayni\s+proje|same\s+project|bu\s+proje|this\s+project|"
    r"onceki\s+proje|previous\s+(?:one|project)|ustundeki)\b",
    re.I,
)
_COMPARE = re.compile(
    r"\b(karsilastir|karşılaştır|karsilastirma|farki|farkı|farklar|"
    r"vs\.?|versus|hangisi\s+daha|compare|comparison|between)\b",
    re.I,
)
_HOW_SELF = re.compile(
    r"\b(sen\s+nasil\s+calisiyorsun|nasil\s+calisiyorsun|how\s+do\s+you\s+work|"
    r"how\s+are\s+you\s+built|nasil\s+isliyorsun|ne\s+yapabiliyorsun|"
    r"seni\s+anlat|kendini\s+anlat)\b",
    re.I,
)
_DEFINITION = re.compile(
    r"\b(\w+)\s+(nedir|ne\s+demek|hakkinda)\b|\bwhat\s+is\b|\bexplain\b",
    re.I,
)
_STOP_NAME = {
    "bu", "su", "o", "bir", "the", "a", "an", "web", "de", "da", "icin",
    "bana", "nedir", "nasil", "ne", "kim", "who", "is",
}


def extract_search_topic(text: str) -> str:
    """Pull the likely topic from a search/who-is utterance."""
    raw = (text or "").strip()
    m = _PERSON_Q.search(raw)
    if m:
        name = m.group("name").strip()
        parts = [p for p in name.split() if _fold(p) not in _STOP_NAME]
        if parts:
            return " ".join(parts)

    folded = _fold(raw)
    # strip speech-act words, keep content
    cleaned = re.sub(
        r"\b(web|de|da|den|ara[sş]tir|arastir|googlela|internetten|bak|bul|"
        r"search|research|kimdir|kim|who|is|was|hakkinda|nedir|ne|demek)\b",
        " ",
        folded,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # restore nicer casing from original tokens when possible
    if cleaned:
        return cleaned
    return raw


def decide(
    text: str,
    *,
    has_prior_code: bool = False,
    has_topic: bool = False,
) -> DiscourseDecision:
    raw = text or ""
    folded = _fold(raw)

    if _IMPROVE.search(folded) and has_prior_code:
        return DiscourseDecision(
            intent=Intent.CODING,
            confidence=0.92,
            improve_code=True,
            reason="repair/improve prior code",
        )

    # Self-model questions — never stuck on prior topic
    if _HOW_SELF.search(folded):
        return DiscourseDecision(
            intent=Intent.CONVERSATION,
            confidence=0.95,
            reason="how-self / capability question",
        )

    # Explicit comparisons — answer, don't clarify
    if _COMPARE.search(folded) and len(folded.split()) >= 2:
        return DiscourseDecision(
            intent=Intent.OPINION,
            confidence=0.9,
            search_query=raw.strip(),
            reason="compare/vs speech act",
        )

    if _PERSON_Q.search(raw) or (
        _SEARCH.search(folded)
        and len([w for w in folded.split() if w not in _STOP_NAME]) >= 1
    ):
        topic = extract_search_topic(raw)
        return DiscourseDecision(
            intent=Intent.SEARCH,
            confidence=0.9,
            search_query=topic or raw,
            reason="person/search speech act",
        )

    # "X kimdir" without regex hit due to typos — morph ending
    if re.search(r"\b\w+\s+kimdir\b", folded) or "who is" in folded:
        return DiscourseDecision(
            intent=Intent.SEARCH,
            confidence=0.85,
            search_query=extract_search_topic(raw) or raw,
            reason="kimdir/who-is",
        )

    if _IMPROVE.search(folded):
        return DiscourseDecision(
            intent=Intent.CODING,
            confidence=0.7,
            improve_code=True,
            reason="improve requested",
        )

    # Definitional "X nedir" with content — question, not clarify
    if _DEFINITION.search(folded) and len([w for w in folded.split() if w not in _STOP_NAME]) >= 1:
        return DiscourseDecision(
            intent=Intent.QUESTION,
            confidence=0.82,
            search_query=extract_search_topic(raw) or raw,
            reason="definitional question",
        )

    # Continuation / incomplete follow-ups when prior topic exists
    if has_topic and (
        _CONTINUE.match(folded.strip())
        or _SAME_PROJECT.search(folded)
        or folded.strip() in {"peki", "ya", "ee", "hmm", "ok", "okay", "tamam"}
    ):
        return DiscourseDecision(
            intent=Intent.EXPLANATION,
            confidence=0.82,
            reason="continue/incomplete follow-up",
        )

    # Indirect questions → treat as question/search, not chitchat
    if _INDIRECT_Q.search(folded) and len(folded.split()) >= 3:
        if _PERSON_Q.search(raw) or "kim" in folded or "who" in folded:
            return DiscourseDecision(
                intent=Intent.SEARCH,
                confidence=0.78,
                search_query=extract_search_topic(raw) or raw,
                reason="indirect person/search",
            )
        return DiscourseDecision(
            intent=Intent.QUESTION,
            confidence=0.75,
            reason="indirect question",
        )

    return DiscourseDecision()
