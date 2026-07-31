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


def decide(text: str, *, has_prior_code: bool = False) -> DiscourseDecision:
    raw = text or ""
    folded = _fold(raw)

    if _IMPROVE.search(folded) and has_prior_code:
        return DiscourseDecision(
            intent=Intent.CODING,
            confidence=0.92,
            improve_code=True,
            reason="repair/improve prior code",
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
        # improve asked but no code in memory yet
        return DiscourseDecision(
            intent=Intent.CODING,
            confidence=0.7,
            improve_code=True,
            reason="improve requested",
        )

    return DiscourseDecision()
