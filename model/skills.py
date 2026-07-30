"""Practical skills that make DimAI strong where the tiny RNN is weak.

Math (incl. Turkish words, roots, percent, comparisons), clock/date,
translation mini-lexicon, DimAI meta, unit conversion — no external AI APIs.
"""
from __future__ import annotations

import ast
import math
import operator
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo


def _norm(text: str) -> str:
    text = (text or "").lower()
    text = text.translate(str.maketrans("çğıöşü", "cgiosu"))
    text = unicodedata.normalize("NFKD", text)
    # preserve != and European decimals before stripping punctuation
    text = text.replace("!=", "⟦ne⟧")
    text = re.sub(r"(\d),(\d)", r"\1.\2", text)
    text = re.sub(r"[^a-z0-9+\-*/=<>.%()^\s⟦⟧]", " ", text)
    text = text.replace("⟦ne⟧", "!=")
    return re.sub(r"\s+", " ", text).strip()


# -------------------- Turkish number words --------------------

_TR_NUM = {
    "sifir": 0, "bir": 1, "iki": 2, "uc": 3, "dort": 4, "bes": 5,
    "alti": 6, "yedi": 7, "sekiz": 8, "dokuz": 9, "on": 10,
    "onbir": 11, "oniki": 12, "onuc": 13, "ondort": 14, "onbes": 15,
    "onalti": 16, "onyedi": 17, "onsekiz": 18, "ondokuz": 19,
    "yirmi": 20, "otuz": 30, "kirk": 40, "elli": 50,
    "altmis": 60, "yetmis": 70, "seksen": 80, "doksan": 90,
    "yuz": 100, "bin": 1000,
}


def _words_to_number(tokens: list[str]) -> Optional[int]:
    if not tokens:
        return None
    total = 0
    current = 0
    used = False
    for t in tokens:
        if t.isdigit():
            current += int(t)
            used = True
            continue
        if t not in _TR_NUM:
            return None
        val = _TR_NUM[t]
        used = True
        if val == 100:
            current = (current or 1) * 100
        elif val == 1000:
            current = (current or 1) * 1000
            total += current
            current = 0
        else:
            current += val
    if not used:
        return None
    return total + current


def _replace_tr_numbers(text: str) -> str:
    """Replace Turkish number phrases with digits (greedy left-to-right).

    Arabic numerals stay as separate tokens (so 'yuzde 20 200' ≠ 220).
    """
    tokens = text.split()
    out: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if re.fullmatch(r"\d+(?:\.\d+)?", tok):
            out.append(tok)
            i += 1
            continue
        matched = None
        for n in range(min(4, len(tokens) - i), 0, -1):
            chunk = tokens[i : i + n]
            # only pure Turkish number-words (no arabic digits mixed)
            if all(t in _TR_NUM for t in chunk):
                val = _words_to_number(chunk)
                if val is not None:
                    matched = str(val)
                    i += n
                    break
        if matched is not None:
            out.append(matched)
        else:
            out.append(tok)
            i += 1
    return " ".join(out)


# -------------------- math --------------------

_WORD_OPS = (
    ("kere", "*"),
    ("carpi", "*"),
    ("arti", "+"),
    ("eksi", "-"),
    ("bolu", "/"),
    ("uzeri", "**"),
    ("plus", "+"),
    ("minus", "-"),
    ("times", "*"),
    ("divided", "/"),
)

_STRIP_PHRASES = (
    "kac eder", "kac yapar", "sonucu ne", "sonuc ne", "hesapla",
    "hesaplar misin", "ne eder", "ne yapar", "esittir",
    "kac", "nedir sonucu", "cevap ne", "dogru mu", "true or false",
    "true or false:",
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
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            left, right = _eval(n.left), _eval(n.right)
            if isinstance(n.op, ast.Pow) and (right > 1000 or left > 10**6):
                raise ValueError("too large")
            return _OPS[type(n.op)](left, right)
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](_eval(n.operand))
        raise ValueError("unsupported")

    return _eval(node)


