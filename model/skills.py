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
    text = (text or "")
    # Turkish İ/I before lower() — default locale makes İ → i + combining dot
    text = text.replace("İ", "i").replace("I", "i").replace("ı", "i")
    text = text.lower()
    text = text.translate(str.maketrans("çğıöşü", "cgiosu"))
    text = unicodedata.normalize("NFKD", text)
    # preserve != and European decimals before stripping punctuation
    text = text.replace("!=", "⟦ne⟧")
    # European decimal: 3,5 → 3.5 — never inside abs/round/min/max/pow(...)
    if not re.search(r"\b(abs|round|min|max|pow)\s*\(", text):
        text = re.sub(r"(?<![\d.])(\d{1,8}),(\d{1,6})(?![\d.])", r"\1.\2", text)
    # keep commas for function args like round(3.14, 2)
    text = re.sub(r"[^a-z0-9+\-*/=<>.%()^\s,⟦⟧]", " ", text)
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
    allowed_funcs = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "pow": pow,
        "int": int,
        "float": float,
    }

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
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            fname = n.func.id
            if fname not in allowed_funcs or len(n.args) > 3 or n.keywords:
                raise ValueError("unsupported")
            return allowed_funcs[fname](*[_eval(a) for a in n.args])
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
    # Function calls on raw first — commas must stay as arg separators
    raw_l = (raw or "").replace("İ", "i").replace("I", "i").replace("ı", "i").lower()
    mfn0 = re.search(
        r"\b(abs|round|min|max|pow)\s*\(\s*(-?\d+(?:\.\d+)?(?:\s*,\s*-?\d+(?:\.\d+)?)*)\s*\)",
        raw_l,
    )
    if mfn0:
        return f"{mfn0.group(1)}({re.sub(r'\s+', '', mfn0.group(2))})"

    # explicit division by zero before eval
    if re.search(r"/\s*0(?:\.0+)?\b", raw_l) or re.search(r"\bbolu\s+sifir\b", _norm(raw)):
        return "ZERO_DIV"

    text = _norm(raw)
    if not text:
        return None
    # European decimals outside function calls
    if not re.search(r"\b(abs|round|min|max|pow)\s*\(", text):
        text = re.sub(r"(?<![\d.])(\d{1,8}),(\d{1,6})(?![\d.])", r"\1.\2", text)
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

    # abs / round / min / max / pow — function calls (comma or space-separated args)
    mfn = re.search(
        r"\b(abs|round|min|max|pow)\s*\(\s*(-?\d+(?:\.\d+)?(?:\s*,\s*-?\d+(?:\.\d+)?)*)\s*\)",
        text,
    )
    if not mfn:
        mfn = re.search(
            r"\b(abs|round|min|max|pow)\s*\(\s*(-?\d+(?:\.\d+)(?:\s+-?\d+(?:\.\d+)?)+)\s*\)",
            text,
        )
        if mfn:
            args = re.sub(r"\s+", ",", mfn.group(2).strip())
            return f"{mfn.group(1)}({args})"
    if mfn:
        return f"{mfn.group(1)}({mfn.group(2).replace(' ', '')})"

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
    # 2++2 / 5--1 — leave for solve_math to explain (don't silently unary-fold)
    if "++" in cand or "--" in cand:
        return cand
    try:
        _safe_eval(cand)
    except ZeroDivisionError:
        return "ZERO_DIV"
    except Exception:
        return None
    return cand


def looks_like_math(raw: str) -> bool:
    t = _norm(raw)
    if extract_math_expr(raw):
        return True
    if re.search(r"\b(abs|round|min|max|pow)\s*\(", t):
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
    if expr == "ZERO_DIV":
        return "Sıfıra bölme tanımsız — payda 0 olamaz."
    if expr.startswith("sqrt("):
        n = float(expr[5:-1])
        if n < 0:
            return "Negatif sayının gerçek karekökü yok. (Karmaşık sayılar için `√(-1) = i`)"
        r = math.sqrt(n)
        return f"Sonuç: **{_format_num(r)}**\n\n`√{_format_num(n)} = {_format_num(r)}`"
    # invalid operator runs like 2++2
    if re.search(r"[+\-*/%]{2,}", expr.replace("**", "")):
        return "İfade geçersiz gibi görünüyor (üst üste işlem işareti). Örn: `2+2` veya `2**3`."
    try:
        result = _safe_eval(expr)
    except ZeroDivisionError:
        return "Sıfıra bölme tanımsız — payda 0 olamaz."
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
    # "2 saat kaç dakika" süre çevirisi — saat sorusu değil
    if re.search(r"\d+\s*(saat|dakika|saniye|gun|hafta)", t) and re.search(
        r"\b(saat|dakika|saniye|gun|hafta|kac)\b", t
    ):
        if convert_duration(raw):
            return False
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
    "hava durumu", "hava nasil", "hava rapor", "hava kac", "kac derece",
    "weather", "forecast", "yagmur", "sicaklik", "derece", "sicak mi",
    "soguk mu", "yagmur yag", "hava bugun",
)

