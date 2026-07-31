"""First-principles software design — architecture before code.

DimAI Phase 3: think like a senior engineer. Produce a DesignSpec from the
user request and project context. Never starts from a tutorial paste.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional, Sequence


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower().replace("ı", "i").replace("İ", "i")
    text = re.sub(r"[^\w\s+#./-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


STOP = {
    "bir", "bana", "benim", "icin", "ile", "ve", "veya", "kod", "kodu", "code",
    "yaz", "write", "olustur", "uret", "generate", "yap", "lutfen", "please",
    "ornek", "ornegi", "example", "goster", "show", "program", "script",
    "fonksiyon", "function", "class", "python", "javascript", "basit", "mini",
}


@dataclass
class ModuleSpec:
    name: str
    responsibility: str
    public_api: list[str] = field(default_factory=list)


@dataclass
class DesignSpec:
    """Internal architecture plan produced before any code is written."""

    goal: str
    problem_type: str  # algorithm | game | cli_app | library | api | data_pipeline | ui
    language: str
    modules: list[ModuleSpec] = field(default_factory=list)
    data_model: list[str] = field(default_factory=list)
    invariants: list[str] = field(default_factory=list)
    edge_cases: list[str] = field(default_factory=list)
    non_goals: list[str] = field(default_factory=list)
    architecture_notes: list[str] = field(default_factory=list)
    domain_keywords: list[str] = field(default_factory=list)
    known_domain: str = ""  # optional match key for specialized composers
    confidence: float = 0.6
    project_fit: str = ""

    def summary_lines(self, *, language: str = "tr") -> list[str]:
        if language == "en":
            lines = [
                f"Goal: {self.goal}",
                f"Shape: {self.problem_type} ({self.language})",
                "Modules:",
            ]
            for m in self.modules:
                lines.append(f"  • {m.name} — {m.responsibility}")
            if self.data_model:
                lines.append("Data: " + "; ".join(self.data_model[:4]))
            if self.architecture_notes:
                lines.append("Decisions: " + "; ".join(self.architecture_notes[:3]))
            return lines
        lines = [
            f"Hedef: {self.goal}",
            f"Şekil: {self.problem_type} ({self.language})",
            "Modüller:",
        ]
        for m in self.modules:
            lines.append(f"  • {m.name} — {m.responsibility}")
        if self.data_model:
            lines.append("Veri: " + "; ".join(self.data_model[:4]))
        if self.architecture_notes:
            lines.append("Kararlar: " + "; ".join(self.architecture_notes[:3]))
        return lines


# Domain detectors → specialized but still design-driven composers
_DOMAIN_HINTS: list[tuple[str, tuple[str, ...]]] = [
    ("3d", ("3d", "raycast", "pseudo 3d", "pseudo-3d")),
    ("rps", ("tas kagit", "tas-kagit", "rock paper", "rps")),
    ("hangman", ("adam asmaca", "hangman")),
    ("tictactoe", ("xox", "tic tac", "tic-tac", "tictactoe")),
    ("guess", ("tahmin", "guess", "sayi tut")),
    ("todo", ("todo", "yapilacak", "gorev list", "to do", "checklist")),
    ("calculator", ("hesap makine", "calculator", "calc ")),
    ("password", ("sifre", "password", "passwd")),
    ("fastapi", ("fastapi",)),
    ("flask", ("flask", "rest api", "api yaz", "endpoint")),
    ("chatbot", ("chatbot", "sohbet bot", "chat bot")),
    ("quiz", ("quiz", "soru cevap", "trivia")),
    ("csv", ("csv",)),
    ("http", ("http get", "http iste", "request get", "url cek", "url çek")),
    ("json_crud", ("json", "crud")),
    ("email", ("email", "e-posta", "eposta", "mail dogru")),
    ("binary_search", ("binary search", "ikili ara")),
    ("fibonacci", ("fibonacci", "fibonacchi", "fibo")),
    ("sort", ("sort", "sirala", "siralama", "bubble", "quick sort")),
    ("countdown", ("geri say", "countdown", "geri sayim")),
    ("unit", ("birim", "donustur", "convert")),
    ("scrape", ("scrape", "kazi", "kazı", "html parse", "baslik cek")),
    ("file_stats", ("dosya", "file stat", "satir say")),
    ("react", ("react", "usestate", "component", "sayac yaz", "counter")),
    ("html", ("html", "landing", "web sayfa")),
    ("sql", ("sql", "schema", "tablo olustur")),
]


def _detect_lang(text: str) -> str:
    n = _norm(text)
    if any(x in n for x in ("javascript", " js", "js ", "node", "react", "typescript", " ts")):
        return "javascript"
    if "html" in n or "css" in n:
        return "html"
    if "sql" in n:
        return "sql"
    if "bash" in n or "shell" in n:
        return "bash"
    if "java" in n and "javascript" not in n:
        return "java"
    return "python"


def _keywords(text: str) -> list[str]:
    return [w for w in _norm(text).split() if w and w not in STOP and len(w) > 1]


def _match_domain(n: str) -> str:
    for name, keys in _DOMAIN_HINTS:
        if any(k in n for k in keys):
            return name
    return ""


def _problem_type(n: str, domain: str) -> str:
    if domain in {"rps", "hangman", "tictactoe", "guess", "quiz"}:
        return "game"
    if domain in {"flask", "fastapi"}:
        return "api"
    if domain in {"react", "html"}:
        return "ui"
    if domain in {"csv", "file_stats", "scrape", "http"}:
        return "data_pipeline"
    if domain in {"binary_search", "fibonacci", "sort", "email", "unit", "password", "countdown"}:
        return "algorithm"
    if domain in {"todo", "chatbot", "calculator", "json_crud"}:
        return "cli_app"
    if any(x in n for x in ("api", "endpoint", "server", "flask", "fastapi")):
        return "api"
    if any(x in n for x in ("oyun", "game", "play")):
        return "game"
    # software library — not "kütüphane ödünç" style domain apps
    if any(x in n for x in ("modul yaz", "module yaz", "utility", "util yaz", "yardimci fonksiyon")):
        return "library"
    if "library" in n and "book" not in n and "odunc" not in n and "kitap" not in n:
        return "library"
    if any(x in n for x in ("pipeline", "parse", "filtre", "filter", "csv", "json")):
        return "data_pipeline"
    if any(x in n for x in ("algoritma", "algorithm", "search", "sort", "recursive")):
        return "algorithm"
    return "cli_app"


def design(
    message: str,
    *,
    project_context: str = "",
    prior_code: str = "",
    improve: bool = False,
) -> DesignSpec:
    """Architect the solution before implementation."""
    raw = (message or "").strip()
    n = _norm(raw)
    lang = _detect_lang(n)
    kws = _keywords(raw)
    domain = _match_domain(n)
    ptype = _problem_type(n, domain)

    goal = raw[:200] if raw else "small runnable tool"
    if improve and prior_code:
        goal = f"Improve existing system toward: {raw or 'cleaner modular design'}"

    modules: list[ModuleSpec] = []
    data_model: list[str] = []
    invariants: list[str] = []
    edge_cases: list[str] = []
    notes: list[str] = [
        "Design-first: no tutorial paste; compose for this request.",
        "Separate domain logic from I/O (SOLID: SRP).",
        "Prefer stdlib over new dependencies.",
    ]
    non_goals = [
        "Do not copy GitHub/tutorial layouts wholesale",
        "Do not invent unrelated features (YAGNI)",
    ]

    if ptype == "game":
        modules = [
            ModuleSpec("rules", "Pure game rules and win/draw detection", ["evaluate", "legal_moves"]),
            ModuleSpec("state", "Mutable session state / scoreboard", ["reset", "apply"]),
            ModuleSpec("cli", "User I/O loop only", ["main"]),
        ]
        data_model = ["SessionState", "Move | Choice", "Score"]
        invariants = ["Rules module has no input()/print()", "Invalid input never corrupts state"]
        edge_cases = ["empty input", "quit command", "repeated play"]
        notes.append("Game: keep RNG at the boundary; rules stay deterministic where possible.")
    elif ptype == "api":
        modules = [
            ModuleSpec("models", "Request/response shapes", ["ItemIn", "Item"]),
            ModuleSpec("store", "In-memory repository", ["list", "add", "remove"]),
            ModuleSpec("routes", "HTTP handlers thin over store", ["health", "crud"]),
        ]
        data_model = ["Item(id, title, created_at)", "Store: dict[int, Item]"]
        invariants = ["Handlers validate then delegate", "IDs monotonic"]
        edge_cases = ["missing body", "unknown id → 404"]
        notes.append("API: repository pattern; no business rules inside route decorators.")
    elif ptype == "data_pipeline":
        modules = [
            ModuleSpec("io", "Read/write paths", ["load", "save"]),
            ModuleSpec("transform", "Pure transforms", ["filter", "map"]),
            ModuleSpec("cli", "Argument wiring", ["main"]),
        ]
        data_model = ["Record: dict[str, str]", "PipelineConfig"]
        invariants = ["Transforms are pure", "IO failures raise clear errors"]
        edge_cases = ["missing file", "empty input", "bad encoding"]
    elif ptype == "algorithm":
        modules = [
            ModuleSpec("core", "Algorithm implementation", ["run / compute"]),
            ModuleSpec("demo", "Small driver with asserts or prints", ["main"]),
        ]
        data_model = ["Input domain values", "Result type"]
        invariants = ["Clear time/space intent in comments", "Handle empty / edge inputs"]
        edge_cases = ["empty collection", "single element", "duplicates"]
        notes.append("Algorithm: teachable, original implementation — not a copy-paste snippet farm.")
    elif ptype == "ui":
        modules = [
            ModuleSpec("state", "UI state hooks / variables", ["useState / state"]),
            ModuleSpec("view", "Render tree", ["Component"]),
        ]
        data_model = ["Component props", "Local state"]
        notes.append("UI: minimal, accessible structure; no framework tutorial boilerplate dump.")
    elif ptype == "library":
        modules = [
            ModuleSpec("api", "Public functions/classes", ["public entrypoints"]),
            ModuleSpec("internal", "Helpers not exported", ["_helpers"]),
        ]
        data_model = ["Primary value object"]
        notes.append("Library: small surface area; document with docstrings.")
    else:  # cli_app
        modules = [
            ModuleSpec("domain", "Entities and invariants", ["dataclasses"]),
            ModuleSpec("service", "Application use-cases", ["add", "list", "remove"]),
            ModuleSpec("persistence", "Optional storage boundary", ["load", "save"]),
            ModuleSpec("cli", "REPL / argparse I/O", ["main"]),
        ]
        data_model = ["Entity with clear fields from request keywords", "AppService facade"]
        invariants = ["CLI does not embed business rules", "Persistence is swappable"]
        edge_cases = ["empty store", "unknown command", "bad user input"]

    if project_context:
        notes.append(f"Fit to ongoing project context: {project_context[:120]}")
    if prior_code and improve:
        notes.append("Evolve prior code; preserve intent; raise structure (modules, errors, main).")
        non_goals.append("Do not rewrite into an unrelated app")

    # Confidence: clearer domain → higher
    conf = 0.55
    if domain:
        conf = 0.85
    elif kws:
        conf = 0.7
    if improve and prior_code:
        conf = max(conf, 0.75)

    title_bits = kws[:5] or ["uygulama"]
    if not goal or goal in {"kod yaz", "write code", "program yaz"}:
        goal = f"Runnable {ptype} around: {' '.join(title_bits)}"

    return DesignSpec(
        goal=goal,
        problem_type=ptype,
        language=lang,
        modules=modules,
        data_model=data_model,
        invariants=invariants,
        edge_cases=edge_cases,
        non_goals=non_goals,
        architecture_notes=notes,
        domain_keywords=kws,
        known_domain=domain,
        confidence=conf,
        project_fit=project_context[:160],
    )


def compare_alternatives(spec: DesignSpec) -> list[str]:
    """Brief multi-solution compare (reasoning aid)."""
    alts = []
    if spec.problem_type == "cli_app":
        alts = [
            "A) Single-file layered CLI (chosen: simplest to ship)",
            "B) Package with src/ — overkill for one-shot request",
            "C) GUI — rejected unless UI explicitly asked",
        ]
    elif spec.problem_type == "api":
        alts = [
            "A) In-memory repo + thin routes (chosen)",
            "B) DB-backed — deferred until persistence requested",
            "C) Full auth microservice — YAGNI",
        ]
    elif spec.problem_type == "game":
        alts = [
            "A) Rules/state/cli split (chosen)",
            "B) One giant loop — harder to extend",
            "C) Async network multiplayer — out of scope",
        ]
    else:
        alts = [
            "A) Minimal modular single file (chosen)",
            "B) Multi-package layout — deferred",
        ]
    return alts