def _format_num(result) -> str:
    if isinstance(result, float):
        if abs(result - round(result)) < 1e-9:
            result = int(round(result))
        else:
            result = round(result, 8)
    return str(result)


def extract_math_expr(raw: str) -> Optional[str]:
    text = _norm(raw)
    if not text:
        return None
    # European decimals: 3,5 → 3.5 (only digit,digit)
    text = re.sub(r"(\d),(\d)", r"\1.\2", text)
    text = _replace_tr_numbers(text)
    text = re.sub(r"[?]+", " ", text)
    for phrase in _STRIP_PHRASES:
        p = _norm(phrase)
        if len(p) < 2:
            continue
        text = text.replace(p, " ")
    # modulo word BEFORE percent handling (avoid 17 mod 5 → percent)
    text = re.sub(r"\bmod\b", " % ", text)
    for a, b in _WORD_OPS:
        text = re.sub(rf"\b{a}\b", f" {b} ", text)
    text = re.sub(r"(\d)\s*x\s*(\d)", r"\1 * \2", text)
    text = text.replace("×", "*").replace("÷", "/").replace("^", "**")
    text = re.sub(r"\b(kok|sqrt)\s*\(?\s*(-?\d+(?:\.\d+)?)\s*\)?", r" sqrt(\2) ", text)

    # yüzde only with explicit word (not bare a%b from mod)
    mperc = re.search(r"\byuzde\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)", text)
    if mperc:
        return f"({mperc.group(2)}*{mperc.group(1)}/100)"
    mperc2 = re.search(
        r"(\d+(?:\.\d+)?)\s*%\s*(?:of|si|su|nin|inin)\s*(\d+(?:\.\d+)?)",
        text,
    )
    if mperc2:
        return f"({mperc2.group(2)}*{mperc2.group(1)}/100)"

    m = re.search(r"sqrt\((-?\d+(?:\.\d+)?)\)", text)
    if m:
        return f"sqrt({m.group(1)})"

    # Longest math-looking span: allow nested parens + unary minus
    m = re.search(r"[-+]?(?:\d|\()[\d+\-*/%.()\s*]{0,120}[\d)]", text)
    if not m:
        return None
    cand = re.sub(r"\s+", "", m.group(0))
    # trim trailing ops
    cand = cand.rstrip("+-*/%")
    has_op = "**" in cand or bool(re.search(r"[+\-*/%]", cand.replace("**", "")))
    if not has_op:
        return None
    if not re.fullmatch(r"[0-9+\-*/().%]+", cand.replace("**", "*")):
        return None
    # must parse
    try:
        _safe_eval(cand)
    except Exception:
        return None
    return cand


def looks_like_math(raw: str) -> bool:
    t = _norm(raw)
    if extract_math_expr(raw):
        return True
    if re.search(r"\b(kok|sqrt|yuzde|kere|uzeri)\b", t) and re.search(r"\d", t):
        return True
    if _replace_tr_numbers(t) != t and any(op in t for op in ("arti", "eksi", "kere", "bolu", "carpi", "+", "-", "*")):
        return True
    if re.search(r"[<>]=?|==|!=", t) and re.search(r"\d", t):
        return True
    return False


def solve_comparison(raw: str) -> Optional[str]:
    t = _norm(raw)
    t = _replace_tr_numbers(t)
    t = t.replace("x", "*")
    m = re.search(
        r"(-?\d+(?:\.\d+)?)\s*(==|!=|<=|>=|<|>)\s*(-?\d+(?:\.\d+)?)",
        t,
    )
    if not m:
        # "dogru mu 2>3"
        m = re.search(r"(-?\d+(?:\.\d+)?)\s*([<>]=?|==|!=)\s*(-?\d+(?:\.\d+)?)", t)
    if not m:
        return None
    a, op, b = float(m.group(1)), m.group(2), float(m.group(3))
    ops = {
        ">": operator.gt, "<": operator.lt, ">=": operator.ge,
        "<=": operator.le, "==": operator.eq, "!=": operator.ne,
    }
    ok = ops[op](a, b)
    label = "Doğru" if ok else "Yanlış"
    # pretty ints
    as_ = _format_num(a)
    bs_ = _format_num(b)
    return f"**{label}** — `{as_} {op} {bs_}` → **{ok}**"