_WEATHER_CITIES = (
    "istanbul", "ankara", "izmir", "bursa", "antalya", "adana",
    "gaziantep", "konya", "trabzon", "eskisehir", "diyarbakir",
    "samsun", "kayseri", "mersin", "mugla", "aydin", "denizli",
)


def looks_like_weather(raw: str) -> bool:
    t = _norm(raw)
    if any(h in t for h in _WEATHER_HINTS):
        return True
    words = set(t.split())
    if "hava" in words or "weather" in words or "forecast" in words:
        return True
    if ("derece" in words or "sicaklik" in t) and (
        words & set(_WEATHER_CITIES) or "kac" in words or "ne" in words
    ):
        return True
    if words & set(_WEATHER_CITIES) and words & {"sicak", "soguk", "yagmur", "gunesli", "derece"}:
        return True
    return False


def _weather_city(raw: str) -> str:
    t = _norm(raw)
    for c in _WEATHER_CITIES:
        if c in t:
            return c
    return "istanbul"


def weather_query(raw: str) -> str:
    city = _weather_city(raw).capitalize()
    return f"{city} Turkey current weather temperature Celsius"


def answer_weather(raw: str = "") -> Optional[str]:
    """wttr.in JSON — sıcaklığı her zaman °C olarak formatla."""
    city_key = _weather_city(raw)
    city_label = {
        "istanbul": "İstanbul",
        "ankara": "Ankara",
        "izmir": "İzmir",
        "bursa": "Bursa",
        "antalya": "Antalya",
        "adana": "Adana",
        "gaziantep": "Gaziantep",
        "konya": "Konya",
        "trabzon": "Trabzon",
        "eskisehir": "Eskişehir",
        "diyarbakir": "Diyarbakır",
        "samsun": "Samsun",
        "kayseri": "Kayseri",
        "mersin": "Mersin",
        "mugla": "Muğla",
        "aydin": "Aydın",
        "denizli": "Denizli",
    }.get(city_key, city_key.capitalize())

    _DESC_TR = {
        "sunny": "Güneşli",
        "clear": "Açık",
        "partly cloudy": "Parçalı bulutlu",
        "cloudy": "Bulutlu",
        "overcast": "Kapalı",
        "mist": "Sisli",
        "fog": "Sis",
        "light rain": "Hafif yağmur",
        "moderate rain": "Yağmurlu",
        "heavy rain": "Şiddetli yağmur",
        "patchy rain possible": "Yer yer yağmur olasılığı",
        "thundery outbreaks possible": "Gök gürültülü sağanak riski",
        "light snow": "Hafif kar",
        "snow": "Karlı",
    }

    try:
        import requests

        # Do NOT pass lang=tr — wttr sometimes returns inconsistent obs with it.
        # Always read temp_C / FeelsLikeC explicitly (never °F).
        r = requests.get(
            f"https://wttr.in/{city_key.capitalize()},Turkey",
            params={"format": "j1"},
            headers={"User-Agent": "DimAI/1.0 (weather; Celsius)"},
            timeout=6,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        cur = (data.get("current_condition") or [None])[0]
        if not cur:
            return None

        temp_c = cur.get("temp_C")
        feels_c = cur.get("FeelsLikeC")
        humidity = cur.get("humidity")
        wind_km = cur.get("windspeedKmph")
        wind_dir = cur.get("winddir16Point") or ""
        desc_en = ""
        block = cur.get("weatherDesc") or []
        if block and isinstance(block, list):
            desc_en = str(block[0].get("value") or "").strip()
        desc = _DESC_TR.get(desc_en.lower(), desc_en) or "—"

        if temp_c is None:
            return None

        try:
            temp_i = int(round(float(str(temp_c).replace(",", "."))))
            feels_i = (
                int(round(float(str(feels_c).replace(",", "."))))
                if feels_c is not None
                else temp_i
            )
        except (TypeError, ValueError):
            return None

        # Sanity: reject absurd readings / accidental Fahrenheit
        if temp_i < -60 or temp_i > 70:
            return None
        # Classic °F misread for Turkish cities (e.g. 79°F shown as 79)
        if temp_i > 55 and feels_i > 55:
            temp_i = int(round((temp_i - 32) * 5 / 9))
            feels_i = int(round((feels_i - 32) * 5 / 9))

        lines = [
            f"**Hava — {city_label}**",
            "",
            f"• Durum: {desc}",
            f"• Sıcaklık: **{temp_i}°C**",
            f"• Hissedilen: **{feels_i}°C**",
        ]
        if humidity is not None:
            lines.append(f"• Nem: %{humidity}")
        if wind_km is not None:
            try:
                wind_i = int(round(float(wind_km)))
            except (TypeError, ValueError):
                wind_i = wind_km
            lines.append(f"• Rüzgar: {wind_dir} {wind_i} km/s".strip())
        lines += ["", "_Kaynak: wttr.in · Celsius (°C)_"]
        return "\n".join(lines)
    except Exception:
        return None


# -------------------- translation --------------------

_TR_EN = {
    "merhaba": "hello", "selam": "hi / hello", "tesekkurler": "thank you",
    "tesekkur": "thanks", "lutfen": "please", "evet": "yes", "hayir": "no",
    "gunaydin": "good morning", "iyi geceler": "good night",
    "hos geldin": "welcome", "guzel": "beautiful / nice", "arkadas": "friend",
    "kitap": "book", "su": "water", "ekmek": "bread", "okul": "school",
    "bilgisayar": "computer", "yazilim": "software", "kod": "code",
    "harika": "wonderful / great / amazing", "mukemmel": "perfect / excellent",
    "iyi": "good", "kotu": "bad", "buyuk": "big / large", "kucuk": "small",
    "yeni": "new", "eski": "old", "hizli": "fast", "yavas": "slow",
    "kolay": "easy", "zor": "hard / difficult", "onemli": "important",
    "guclu": "strong", "zayif": "weak", "mutlu": "happy", "uzgun": "sad",
    "sicak": "hot / warm", "soguk": "cold", "dogru": "correct / true",
    "yanlis": "wrong / false", "basari": "success", "hata": "error / mistake",
    "soru": "question", "cevap": "answer", "yardim": "help",
    "gun": "day", "gece": "night", "sabah": "morning", "aksam": "evening",
    "bugun": "today", "yarin": "tomorrow", "dun": "yesterday",
    "ev": "home / house", "araba": "car", "insan": "human / person",
    "dunya": "world", "ask": "love", "sevgi": "love / affection",
    "is": "work / job", "para": "money", "zaman": "time",
    "saat": "hour / clock", "dakika": "minute", "tamam": "okay",
    "belki": "maybe", "simdi": "now", "burada": "here", "orada": "there",
    "programlama": "programming", "bilgi": "information", "ornek": "example",
    "fonksiyon": "function", "degisken": "variable", "nasilsin": "how are you",
}
_EN_TR = {v.split(" / ")[0].strip(): k for k, v in _TR_EN.items()}
_EN_TR.update({
    "hello": "merhaba", "hi": "selam", "thanks": "teşekkürler",
    "thank you": "teşekkür ederim", "please": "lütfen", "yes": "evet",
    "no": "hayır", "good morning": "günaydın", "good night": "iyi geceler",
    "friend": "arkadaş", "book": "kitap", "water": "su", "computer": "bilgisayar",
    "code": "kod", "software": "yazılım", "hello world": "merhaba dünya",
    "world": "dünya", "wonderful": "harika", "great": "harika",
    "amazing": "harika", "perfect": "mükemmel", "beautiful": "güzel",
    "nice": "güzel", "good": "iyi", "bad": "kötü", "happy": "mutlu",
    "love": "aşk", "time": "zaman", "today": "bugün", "tomorrow": "yarın",
})


def looks_like_translate(raw: str) -> bool:
    t = _norm(raw)
    return any(
        x in t
        for x in (
            "ne demek", "nedir turkce", "turkcesi", "turkce", "english",
            "ingilizce", "ingilizcesi", "ingilizcede", "turkcede",
            "cevir", "translate", "meaning of",
        )
    )


def translate(raw: str) -> Optional[str]:
    t = _norm(raw)
    word = None
    lang_hint = ""
    # "harika ingilizcede ne demek / nedir"
    m = re.search(
        r"^(.+?)\s+(ingilizcede|turkcede|ingilizcesi|turkcesi|ingilizce|turkce|english)\s*"
        r"(ne demek|nedir|cevir|translate)?$",
        t,
    )
    if m:
        word, lang_hint = m.group(1).strip(), m.group(2)
    if not word:
        m = re.search(
            r"^(.+?)\s*(?:yi|yu|ye|ya|u|i)?\s*"
            r"(turkceye|ingilizceye|turkce|english|ingilizce)\s*(cevir|translate)?$",
            t,
        )
        if m:
            word, lang_hint = m.group(1).strip(), m.group(2)
    if not word:
        m = re.search(r"^(.+?)\s+(ne demek)$", t)
        if m:
            word = m.group(1).strip()
    if not word:
        m = re.search(r"^(cevir|translate)\s+(.+)$", t)
        if m:
            word = m.group(2).strip()
    if not word:
        return None

    word = re.sub(r"^(kelime|word)\s+", "", word).strip()
    word = re.sub(
        r"\b(turkceye|ingilizceye|turkcede|ingilizcede|turkcesi|ingilizcesi|"
        r"turkce|ingilizce|english|cevir|translate|ne demek|nedir)\b",
        " ",
        word,
    )
    word = re.sub(r"\s+", " ", word).strip()
    if not word:
        return None

    want_en = any(
        x in t or x in lang_hint
        for x in ("ingilizce", "ingilizcesi", "ingilizcede", "ingilizceye", "english")
    )
    want_tr = any(
        x in t or x in lang_hint
        for x in ("turkce", "turkcesi", "turkcede", "turkceye")
    ) or ("ne demek" in t and not want_en)

    if word in _TR_EN and (want_en or not want_tr):
        return f"**{word}** → İngilizce: **{_TR_EN[word]}**"
    if word in _EN_TR:
        return f"**{word}** → Türkçe: **{_EN_TR[word]}**"
    if word in _TR_EN:
        return f"**{word}** → İngilizce: **{_TR_EN[word]}**"
    for en, tr in sorted(_EN_TR.items(), key=lambda x: -len(x[0])):
        if en == word:
            return f"**{en}** → Türkçe: **{tr}**"
    for tr, en in sorted(_TR_EN.items(), key=lambda x: -len(x[0])):
        if tr == word:
            return f"**{tr}** → İngilizce: **{en}**"
    if "hello world" in word:
        return "**hello world** → Türkçe: **merhaba dünya**"
    return (
        f"«{word}» için hazır sözlüğümde tam karşılık yok. "
        f"Başka kelime dene — örn. `güzel İngilizcede ne demek`."
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

_DURATION = {
    "saniye": 1,
    "dakika": 60,
    "saat": 3600,
    "gun": 86400,
    "hafta": 604800,
}


def convert_duration(raw: str) -> Optional[str]:
    """2 saat kaç dakika → 120 dakika."""
    t = _norm(raw)
    m = re.search(
        r"(\d+(?:[.,]\d+)?)\s*(saat|dakika|saniye|gun|hafta)\s*"
        r"(?:kac|ne kadar)?\s*(saat|dakika|saniye|gun|hafta)?",
        t,
    )
    if not m:
        return None
    val = float(m.group(1).replace(",", "."))
    src = m.group(2)
    dst = m.group(3)
    # "saat kaç" clock questions: bare "saat kaç" without number already excluded
    if src == "saat" and not dst and "dakika" not in t and "saniye" not in t and "gun" not in t:
        # "2 saat" alone is ambiguous — only convert when target unit present
        return None
    if not dst:
        # infer common target
        if src == "saat":
            dst = "dakika"
        elif src == "dakika":
            dst = "saniye"
        elif src == "gun":
            dst = "saat"
        else:
            return None
    if src not in _DURATION or dst not in _DURATION:
        return None
    seconds = val * _DURATION[src]
    out = seconds / _DURATION[dst]
    return f"**{_format_num(val)} {src}** = **{_format_num(out)} {dst}**"


def convert_units(raw: str) -> Optional[str]:
    dur = convert_duration(raw)
    if dur:
        return dur
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
        "Örnek: `2+2 kaç`, `todo yaz`, `karadelik nedir`, `saat kaç`"
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


# -------------------- special codes (exact message only) --------------------

_SPECIAL_CODES = {
    "kk22": "Facebook olan Kaan!!!",
    "kk 22": "Facebook olan Kaan!!!",
    "cnrbsk11": "Çınar Baskın!",
    "efito": "Efe Alsancak!!!",
    "kettle": "Göksel Derin SUyolcu hahaha!!",
    "saral": "Ali Abiiii!!!",
    "kronik": "w1 kronik void",
    "angel": "triple whopper",
}


def looks_like_special_code(raw: str) -> bool:
    """Only the whole message — not when the word appears inside a sentence."""
    t = (raw or "").strip().lower()
    return t in _SPECIAL_CODES


def answer_special_code(raw: str = "") -> str:
    t = (raw or "").strip().lower()
    return _SPECIAL_CODES.get(t, "")
