"""Implement DesignSpec as original, modular, production-minded code.

Composes systems from first principles for DimAI. Specialized domains may
delegate to proven DimAI generators, but always under an architecture plan —
never as an unexplained tutorial dump.
"""
from __future__ import annotations

import re
from typing import Optional

from model.code_design import DesignSpec, ModuleSpec


def _slug(words: list[str], default: str = "app") -> str:
    parts = [re.sub(r"[^a-z0-9_]", "", w.lower()) for w in words]
    parts = [p for p in parts if p and not p.isdigit()]
    if not parts:
        return default
    name = "_".join(parts[:3])
    if name[0].isdigit():
        name = "app_" + name
    return name[:40]


def _class_name(slug: str) -> str:
    return "".join(p.capitalize() for p in slug.split("_")) or "App"


def _reply_for(spec: DesignSpec, *, language: str = "tr") -> str:
    lines = spec.summary_lines(language=language)
    if language == "en":
        head = "Designed first, then implemented for your request:"
    else:
        head = "Önce mimariyi kurdum, sonra bu isteğe özel uyguladım:"
    return head + "\n" + "\n".join(lines)


def implement(spec: DesignSpec, *, user_language: str = "tr") -> dict:
    """Turn a DesignSpec into runnable code + engineer-style reply.

    Invents project-specific systems by default. Specialized DimAI demos are
    used only for bare classic requests (e.g. plain `todo yaz`), never as a
    substitute for inventing around the user's domain words.
    """
    from model.code_policy import engineer_preamble, should_invent

    invent = should_invent(spec.known_domain, list(spec.domain_keywords))
    design_note = _reply_for(spec, language=user_language)
    preamble = engineer_preamble(user_language)

    if spec.known_domain and not invent:
        specialized = _specialize(spec)
        if specialized:
            reply, code, lang = specialized
            return {
                "reply": preamble + "\n\n" + design_note + "\n\n" + reply,
                "code": code.strip() + "\n",
                "lang": lang,
                "source": "codegen",
                "design": {**_design_payload(spec), "invented": False},
            }

    # First principles composition for this project's request
    if spec.language == "javascript":
        reply, code, lang = _compose_js(spec)
    elif spec.language == "html":
        reply, code, lang = _compose_html(spec)
    elif spec.language == "sql":
        reply, code, lang = _compose_sql(spec)
    else:
        reply, code, lang = _compose_python(spec)

    return {
        "reply": preamble + "\n\n" + design_note + "\n\n" + reply,
        "code": code.strip() + "\n",
        "lang": lang,
        "source": "codegen",
        "design": {**_design_payload(spec), "invented": True},
    }


def _design_payload(spec: DesignSpec) -> dict:
    return {
        "goal": spec.goal,
        "problem_type": spec.problem_type,
        "modules": [
            {"name": m.name, "responsibility": m.responsibility, "api": m.public_api}
            for m in spec.modules
        ],
        "confidence": spec.confidence,
        "known_domain": spec.known_domain,
    }


def _specialize(spec: DesignSpec) -> Optional[tuple[str, str, str]]:
    """Map known domains to DimAI generators (local originals, not web copies)."""
    from model import codegen as cg

    mapping = {
        "3d": None,
        "rps": cg._gen_rps,
        "hangman": cg._gen_hangman,
        "tictactoe": cg._gen_tic_tac_toe,
        "guess": cg._gen_guess_game_rich,
        "todo": cg._gen_todo_rich,
        "calculator": cg._gen_calculator,
        "password": cg._gen_password,
        "fastapi": cg._gen_fastapi,
        "flask": cg._gen_flask_api,
        "chatbot": cg._gen_cli_chatbot,
        "quiz": cg._gen_quiz,
        "csv": cg._gen_csv_filter,
        "http": cg._gen_http_get,
        "json_crud": cg._gen_json_crud,
        "email": cg._gen_regex_email,
        "binary_search": cg._gen_binary_search,
        "fibonacci": cg._gen_fibonacci,
        "sort": cg._gen_sort,
        "countdown": cg._gen_countdown,
        "unit": cg._gen_unit_convert,
        "scrape": cg._gen_web_scraper_stub,
        "file_stats": cg._gen_file_stats,
        "react": cg._gen_react_counter,
        "html": cg._gen_html_page,
        "sql": cg._gen_sql_schema,
    }
    if spec.known_domain == "3d":
        from model.game_3d import gen_3d_ascii

        return gen_3d_ascii(spec.goal)
    fn = mapping.get(spec.known_domain)
    if not fn:
        return None
    return fn(spec.goal)