def solve_math(raw: str) -> Optional[str]:
    # comparisons first
    cmp = solve_comparison(raw)
    if cmp and re.search(r"[<>]=?|==|!=", _norm(raw)):
        return cmp

    # kök specially if extract missed
    t = _norm(raw)
    t = _replace_tr_numbers(t)
    mk = re.search(r"\b(?:kok|sqrt)\s*\(?\s*(\d+(?:\.\d+)?)\s*\)?", t)
    if mk and not re.search(r"[+\-*/]", t.replace("kok", "").replace("sqrt", "")):
        n = float(mk.group(1))
        if n < 0:
            return "Negatif sayının gerçek karekökü yok."
        r = math.sqrt(n)
        return f"Sonuç: **{_format_num(r)}**\n\n`√{ _format_num(n) } = {_format_num(r)}`"

    expr = extract_math_expr(raw)
    if not expr:
        return None
    if expr.startswith("sqrt("):
        n = float(expr[5:-1])
        r = math.sqrt(n)
        return f"Sonuç: **{_format_num(r)}**\n\n`√{_format_num(n)} = {_format_num(r)}`"
    try:
        result = _safe_eval(expr)
    except Exception:
        return None
    return f"Sonuç: **{_format_num(result)}**\n\n`{expr} = {_format_num(result)}`"


# -------------------- clock / date --------------------

_TIME_HINTS = (
    "saat kac", "saati soyle", "what time", "bugunun tarihi", "tarih ne",
    "hangi gun", "bugun gunlerden", "ne gun", "yarin ne gun", "yarin hangi gun",
)


def looks_like_time(raw: str) -> bool:
    t = _norm(raw)
    if any(h in t for h in _TIME_HINTS) or t in {"saat", "tarih", "bugun"}:
        return True
    if "yarin" in t and "gun" in t:
        return True
    if "ayin kaci" in t or "ayin kaçi" in t or ("ayin" in t and "kac" in t):
        return True
    if "bugun" in t and ("kac" in t or "tarih" in t):
        return True
    return False


def answer_time(raw: str = "") -> str:
    try:
        now = datetime.now(ZoneInfo("Europe/Istanbul"))
        tz = "Türkiye (Europe/Istanbul)"
    except Exception:
        now = datetime.now(timezone.utc)
        tz = "UTC"
    gunler = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    aylar = [
        "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
        "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
    ]
    text = _norm(raw)
    if "yarin" in text:
        d = now + timedelta(days=1)
        return f"Yarın **{d.day:02d}.{d.month:02d}.{d.year}**, **{gunler[d.weekday()]}**.\n\n({tz})"
    if "ayin" in text or ("bugun" in text and "kac" in text and "saat" not in text):
        return (
            f"Bugün ayın **{now.day}**'i — "
            f"**{now.day} {aylar[now.month - 1]} {now.year}**, {gunler[now.weekday()]}.\n\n({tz})"
        )
    if "tarih" in text or ("gun" in text and "saat" not in text):
        return (
            f"Bugün **{now.day:02d}.{now.month:02d}.{now.year}**, "
            f"**{gunler[now.weekday()]}**.\n\n({tz})"
        )
    return (
        f"Saat **{now.hour:02d}:{now.minute:02d}** "
        f"({now.day:02d}.{now.month:02d}.{now.year}, {gunler[now.weekday()]}).\n\n"
        f"Saat dilimi: {tz}"
    )


# -------------------- weather --------------------

_WEATHER_HINTS = (
    "hava durumu", "hava nasil", "hava rapor", "weather", "forecast", "yagmur",
    "sicaklik",
)


def looks_like_weather(raw: str) -> bool:
    t = _norm(raw)
    if any(h in t for h in _WEATHER_HINTS):
        return True
    words = set(t.split())
    return "hava" in words and bool(words & {"bugun", "yarin", "nasil", "durumu", "istanbul", "ankara", "izmir"})


