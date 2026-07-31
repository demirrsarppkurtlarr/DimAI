"""First-principles coding policy for DimAI.

Enforces senior-engineer behavior: design before code, invent for this
project, never hunt the web for full source implementations.

Only invent when the user named a concrete software domain.
Capability / meta prompts ("bildiğin bütün bilginle kod yaz") must clarify,
never become Entity field names or class names.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

FORBIDDEN_FIRST_MOVES = (
    "search github for complete source",
    "copy tutorial repository structure",
    "paste stackoverflow snippet as the whole app",
)


@dataclass
class CodingPolicy:
    design_first: bool = True
    allow_web_for_full_source: bool = False
    prefer_stdlib: bool = True
    require_modules: bool = True
    require_review: bool = True
    invent_for_project: bool = True


DEFAULT_POLICY = CodingPolicy()

# Conversational / epistemic fillers — never domain nouns or identifiers.
META_FILLER = frozenset({
    "bildigin", "bildiğin", "bildiklerin", "butun", "bütün", "bilginle",
    "bilgin", "bilgi", "bilgini", "butunu", "bütünü", "tum", "tüm",
    "hepsi", "hepsini", "hepsinle", "hersey", "herşey", "herseyi", "herşeyi",
    "kullanarak", "kullan", "yaz", "yazilim", "yazılım", "kod", "kodu", "code",
    "program", "uygulama", "app", "proje", "project", "ornek", "örnek", "ornegi",
    "demo", "template", "sablon", "şablon", "basit", "guzel", "güzel", "mini",
    "tam", "full", "komple", "kompleks", "advanced", "modern", "professional",
    "lutfen", "lütfen", "rica", "ederim", "bana", "benim", "icin", "için",
    "bir", "bi", "the", "a", "an", "ve", "ile", "olan", "gibi", "kadar",
    "yap", "olustur", "oluştur", "hazirla", "hazırla", "uret", "üret", "generate",
    "ver", "goster", "göster", "anlat", "acikla", "açıkla", "soyle", "söyle",
    "nedir", "nasil", "nasıl", "neden", "ne", "mi", "mı", "mu", "mü",
    "senin", "sen", "ben", "biz", "dimai", "ai", "zeka",
    "yetenegin", "yeteneğin", "yeteneginle", "becerin", "gucun", "gücün",
    "kapasiten", "elinden", "gelenin", "iyisiyle",
    "maximum", "maksimum", "en", "iyi", "guclu", "güçlü", "best", "ability", "power",
    "knowledge", "know", "all", "your", "with", "using", "write", "create",
    "make", "build", "please", "me", "my", "for", "this", "that",
    "something", "anything", "everything", "herhangi", "sey", "şey",
    "request", "istek", "talep", "prompt", "soru", "cevap",
    "chatgpt", "claude", "gemini", "sistemi", "sistem", "script", "tool",
    "liste", "listesi", "lists",
})

SOFTWARE_NOUNS = frozenset({
    "todo", "stok", "stock", "inventory", "envanter", "faturalama", "fatura",
    "invoice", "crm", "blog", "auth", "login", "chat", "mesaj", "message",
    "notes", "not", "defter", "kitap", "book", "library", "kutuphane", "kütüphane",
    "musteri", "müşteri", "siparis", "sipariş", "order", "sepet", "cart",
    "ecommerce", "eticaret", "bank", "banka", "hesap", "account",
    "wallet", "cuzdan", "cüzdan", "oyun", "game", "rpg", "fps", "platformer",
    "puzzle", "labirent", "maze", "tetris", "snake", "pong", "flappy",
    "dashboard", "panel", "admin", "api", "rest", "graphql", "websocket",
    "bot", "scraper", "crawler", "parser", "cli", "repl", "server", "client",
    "flask", "django", "fastapi", "express", "react", "vue", "next",
    "calculator", "hesapmakinesi", "timer", "alarm", "calendar", "takvim",
    "gallery", "galeri", "music", "muzik", "müzik", "player", "video",
    "weather", "hava", "news", "haber", "rss", "markdown", "editor",
    "kanban", "board", "ticket", "issue", "bug", "tracker", "takip",
    "quiz", "anket", "survey", "poll", "forum", "wiki", "cms",
    "pomodoro", "habit", "aliskanlik", "alışkanlık", "fitness", "diet",
    "recipe", "tarif", "restaurant", "restoran", "menu", "menü",
    "hotel", "otel", "booking", "rezervasyon", "randevu", "flight", "ucus", "uçuş",
    "taxi", "taksi", "map", "harita", "gps", "iot", "sensor",
    "ml", "nlp", "vision", "image", "resim", "foto", "photo",
    "pdf", "csv", "excel", "spreadsheet", "report", "rapor",
    "encrypt", "sifrele", "şifrele", "hash", "jwt", "oauth",
    "queue", "kuyruk", "cache", "redis", "postgres", "sqlite", "mongo",
    "docker", "kubernetes", "pipeline",
    "portfolio", "landing", "landingpage", "saas", "billing", "abonelik",
    "subscription", "payment", "odeme", "ödeme", "stripe",
    "email", "mail", "smtp", "notification", "bildirim",
    "scheduler", "cron", "worker", "job",
    "graph", "grafik", "chart", "plot", "visualization",
    "translator", "ceviri", "çeviri", "dictionary", "sozluk", "sözlük",
    "password", "sifre", "şifre", "vault", "manager", "yonetici", "yönetici",
    "file", "dosya", "folder", "klasor", "klasör", "upload", "download",
    "search", "arama", "filter", "filtre", "sort", "sirala", "sırala",
    "odunc", "ödünç", "personel", "maas", "maaş", "bordro", "depo", "irsaliye",
    "cari", "muhasebe", "klinik", "hasta", "ogrenci", "öğrenci", "devamsizlik",
    "ajanda", "kayit", "kayıt",
})

CAPABILITY_PHRASES = (
    r"bildigin\s+butun\s+bilgin",
    r"bildiğin\s+bütün\s+bilgin",
    r"bildigin\s+butun",
    r"bildiğin\s+bütün",
    r"tum\s+bilgin",
    r"tüm\s+bilgin",
    r"butun\s+bilgin",
    r"bütün\s+bilgin",
    r"all\s+your\s+knowledge",
    r"with\s+all\s+your\s+knowledge",
    r"using\s+everything\s+you\s+know",
    r"en\s+iyi\s+sekilde",
    r"en\s+iyi\s+şekilde",
    r"maximum\s+yetene",
    r"maksimum\s+yetene",
    r"butun\s+gucun",
    r"bütün\s+gücün",
    r"her\s+seyini\s+kullan",
    r"her\s+şeyini\s+kullan",
)

_WORD = re.compile(r"[a-zA-ZçğıöşüÇĞİÖŞÜ0-9_\-]{2,}")

_DEMO_TOKENS = frozenset({
    "todo", "rps", "hangman", "guess", "quiz", "chatbot", "flask", "fastapi",
    "password", "calculator", "fibonacci", "sort", "react", "html", "sql",
    "3d", "csv", "http", "email", "unit", "countdown", "scrape", "file_stats",
    "json_crud", "binary_search", "tictactoe", "tas", "kagit", "makas",
    "adam", "asmaca", "xox", "tahmin", "hesap", "makine", "sifre",
    "rest", "endpoint", "api", "sohbet", "bot", "trivia", "crud", "eposta",
    "ikili", "ara", "sirala", "siralama", "geri", "say", "birim",
    "donustur", "convert", "kazi", "dosya", "sayac", "counter", "landing",
    "schema", "tablo", "checklist", "yapilacak", "yapilacaklar", "gorev",
    "list", "raycast", "pseudo", "koridor", "oyunu", "seviyeli", "sayi", "sayısı",
})

# Shape words: count as concrete domain for invent-from-scratch, but not as
# "extras" that force invent over a matched specialized demo.
_SHAPE_FILLER = frozenset({
    "oyun", "game", "program", "app", "cli", "tool", "sistem", "sistemi",
    "uygulama", "script", "liste", "listesi", "mini", "basit",
})

_INVENT_SIGNALS = frozenset({
    "stok", "envanter", "inventory", "odunc", "kutuphane", "kitap",
    "musteri", "siparis", "fatura", "rezervasyon", "randevu", "personel",
    "maas", "bordro", "depo", "irsaliye", "cari", "muhasebe", "klinik",
    "hasta", "ogrenci", "not", "devamsizlik", "takvim", "ajanda",
    "blog", "forum", "auth", "login", "kayit", "abonelik", "takip",
    "labirent", "faturalama",
})


def _norm(text: str) -> str:
    t = (text or "").casefold()
    return t.replace("İ", "i").replace("I", "ı")


def is_capability_prompt(text: str) -> bool:
    """True when the user asks DimAI to 'use all knowledge' without a domain."""
    t = _norm(text)
    return any(re.search(p, t) for p in CAPABILITY_PHRASES)


def concrete_keywords(text: str, extra_stop: Iterable[str] | None = None) -> list[str]:
    """Tokens that can safely name modules / fields — meta fillers stripped."""
    stop = set(META_FILLER)
    if extra_stop:
        stop |= {str(s).casefold() for s in extra_stop}
    out: list[str] = []
    seen: set[str] = set()
    for m in _WORD.finditer(text or ""):
        w = m.group(0).casefold()
        if w in stop or w.isdigit() or len(w) < 2:
            continue
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out[:12]


def has_concrete_domain(
    text: str,
    known_domain: str = "",
    keywords: Iterable[str] | None = None,
) -> bool:
    if (known_domain or "").strip():
        return True
    kws = list(keywords) if keywords is not None else concrete_keywords(text)
    for k in kws:
        kk = k.casefold().replace("-", "")
        if kk in SOFTWARE_NOUNS or k.casefold() in SOFTWARE_NOUNS:
            return True
        if kk in _INVENT_SIGNALS or k.casefold() in _INVENT_SIGNALS:
            return True
    return False


def is_demo_request(text: str) -> bool:
    t = _norm(text)
    return any(
        x in t
        for x in (
            "ornek", "örnek", "demo", "template", "sablon", "şablon",
            "basit", "tutorial", "ogretici", "öğretici", "ornek kod", "örnek kod",
        )
    )


def should_invent(
    known_domain: str,
    keywords: Iterable[str] | None = None,
    text: str = "",
) -> bool:
    """True → compose original system; False → specialized demo OK or clarify.

    Empty known_domain + only meta tokens → False (caller clarifies instead of
    nonsense CRUD named after conversational words).
    """
    kws_raw = [str(k) for k in (keywords or []) if k]
    kws = [k for k in kws_raw if k.casefold() not in META_FILLER]
    if not kws and text:
        kws = concrete_keywords(text)

    if text and is_capability_prompt(text) and not has_concrete_domain(text, known_domain, kws):
        return False

    if not (known_domain or "").strip():
        # No catalog domain: invent only with real nouns left.
        if not kws:
            return False
        return True

    # Known demo domain — invent when extras / invent signals present.
    if any(w.casefold() in _INVENT_SIGNALS for w in kws) or any(
        s in " ".join(k.casefold() for k in kws) for s in _INVENT_SIGNALS
    ):
        return True
    extras = [
        w for w in kws
        if w.casefold() not in _DEMO_TOKENS
        and w.casefold() not in _SHAPE_FILLER
        and w.casefold() != known_domain.casefold()
    ]
    return len(extras) >= 1


def needs_topic_clarify(text: str, known_domain: str = "", keywords: Iterable[str] | None = None) -> bool:
    """Coding ask with no concrete topic — ask instead of inventing garbage."""
    kws = list(keywords) if keywords is not None else concrete_keywords(text)
    kws = [k for k in kws if k.casefold() not in META_FILLER]
    if (known_domain or "").strip():
        return False
    if has_concrete_domain(text, known_domain, kws):
        return False
    if is_capability_prompt(text):
        return True
    # Meta-only / empty after stripping (e.g. leftover fluff nouns)
    return not kws


def clarify_concrete_topic(text: str = "") -> str:
    return (
        "«bildiğin bütün bilginle» tek başına bir yazılım konusu değil — "
        "o ifadeyi sınıf/alan adı yapmam.\n\n"
        "Ne yazmamı istediğini **somut** söyle, örneğin:\n"
        "• `stok takip CLI yaz`\n"
        "• `3D labirent oyunu yap`\n"
        "• `Flask todo API yaz`\n"
        "• `faturalama sistemi tasarla`\n\n"
        "Konuyu ver; mimariyi ve kodu ona göre üreteyim."
    )


def engineer_preamble(language: str = "tr") -> str:
    if language == "en":
        return (
            "Engineering approach: architecture first, modules with single "
            "responsibilities, stdlib-first, no tutorial paste, review before send."
        )
    return (
        "Mühendislik yaklaşımı: önce mimari, tek sorumluluklu modüller, "
        "stdlib öncelikli, tutorial yapıştırması yok, göndermeden önce gözden geçirme."
    )