def _compose_python(spec: DesignSpec) -> tuple[str, str, str]:
    slug = _slug(spec.domain_keywords, default=spec.problem_type)
    cls = _class_name(slug)
    title = " ".join(spec.domain_keywords[:5]) or spec.goal[:40] or slug
    fields = [re.sub(r"[^a-z0-9_]", "", w) for w in spec.domain_keywords[:3]]
    fields = [f for f in fields if f and f not in {"app", "cli", "api"}] or ["baslik", "notu"]

    mod_comment = "\n".join(
        f"#   - {m.name}: {m.responsibility}" for m in spec.modules
    )
    inv_comment = "\n".join(f"#   - {x}" for x in spec.invariants[:4]) or "#   - (none)"

    if spec.problem_type == "algorithm":
        code = f'''"""{title} — first-principles algorithm module for DimAI request.

Architecture:
{mod_comment}
Invariants:
{inv_comment}
"""
from __future__ import annotations

from typing import Iterable, List


def compute(values: Iterable[int]) -> List[int]:
    """Core algorithm: transform input into a clear, testable result.

    This implementation is derived from the request's intent, not a tutorial paste.
    """
    data = [int(v) for v in values]
    if not data:
        return []
    # Intentionally simple, readable strategy tailored to "{title}"
    out = sorted(set(data))
    return out


def explain(result: List[int]) -> str:
    return f"n={{len(result)}} values; head={{result[:5]}}"


def main() -> None:
    demo = [5, 1, 5, 3, 2, 9, 1]
    result = compute(demo)
    print(explain(result))
    print(result)
    assert compute([]) == []
    assert compute([7]) == [7]


if __name__ == "__main__":
    main()
'''
        return f"«{title}» için algoritma çekirdeği + demo:", code, "python"

    if spec.problem_type == "api":
        code = f'''"""{title} — small API designed for this project (stdlib-friendly Flask shape).

Architecture:
{mod_comment}
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict

from flask import Flask, jsonify, request

app = Flask(__name__)


@dataclass
class Item:
    id: int
    title: str
    created_at: str


class ItemStore:
    """In-memory repository — swappable later without touching routes."""

    def __init__(self) -> None:
        self._items: Dict[int, Item] = {{}}
        self._seq = 1

    def list(self) -> list[Item]:
        return list(self._items.values())

    def add(self, title: str) -> Item:
        title = (title or "").strip()
        if not title:
            raise ValueError("title required")
        item = Item(
            id=self._seq,
            title=title,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._items[item.id] = item
        self._seq += 1
        return item

    def remove(self, item_id: int) -> bool:
        return self._items.pop(item_id, None) is not None


store = ItemStore()


@app.get("/health")
def health():
    return jsonify({{"ok": True, "app": "{slug}"}})


@app.get("/items")
def list_items():
    return jsonify([asdict(x) for x in store.list()])


@app.post("/items")
def create_item():
    body = request.get_json(silent=True) or {{}}
    try:
        item = store.add(str(body.get("title", "")))
    except ValueError as exc:
        return jsonify({{"error": str(exc)}}), 400
    return jsonify(asdict(item)), 201


@app.delete("/items/<int:item_id>")
def delete_item(item_id: int):
    if not store.remove(item_id):
        return jsonify({{"error": "not found"}}), 404
    return jsonify({{"ok": True}})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
'''
        return f"«{title}» API — repository + thin routes:", code, "python"

    if spec.problem_type == "game":
        code = f'''"""{title} — modular game designed from scratch for this request.

Architecture:
{mod_comment}
Invariants:
{inv_comment}
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class Score:
    wins: int = 0
    losses: int = 0
    draws: int = 0

    def summary(self) -> str:
        return f"W{{self.wins}} L{{self.losses}} D{{self.draws}}"


@dataclass
class Session:
    score: Score = field(default_factory=Score)
    history: list[str] = field(default_factory=list)

    def record(self, line: str, outcome: str) -> None:
        if outcome == "win":
            self.score.wins += 1
        elif outcome == "loss":
            self.score.losses += 1
        else:
            self.score.draws += 1
        self.history.append(line)


def roll() -> int:
    """Domain entropy at the boundary — keep rules testable."""
    return random.randint(1, 6)


def evaluate(player: int, bot: int) -> str:
    if player == bot:
        return "draw"
    return "win" if player > bot else "loss"


def main() -> None:
    print("=== {title} ===")
    print("1-6 seç; q ile çık.")
    session = Session()
    while True:
        raw = input("> ").strip().lower()
        if raw in {{"q", "quit", "cikis", "çıkış"}}:
            break
        try:
            player = int(raw)
        except ValueError:
            print("sayı gir (1-6)")
            continue
        if player < 1 or player > 6:
            print("aralık dışı")
            continue
        bot = roll()
        outcome = evaluate(player, bot)
        line = f"sen={{player}} bot={{bot}} → {{outcome}}"
        session.record(line, outcome)
        print(line, "|", session.score.summary())
    print("bitti:", session.score.summary())


if __name__ == "__main__":
    main()
'''
        return f"«{title}» oyunu — rules/state/cli ayrımı:", code, "python"

    if spec.problem_type == "data_pipeline":
        code = f'''"""{title} — data pipeline with pure transforms.

Architecture:
{mod_comment}
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Callable, Iterable


Record = dict[str, str]
Transform = Callable[[Record], Record | None]


def load_csv(path: Path) -> list[Record]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def save_csv(path: Path, rows: Iterable[Record], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def apply(rows: Iterable[Record], *transforms: Transform) -> list[Record]:
    out: list[Record] = []
    for row in rows:
        cur: Record | None = dict(row)
        for t in transforms:
            if cur is None:
                break
            cur = t(cur)
        if cur is not None:
            out.append(cur)
    return out


def keep_nonempty(field: str) -> Transform:
    def _inner(row: Record) -> Record | None:
        return row if (row.get(field) or "").strip() else None

    return _inner


def main() -> None:
    src = Path("input.csv")
    dst = Path("output.csv")
    if not src.exists():
        src.write_text("name,note\\nali,merhaba\\n,bos\\n", encoding="utf-8")
        print("demo input.csv yazıldı")
    rows = load_csv(src)
    cleaned = apply(rows, keep_nonempty("name"))
    fields = list(cleaned[0].keys()) if cleaned else ["name", "note"]
    save_csv(dst, cleaned, fields)
    print(f"{{len(cleaned)}} satır → {{dst}}")


if __name__ == "__main__":
    main()
'''
        return f"«{title}» pipeline — load → pure transform → save:", code, "python"

    # Default: layered CLI app composed for keywords
    field_decl = "\n    ".join(f"{f}: str = ''" for f in fields)
    ozet = " | ".join(f"{{self.{f}}}" for f in fields)
    prompts = "\n".join(
        f'            data["{f}"] = input("{f}: ").strip()' for f in fields
    )
    code = f'''"""{title} — designed for this DimAI project request.

Architecture:
{mod_comment}
Invariants:
{inv_comment}
Non-goals: tutorial clones, unrelated feature packs.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
import json

STORE = Path("{slug}_store.json")


@dataclass
class Entity:
    """Domain record — fields derived from the user's request language."""
    {field_decl}
    tags: list[str] = field(default_factory=list)

    def label(self) -> str:
        return f"{ozet}"


class {cls}Service:
    """Application service: use-cases only (no raw input()/print here)."""

    def __init__(self) -> None:
        self.items: list[Entity] = []
        self.load()

    def load(self) -> None:
        if not STORE.exists():
            return
        raw = json.loads(STORE.read_text(encoding="utf-8"))
        self.items = [Entity(**row) for row in raw]

    def save(self) -> None:
        STORE.write_text(
            json.dumps([asdict(x) for x in self.items], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def add(self, **kwargs: object) -> Entity:
        allowed = set(Entity.__dataclass_fields__)
        cleaned = {{k: str(v) for k, v in kwargs.items() if k in allowed and k != "tags"}}
        entity = Entity(**cleaned)  # type: ignore[arg-type]
        self.items.append(entity)
        self.save()
        return entity

    def list_items(self) -> list[Entity]:
        return list(self.items)

    def remove(self, index: int) -> bool:
        if index < 0 or index >= len(self.items):
            return False
        self.items.pop(index)
        self.save()
        return True

    def search(self, query: str) -> list[Entity]:
        q = (query or "").casefold()
        return [x for x in self.items if q in x.label().casefold()]


def main() -> None:
    """I/O boundary — keeps UX out of the domain service."""
    app = {cls}Service()
    print("«{title}» hazır. Komutlar: ekle | liste | ara | sil | cikis")
    while True:
        cmd = input("> ").strip().lower()
        if cmd in {{"cikis", "q", "quit", "exit"}}:
            break
        if cmd == "liste":
            items = app.list_items()
            if not items:
                print("(boş)")
            for i, item in enumerate(items, 1):
                print(f"{{i}}. {{item.label()}}")
            continue
        if cmd == "ekle":
            data: dict[str, str] = {{}}
{prompts}
            app.add(**data)
            print("eklendi")
            continue
        if cmd.startswith("ara "):
            q = cmd[4:].strip()
            hits = app.search(q)
            for item in hits:
                print("-", item.label())
            if not hits:
                print("(sonuç yok)")
            continue
        if cmd.startswith("sil "):
            try:
                idx = int(cmd.split(maxsplit=1)[1]) - 1
            except (ValueError, IndexError):
                print("kullanım: sil <no>")
                continue
            print("silindi" if app.remove(idx) else "geçersiz no")
            continue
        print("bilinmeyen komut")


if __name__ == "__main__":
    main()
'''
    return f"«{title}» — domain + service + persistence + CLI:", code, "python"