def weather_query(raw: str) -> str:
    t = _norm(raw)
    city = None
    for c in ("istanbul", "ankara", "izmir", "bursa", "antalya", "adana", "gaziantep", "konya"):
        if c in t:
            city = c.capitalize()
            break
    if city:
        return f"{city} weather temperature"
    return "Turkey weather today temperature"


# -------------------- translation --------------------

_TR_EN = {
    "merhaba": "hello", "selam": "hi / hello", "tesekkurler": "thank you",
    "tesekkur": "thanks", "lutfen": "please", "evet": "yes", "hayir": "no",
    "gunaydin": "good morning", "iyi geceler": "good night",
    "hos geldin": "welcome", "guzel": "beautiful / nice", "arkadas": "friend",
    "kitap": "book", "su": "water", "ekmek": "bread", "okul": "school",
    "bilgisayar": "computer", "yazilim": "software", "kod": "code",
}
_EN_TR = {v.split(" / ")[0]: k for k, v in _TR_EN.items()}
_EN_TR.update({
    "hello": "merhaba", "hi": "selam", "thanks": "teşekkürler",
    "thank you": "teşekkür ederim", "please": "lütfen", "yes": "evet",
    "no": "hayır", "good morning": "günaydın", "good night": "iyi geceler",
    "friend": "arkadaş", "book": "kitap", "water": "su", "computer": "bilgisayar",
    "code": "kod", "software": "yazılım",
})


def looks_like_translate(raw: str) -> bool:
    t = _norm(raw)
    if any(
        x in t
        for x in (
            "ne demek", "nedir turkce", "turkcesi", "turkce", "english",
            "ingilizce", "ingilizcesi", "cevir", "translate", "meaning of",
        )
    ):
        return True
    return False


def translate(raw: str) -> Optional[str]:
    t = _norm(raw)
    m = re.search(
        r"^(.+?)\s+(ne demek|english|ingilizcesi|ingilizce|turkcesi|turkce)$",
        t,
    )
    if not m:
        m = re.search(r"^(cevir|translate)\s+(.+)$", t)
        if m:
            word = m.group(2).strip()
        else:
            return None
    else:
        word = m.group(1).strip()
    word = re.sub(r"^(kelime|word)\s+", "", word).strip()
    to_tr = any(x in t for x in ("turkce", "turkcesi", "ne demek")) and word in _EN_TR or word in _EN_TR
    if word in _TR_EN and not (word in _EN_TR and "turkce" in t):
        # default TR→EN unless explicitly asking turkish
        if "turkce" in t or "turkcesi" in t:
            pass
        else:
            return f"**{word}** → İngilizce: **{_TR_EN[word]}**"
    if word in _EN_TR:
        return f"**{word}** → Türkçe: **{_EN_TR[word]}**"
    if word in _TR_EN:
        return f"**{word}** → İngilizce: **{_TR_EN[word]}**"
    for en, tr in sorted(_EN_TR.items(), key=lambda x: -len(x[0])):
        if en == word or (len(en) > 2 and en in word):
            return f"**{en}** → Türkçe: **{tr}**"
    for tr, en in sorted(_TR_EN.items(), key=lambda x: -len(x[0])):
        if tr == word or (len(tr) > 2 and tr in word):
            return f"**{tr}** → İngilizce: **{en}**"
    return (
        f"«{word}» için hazır sözlüğümde tam karşılık yok. "
        f"Başka bir kelime dene veya «{word} nedir» diye sor."
    )


# -------------------- meta --------------------

_META = (
    "adim sayisi", "step", "steps", "ne kadar egit", "noral model", "neural",
    "checkpoint", "kac adim", "kendini egit", "ne ogreniyorsun",
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
        "• **Web araştırması** → olgu sorularında Wikipedia / arama\n"
        "• **Beceriler** → matematik, saat, birim, çeviri\n\n"
        "Adım sayısı yükseldikçe nöral üretim biraz daha düzenli olur; "
        "asıl güçlü cevaplar KB + beceriler + araştırmadan gelir."
    )


