"""Phase 8 — response quality polish.

Makes DimAI replies clearer and more senior-engineer: direct lead,
less fluff, consistent structure, better presentation of HF/learned code.
"""
from __future__ import annotations

import re
from typing import Any, Optional


_BANNER = re.compile(
    r"^🔎\s*\*?\*?Çoklu kaynak[^\n]*\n+",
    re.I,
)
_SOURCES_TAIL = re.compile(
    r"\n*📚\s*\*?\*?Kaynaklar[^\n]*\n(?:•[^\n]*\n?)*",
    re.I,
)
_MULTI_SPACE = re.compile(r"[ \t]{2,}")
_FILLER_TR = re.compile(
    r"^(tabii|elbette|şöyle ki|kısaca söylemek gerekirse|aslında)\s*[,:]?\s*",
    re.I,
)
_FILLER_EN = re.compile(
    r"^(sure|absolutely|basically|to be honest|in summary)\s*[,:]?\s*",
    re.I,
)


def polish(reply: str, *, language: str = "tr") -> str:
    """Tighten prose without changing meaning."""
    r = (reply or "").strip()
    if not r:
        return r
    r = _BANNER.sub("", r)
    r = _SOURCES_TAIL.sub("", r)
    r = _MULTI_SPACE.sub(" ", r)
    r = re.sub(r"\n{3,}", "\n\n", r)
    first, *rest = r.split("\n", 1)
    for _ in range(3):
        cleaned = _FILLER_EN.sub("", first) if language == "en" else _FILLER_TR.sub("", first)
        cleaned = cleaned.lstrip(" ,:;-")
        if cleaned == first:
            break
        first = cleaned
    r = first + (("\n" + rest[0]) if rest else "")
    # Soft cap very long web dumps for chat readability
    if len(r) > 3500:
        cut = r[:3400]
        if "\n" in cut:
            cut = cut.rsplit("\n", 1)[0]
        r = cut.rstrip() + ("…" if language == "en" else "…")
    return r.strip()


def present_code_answer(
    *,
    question: str,
    answer: str,
    code: str = "",
    lang: str = "python",
    language: str = "tr",
) -> dict[str, Any]:
    """Shape a learned/HF coding hit into a clean engineer-style reply."""
    ans = polish(answer, language=language)
    # If answer already embeds fences, keep prose short
    has_fence = "```" in ans
    if language == "en":
        lead = "Here's a solid approach for your ask:"
    else:
        lead = "İsteğin için net bir yaklaşım:"
    # Prefer extracted code payload when present
    body = ans
    if code and not has_fence:
        # Keep instructional prose brief when we also ship code
        prose = ans
        if len(prose) > 900:
            prose = prose[:850].rsplit("\n", 1)[0] + ("…" if language == "en" else "…")
        body = f"{lead}\n\n{prose}" if prose and prose != code.strip() else lead
        return {
            "reply": polish(body, language=language),
            "code": code.strip() + ("\n" if not code.endswith("\n") else ""),
            "lang": lang or "python",
            "source": "learned",
        }
    return {"reply": polish(body if body else lead, language=language), "source": "learned"}


def lead_with_answer(reply: str, *, language: str = "tr") -> str:
    """Ensure the first sentence carries the answer, not a throat-clear."""
    r = polish(reply, language=language)
    lines = [ln for ln in r.splitlines() if ln.strip()]
    if not lines:
        return r
    # Move a markdown heading / bold title first if buried
    for i, ln in enumerate(lines[:5]):
        if ln.startswith("**") or ln.startswith("#"):
            if i > 0:
                lines = [ln] + lines[:i] + lines[i + 1 :]
            break
    return "\n".join(lines)
