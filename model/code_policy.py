"""First-principles coding policy for DimAI.

Enforces senior-engineer behavior: design before code, invent for this
project, never hunt the web for full source implementations.
"""
from __future__ import annotations

from dataclasses import dataclass


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


def should_invent(known_domain: str, keywords: list[str]) -> bool:
    """True → compose original system; False → DimAI-owned specialized demo OK."""
    if not known_domain:
        return True
    # Custom domain words beyond the demo label → invent
    demo_tokens = {
        "todo", "rps", "hangman", "guess", "quiz", "chatbot", "flask", "fastapi",
        "password", "calculator", "fibonacci", "sort", "react", "html", "sql",
        "3d", "csv", "http", "email", "unit", "countdown", "scrape", "file_stats",
        "json_crud", "binary_search", "tictactoe", "tas", "kagit", "makas",
        "adam", "asmaca", "xox", "tahmin", "hesap", "makine", "sifre",
        "rest", "endpoint", "api", "sohbet", "bot", "trivia", "crud", "eposta",
        "ikili", "ara", "sirala", "siralama", "geri", "say", "birim",
        "donustur", "convert", "kazi", "dosya", "sayac", "counter", "landing",
        "schema", "tablo", "checklist", "yapilacak", "yapilacaklar", "gorev",
        "list", "raycast", "pseudo",
    }
    filler = {
        "yaz", "yap", "olustur", "uret", "write", "make", "create", "kod",
        "code", "oyun", "game", "program", "app", "bir", "bana", "lutfen",
        "sistemi", "sistem", "uygulama", "mini", "basit", "ornegi", "ornek",
        "script", "cli", "tool", "liste", "listesi", "lists", "list",
    }
    extras = [
        w for w in keywords
        if w not in demo_tokens and w not in filler and w != known_domain
    ]
    # Domain apps that are never tutorial demos — always invent
    invent_signals = {
        "stok", "envanter", "inventory", "odunc", "kutuphane", "kitap",
        "musteri", "siparis", "fatura", "rezervasyon", "randevu", "personel",
        "maas", "bordro", "depo", "irsaliye", "cari", "muhasebe", "klinik",
        "hasta", "ogrenci", "not", "devamsizlik", "takvim", "ajanda",
        "blog", "forum", "auth", "login", "kayit", "abonelik",
    }
    if any(w in invent_signals for w in keywords) or any(
        s in " ".join(keywords) for s in invent_signals
    ):
        return True
    # e.g. "stok takip todo" has extras → invent; bare "todo yaz" → demo OK
    return len(extras) >= 1


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
