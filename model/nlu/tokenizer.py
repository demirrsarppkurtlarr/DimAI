"""Stage 2 — tokenization preserving punctuation and numbers."""
from __future__ import annotations

import re
from typing import List

from .types import Token


_TOKEN_RE = re.compile(
    r"""
    (?:[A-Za-zÇĞİÖŞÜçğıöşü]+(?:'[A-Za-zÇĞİÖŞÜçğıöşü]+)*)   # words / contractions
    | \d+(?:[.,]\d+)?                                        # numbers
    | [\.]+ | [!?]+ | [,;:] | ["'()\[\]{}] | [-/\\@#]        # punct
    | \S                                                     # other
    """,
    re.VERBOSE,
)


def _lemma(word: str) -> str:
    w = word.lower().replace("İ", "i").replace("I", "i")
    # light stemming for common TR suffixes (not a full morphological analyzer)
    for suf in (
        "larini", "lerimizi", "larimizi", "siniz", "siniz", "yoruz", "iyoruz",
        "iyor", "uyor", "arak", "erek", "madan", "meden", "larla", "lerle",
        "daki", "deki", "nin", "nın", "nun", "nün", "den", "dan", "ten", "tan",
        "ler", "lar", "dir", "dır", "dur", "dür", "tir", "tır", "tur", "tür",
        "mis", "mış", "muş", "müş", "ing", "ed", "ly", "tion",
    ):
        if len(w) > len(suf) + 2 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def tokenize(text: str) -> List[Token]:
    tokens: list[Token] = []
    for i, m in enumerate(_TOKEN_RE.finditer(text or "")):
        t = m.group(0)
        is_num = bool(re.fullmatch(r"\d+(?:[.,]\d+)?", t))
        is_punct = (not is_num) and (not re.search(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9]", t))
        tokens.append(
            Token(
                text=t,
                lemma=_lemma(t) if not is_punct and not is_num else t.lower(),
                index=i,
                is_punct=is_punct,
                is_number=is_num,
            )
        )
    return tokens
