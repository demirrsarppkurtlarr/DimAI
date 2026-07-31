"""Stage 1 — input normalization (spelling, unicode, punctuation, whitespace)."""
from __future__ import annotations

import re
import unicodedata
from difflib import get_close_matches
from typing import Iterable


# Compact high-frequency TR/EN lexicon for soft spelling repair
_LEXICON: frozenset[str] = frozenset(
    """
    merhaba selam nasilsin naber tesekkur lutfen tamam peki evet hayir
    nedir nasil neden niye kimdir hakkinda anlat acikla ornek yaz olustur
    kod python javascript typescript java react flask django docker git
    sql html css api redis postgres mongodb vercel nextjs render
    chatbot todo oyun sifre hesap makinesi cevir ingilizce turkce
    bugun yarin dun saat hava istanbul ankara izmir
    hello thanks please what how why when where who code write explain
    translate continue again same that this help please sorry
    fibonacci binary search algorithm function class variable project
    gelistir improve refactor optimize debug hata duzelt onceki ayni
    proje devam daha fazla anlat acaba sence merak ediyorum
    fastapi nextjs
    """.split()
)


def _fold(text: str) -> str:
    text = text.replace("İ", "i").replace("I", "i").replace("ı", "i")
    text = text.lower()
    text = text.translate(str.maketrans("çğıöşü", "cgiosu"))
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text


def _fix_punct(text: str) -> str:
    text = text.replace("…", "...")
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"[?]{2,}", "?", text)
    text = re.sub(r"[!]{2,}", "!", text)
    text = re.sub(r"[.]{4,}", "...", text)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    text = re.sub(r"([,.!?;:])([^\s])", r"\1 \2", text)
    return text


def _collapse_ws(text: str) -> str:
    text = text.replace("\u00a0", " ").replace("\t", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _correct_token(tok: str, lexicon: Iterable[str]) -> str:
    if len(tok) < 4 or tok.isdigit() or any(c.isdigit() for c in tok):
        return tok
    folded = _fold(tok)
    if folded in lexicon:
        return tok
    # Keep original casing loosely; suggest by fold match
    hits = get_close_matches(folded, list(lexicon), n=1, cutoff=0.86)
    if not hits:
        return tok
    # Prefer lexicon form when clearly a typo
    return hits[0]


def normalize(text: str, *, spellcheck: bool = True) -> str:
    """Produce a clean, model-ready utterance string."""
    raw = text or ""
    raw = unicodedata.normalize("NFKC", raw)
    raw = _fix_punct(raw)
    raw = _collapse_ws(raw)

    if not spellcheck or not raw:
        return raw

    parts = re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9_]+|[^\sA-Za-zÇĞİÖŞÜçğıöşü0-9_]", raw)
    out: list[str] = []
    for p in parts:
        if re.fullmatch(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9_]+", p):
            out.append(_correct_token(p, _LEXICON))
        else:
            out.append(p)
    # Re-join: no space before punctuation
    joined = ""
    for p in out:
        if not joined:
            joined = p
        elif re.fullmatch(r"[,.!?;:]", p):
            joined += p
        elif joined[-1:].isalnum() and p[:1].isalnum():
            joined += " " + p
        elif p == "'":
            joined += p
        else:
            joined += (" " if p.strip() else "") + p
    return _collapse_ws(joined)
