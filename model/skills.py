"""Practical skills that make DimAI strong where the tiny RNN is weak.

Math, clock/date, DimAI meta-questions, light unit conversion — all local,
no external AI APIs.
"""
from __future__ import annotations

import ast
import operator
import re
import unicodedata
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo


def _norm(text: str) -> str:
    text = (text or "").lower()
    text = text.translate(str.maketrans("çğıöşü", "cgiosu"))
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^a-z0-9+\-*/=<>.%()^\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# -------------------- math --------------------

_WORD_OPS = (
    ("arti", "+"),
    ("artı", "+"),
    ("eksi", "-"),
    ("carpi", "*"),
    ("çarpı", "*"),
    ("x", "*"),
    ("bolu", "/"),
    ("bölü", "/"),
    ("mod", "%"),
    ("uzeri", "**"),
    ("üzeri", "**"),
    ("^", "**"),
)

_STRIP_PHRASES = (
    "kac eder", "kaç eder", "kac yapar", "kaç yapar",
    "sonucu ne", "sonuc ne", "sonuç ne", "hesapla", "hesaplar misin",
    "hesaplar mısın", "ne eder", "ne yapar", "esittir", "eşittir",
    "kac", "kaç", "nedir sonucu", "cevap ne", "=", "?", "!",
)

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(expr: str):
    node = ast.parse(expr, mode="eval")

    def _eval(n):
        if isinstance(n, ast.Expression):
            return _eval(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.Num):  # py<3.8 compat
            return n.n
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](_eval(n.left), _eval(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](_eval(n.operand))
        raise ValueError("unsupported")

    return _eval(node)


def extract_math_expr(raw: str) -> Optional[str]:
    """Return a clean arithmetic expression or None."""
    text = (raw or "").strip().lower()
    if not text:
        return None
    for phrase in _STRIP_PHRASES:
        text = text.replace(phrase, " ")
    for a, b in _WORD_OPS:
        text = re.sub(rf"\b{re.escape(a)}\b", b, text)
    text = text.replace("×", "*").replace("÷", "/")
    # Prefer an explicit arithmetic substring (handles "100/4 nedir")
    m = re.search(r"[\d]+(?:\s*[+\-*/%]\s*[\d().]+)+", text)
    if m:
        cand = re.sub(r"\s+", "", m.group(0))
    else:
        # strip leftover question words then require pure expression
        text = re.sub(
            r"\b(nedir|ne|kac|kaç|eder|yapar|hesapla|sonuc|sonucu|lutfen|lütfen)\b",
            " ",
            text,
        )
        cand = re.sub(r"\s+", "", text)
    if not cand:
        return None
    if not re.fullmatch(r"[\d+\-*/().%]+", cand):
        return None
    if not re.search(r"\d", cand) or not re.search(r"[+\-*/%]", cand):
        return None
    tmp = cand.replace("**", "")
    if re.search(r"[+\-*/%]{2,}", tmp):
        return None
    return cand


def looks_like_math(raw: str) -> bool:
    return extract_math_expr(raw) is not None


def solve_math(raw: str) -> Optional[str]:
    expr = extract_math_expr(raw)
    if not expr:
        return None
    try:
        # ** already in expr; ast Pow handles it
        result = _safe_eval(expr.replace("^", "**") if "^" in expr else expr)
    except Exception:
        return None
    if isinstance(result, float):
        if abs(result - round(result)) < 1e-9:
            result = int(round(result))
        else:
            result = round(result, 8)
    return f"Sonuç: **{result}**\n\n`{expr} = {result}`"


# -------------------- clock / date --------------------

_TIME_HINTS = (
    "saat kac", "saat kaç", "saati soyle", "saati söyle", "what time",
    "bugunun tarihi", "bugünün tarihi", "tarih ne", "hangi gun", "hangi gün",
    "bugun gunlerden", "bugün günlerden", "ne gun", "ne gün",
)


def looks_like_time(raw: str) -> bool:
    t = _norm(raw)
    return any(h.replace("ı", "i").replace("ü", "u") in t or _norm(h) in t for h in _TIME_HINTS) or t in {
        "saat", "tarih", "bugun", "bugün",
    }


def answer_time(raw: str = "") -> str:
    try:
        now = datetime.now(ZoneInfo("Europe/Istanbul"))
        tz = "Türkiye (Europe/Istanbul)"
    except Exception:
        now = datetime.now(timezone.utc)
        tz = "UTC"
    gunler = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    text = _norm(raw)
    if "tarih" in text or "gun" in text:
        return (
            f"Bugün **{now.day:02d}.{now.month:02d}.{now.year}**, "
            f"**{gunler[now.weekday()]}**.\n\n({tz})"
        )
    return (
        f"Saat **{now.hour:02d}:{now.minute:02d}** "
        f"({now.day:02d}.{now.month:02d}.{now.year}, {gunler[now.weekday()]}).\n\n"
        f"Saat dilimi: {tz}"
    )


# -------------------- weather / current → research --------------------

_WEATHER_HINTS = (
    "hava durumu", "hava nasil", "hava nasıl", "hava rapor", "yagmur", "yağmur",
    "sicaklik", "sıcaklık", "weather", "forecast",
)


def looks_like_weather(raw: str) -> bool:
    t = _norm(raw)
    return any(_norm(h) in t for h in _WEATHER_HINTS) or (
        "hava" in t.split() and any(w in t for w in ("bugun", "yarin", "nasil", "durumu"))
    )


def weather_query(raw: str) -> str:
    t = (raw or "").strip()
    # keep city names if present
    return t if len(t) > 3 else "hava durumu Türkiye"


# -------------------- DimAI meta --------------------

_META = (
    "adim sayisi", "adım sayısı", "step", "steps", "ne kadar egit", "ne kadar eğit",
    "model ne", "noral model", "neural", "checkpoint", "kac adim", "kaç adım",
    "kendini egit", "kendini eğit", "ne ogreniyorsun", "ne öğreniyorsun",
)


def looks_like_meta(raw: str) -> bool:
    t = _norm(raw)
    if any(m in t for m in _META):
        return True
    if re.search(r"\b\d{4,}\b", t) and any(w in t for w in ("adim", "step", "ne anlama", "ne demek")):
        return True
    return False


def answer_meta(raw: str = "", steps: Optional[int] = None) -> str:
    step_txt = f"**{steps:,}**" if steps is not None else "yüz binlerce"
    return (
        "DimAI’de **adım (step)**, nöral modelin kaç kez örnek üzerinde "
        f"eğitildiğini gösterir. Şu an yaklaşık {step_txt} adımdayım.\n\n"
        "• **Bilgi tabanı (KB)** → hazır kod/açıklama cevapları\n"
        "• **Öğrenilmiş hafıza** → daha önce araştırıp kaydettiğim bilgiler\n"
        "• **Nöral model** → karakter seviyesinde deneysel üretim (küçük GRU)\n"
        "• **Web araştırması** → olgu sorularında Wikipedia / arama\n\n"
        "Adım sayısı yükseldikçe nöral üretim biraz daha düzenli olur; "
        "asıl güçlü cevaplar KB + araştırma + matematik motorundan gelir."
    )


# -------------------- units (light) --------------------

def convert_units(raw: str) -> Optional[str]:
    t = _norm(raw)
    m = re.search(
        r"(\d+(?:[.,]\d+)?)\s*(km|m|cm|mm|mile|miles|mil|kg|g|c|f|celcius|celsius|fahrenheit)\s*"
        r"(?:to|kac|kaç|in|=)?\s*(km|m|cm|mm|mile|miles|mil|kg|g|c|f|celcius|celsius|fahrenheit)?",
        t,
    )
    if not m:
        return None
    val = float(m.group(1).replace(",", "."))
    src = m.group(2)
    dst = m.group(3)
    table_len = {"km": 1000, "m": 1, "cm": 0.01, "mm": 0.001, "mile": 1609.34, "miles": 1609.34, "mil": 1609.34}
    table_mass = {"kg": 1000, "g": 1}

    def _alias(u: str) -> str:
        if u in ("c", "celcius", "celsius"):
            return "c"
        if u in ("f", "fahrenheit"):
            return "f"
        if u in ("mile", "miles", "mil"):
            return "mile"
        return u

    src, dst = _alias(src), _alias(dst) if dst else None
    if src in ("c", "f") or (dst in ("c", "f") if dst else False):
        if src == "c" and (dst in (None, "f")):
            out = val * 9 / 5 + 32
            return f"**{val}°C** = **{out:.2f}°F**"
        if src == "f" and (dst in (None, "c")):
            out = (val - 32) * 5 / 9
            return f"**{val}°F** = **{out:.2f}°C**"
    if src in table_len and (dst in table_len if dst else True):
        meters = val * table_len[src]
        if not dst:
            dst = "mile" if src == "km" else ("m" if src != "m" else "km")
        out = meters / table_len[dst]
        label = {"mile": "mile"}.get(dst, dst)
        return f"**{val} {src}** = **{out:g} {label}**"
    if src in table_mass and dst in table_mass:
        grams = val * table_mass[src]
        out = grams / table_mass[dst]
        return f"**{val} {src}** = **{out:g} {dst}**"
    return None