# -------------------- units --------------------

def convert_units(raw: str) -> Optional[str]:
    t = _norm(raw)
    units = r"km|mm|cm|mile|miles|mil|kg|g|celcius|celsius|fahrenheit|m|c|f"
    m = re.search(rf"(\d+(?:[.,]\d+)?)\s*\b({units})\b", t)
    if not m:
        return None
    val = float(m.group(1).replace(",", "."))
    src = m.group(2)
    rest = t[m.end() :]
    md = re.search(rf"\b({units})\b", rest)
    dst = md.group(1) if md else None
    table_len = {
        "km": 1000, "m": 1, "cm": 0.01, "mm": 0.001,
        "mile": 1609.34, "miles": 1609.34, "mil": 1609.34,
    }
    table_mass = {"kg": 1000, "g": 1}

    def _alias(u: Optional[str]) -> Optional[str]:
        if not u:
            return None
        if u in ("c", "celcius", "celsius"):
            return "c"
        if u in ("f", "fahrenheit"):
            return "f"
        if u in ("mile", "miles", "mil"):
            return "mile"
        return u

    src, dst = _alias(src), _alias(dst)
    if src in ("c", "f") or dst in ("c", "f"):
        if src == "c" and (dst in (None, "f")):
            out = val * 9 / 5 + 32
            return f"**{val}°C** = **{out:.2f}°F**"
        if src == "f" and (dst in (None, "c")):
            out = (val - 32) * 5 / 9
            return f"**{val}°F** = **{out:.2f}°C**"
    if src in table_len:
        meters = val * table_len[src]
        if not dst:
            dst = "mile" if src == "km" else ("km" if src == "mile" else "m")
        if dst not in table_len:
            return None
        out = meters / table_len[dst]
        return f"**{val} {src}** = **{out:g} {dst}**"
    if src in table_mass and dst in table_mass:
        grams = val * table_mass[src]
        out = grams / table_mass[dst]
        return f"**{val} {src}** = **{out:g} {dst}**"
    return None


# -------------------- tiny talk / noise --------------------

_AFFIRM = {"evet", "hayir", "tamam", "ok", "okay", "anladim", "peki", "olur", "yok", "var"}
_CASUAL = {"lol", "lmao", "haha", "hahaha", "hmm", "hm", "hehe", "wow", "nice", "cool", "süper", "super"}


def looks_like_noise(raw: str) -> bool:
    t = (raw or "").strip()
    if not t:
        return True
    if re.fullmatch(r"[.?!\s…🤷😂😅]+", t):
        return True
    if len(t) == 1 and t.isalpha():
        return True
    if re.fullmatch(r"[.\-_*=]+", t):
        return True
    return False


def answer_noise() -> str:
    return (
        "Bir şey yazmanı bekliyorum 🙂\n"
        "Örnek: `2+2 kaç`, `fibonacci yaz`, `karadelik nedir`, `saat kaç`"
    )


def looks_like_affirm(raw: str) -> bool:
    return _norm(raw) in _AFFIRM


def looks_like_casual(raw: str) -> bool:
    return _norm(raw) in _CASUAL


def answer_affirm(raw: str) -> str:
    t = _norm(raw)
    if t in {"evet", "tamam", "ok", "okay", "olur", "peki", "anladim", "var"}:
        return "Tamam. Devam edelim — kod mu, hesap mı, yoksa bir konuyu mu açalım?"
    if t in {"hayir", "yok"}:
        return "Peki. Başka bir şey sorabilirsin; örneğin kod, matematik veya bilgi."
    return "Tamam — sıradaki adım ne olsun?"


def answer_casual(raw: str) -> str:
    t = _norm(raw)
    if t in {"lol", "lmao", "haha", "hahaha", "hehe"}:
        return "😄 Güzel — şimdi ciddi bir şey yapalım mı? Kod, hesap veya bilgi sor."
    if t in {"hmm", "hm"}:
        return "Düşünürken yardımcı olayım: neyin üzerinde takıldın?"
    return "👍 Ne yapmak istersin — kod, matematik veya bir konu?"