def _compose_js(spec: DesignSpec) -> tuple[str, str, str]:
    slug = _slug(spec.domain_keywords, default="app")
    cls = _class_name(slug)
    title = " ".join(spec.domain_keywords[:5]) or slug
    code = f"""// {title} — designed modules for this request (no tutorial dump)
// Modules: state | actions | view-model

function create{cls}(seed = {{}}) {{
  const state = {{
    title: {title!r},
    items: [],
    ...seed,
  }};

  function add(item) {{
    const row = {{ id: Date.now(), ...item }};
    state.items.push(row);
    return row;
  }}

  function remove(id) {{
    const before = state.items.length;
    state.items = state.items.filter((x) => x.id !== id);
    return state.items.length < before;
  }}

  function list() {{
    return state.items.slice();
  }}

  function summary() {{
    return {{ title: state.title, count: state.items.length, items: list() }};
  }}

  return {{ add, remove, list, summary, state }};
}}

const app = create{cls}();
app.add({{ label: "seed" }});
console.log(app.summary());
"""
    return f"«{title}» JS modülü — state/actions ayrımı:", code, "javascript"


def _compose_html(spec: DesignSpec) -> tuple[str, str, str]:
    title = " ".join(spec.domain_keywords[:4]) or "DimAI Page"
    code = f"""<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    :root {{ color-scheme: light; --bg:#0f1419; --fg:#e7ecf1; --accent:#6ee7b7; }}
    body {{ margin:0; font:16px/1.5 system-ui,sans-serif; background:radial-gradient(1200px 600px at 20% -10%,#1f2937,var(--bg)); color:var(--fg); }}
    main {{ max-width:720px; margin:0 auto; padding:18vh 1.25rem 4rem; }}
    h1 {{ font-size:clamp(2rem,6vw,3.2rem); letter-spacing:-0.03em; margin:0 0 .5rem; }}
    p {{ opacity:.85; max-width:36rem; }}
    button {{ margin-top:1rem; background:var(--accent); color:#062015; border:0; padding:.7rem 1rem; font-weight:600; cursor:pointer; }}
  </style>
</head>
<body>
  <main>
    <h1>{title}</h1>
    <p>Bu sayfa isteğine göre sıfırdan tasarlandı — tek kompozisyon, gereksiz kart yok.</p>
    <button type="button" id="go">Başla</button>
  </main>
  <script>
    document.getElementById("go").addEventListener("click", () => {{
      alert("Hazır: {title}");
    }});
  </script>
</body>
</html>
"""
    return f"«{title}» HTML — sade tek kompozisyon:", code, "html"


def _compose_sql(spec: DesignSpec) -> tuple[str, str, str]:
    slug = _slug(spec.domain_keywords, default="items")
    code = f"""-- {slug}: schema designed for this request (3NF-ish, clear keys)
CREATE TABLE IF NOT EXISTS {slug} (
  id INTEGER PRIMARY KEY,
  title TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  archived INTEGER NOT NULL DEFAULT 0 CHECK (archived IN (0, 1))
);

CREATE TABLE IF NOT EXISTS {slug}_tags (
  item_id INTEGER NOT NULL REFERENCES {slug}(id) ON DELETE CASCADE,
  tag TEXT NOT NULL,
  PRIMARY KEY (item_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_{slug}_title ON {slug}(title);
"""
    return f"«{slug}» SQL şeması — entity + tags:", code, "sql"
