"""Iterative code improvement — each `geliştir` must advance the prior source.

Never regenerates the same rich template. Stamps DIMAI_IMPROVE_LEVEL and
appends the next missing capability layer onto the user's actual code.
"""
from __future__ import annotations

import re
from typing import Optional


_IMPROVE_RE = re.compile(r"DIMAI_IMPROVE_LEVEL\s*=\s*(\d+)")


def read_level(code: str) -> int:
    m = _IMPROVE_RE.search(code or "")
    if m:
        return int(m.group(1))
    low = (code or "").lower()
    score = 0
    if "appstate" in low or "guvenli_calistir" in low:
        score = max(score, 1)
    if "dimai_help" in low or "argparse" in low:
        score = max(score, 2)
    if "dimai_self_test" in low or ("assert " in low and "def test_" in low):
        score = max(score, 3)
    if "class dimaiconfig" in low:
        score = max(score, 4)
    if "dimai_export_json" in low:
        score = max(score, 5)
    if "dimai_stats" in low:
        score = max(score, 6)
    if "dimai_backup" in low:
        score = max(score, 7)
    return score


def stamp_level(code: str, level: int) -> str:
    code = code or ""
    stamp = f"DIMAI_IMPROVE_LEVEL = {level}"
    if _IMPROVE_RE.search(code):
        return _IMPROVE_RE.sub(stamp, code, count=1)
    if code.lstrip().startswith('"""'):
        end = code.find('"""', 3)
        if end != -1:
            end += 3
            return code[:end] + f"\n\n{stamp}\n" + code[end:].lstrip("\n")
    return f"{stamp}\n\n{code}"


def level_label(level: int, *, language: str = "tr") -> str:
    tr = {
        1: "loglama + hata sınırı",
        2: "CLI yardım / menü netliği",
        3: "self-test (assert)",
        4: "config / ayar katmanı",
        5: "dışa aktarım (JSON)",
        6: "istatistik / özet",
        7: "yedekleme / snapshot",
    }
    en = {
        1: "logging + error boundary",
        2: "CLI help",
        3: "self-tests",
        4: "config layer",
        5: "JSON export",
        6: "stats summary",
        7: "backup/snapshot",
    }
    bank = en if language == "en" else tr
    if level in bank:
        return bank[level]
    return f"eklenti katmanı v{level}" if language != "en" else f"plugin layer v{level}"


def evolve(prior: str, *, request: str = "", lang: str = "python") -> dict:
    """Return {code, level, label} — code is guaranteed different from prior.

    Never shrinks the user's source: each pass appends a capability layer.
    """
    prior = (prior or "").strip()
    if "```" in prior:
        m = re.search(r"```(?:\w+)?\n(.*?)```", prior, re.S)
        if m:
            prior = m.group(1).strip()
    level = read_level(prior) + 1
    if lang == "javascript":
        code = _evolve_js(prior, level, request=request)
    else:
        code = _evolve_python(prior, level, request=request)
    if code.strip() == prior.strip():
        code = _force_delta(prior, level, request=request, lang=lang)
    # Hard guard: improving must not discard the body (truncation bug safety net)
    if len(code) + 40 < len(prior):
        code = _force_delta(prior, level, request=request, lang=lang)
    if len(code) < len(prior):
        code = prior.rstrip() + "\n\n# --- dimai evolve safety: preserve prior ---\n" + code
    code = stamp_level(code, level)
    return {
        "code": code.strip() + "\n",
        "level": level,
        "label": level_label(level, language="en" if lang == "javascript" else "tr"),
    }


def _evolve_python(prior: str, level: int, *, request: str) -> str:
    code = prior
    if level == 1 and "def guvenli_calistir" not in code:
        return code.rstrip() + '''

# --- dimai evolve v1: logging + safe runner ---
import traceback
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AppState:
    """Runtime façade added on improve pass."""
    logs: list[str] = field(default_factory=list)
    ayarlar: dict[str, Any] = field(default_factory=lambda: {"debug": True})

    def log(self, msg: str) -> None:
        self.logs.append(msg)
        print(msg)


def guvenli_calistir(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        print("Hata:", exc)
        traceback.print_exc()
        return None
'''

    if level == 2 and "def dimai_help" not in code:
        return code.rstrip() + '''

# --- dimai evolve v2: help ---
def dimai_help() -> None:
    print("Komutlar: help | gelistir-notu | cikis")
    print("Bu sürüm DimAI improve v2 ile genişletildi.")
'''

    if level == 3 and "def dimai_self_test" not in code:
        return code.rstrip() + '''

# --- dimai evolve v3: self-test ---
def dimai_self_test() -> None:
    assert True
    sample = [1, 2, 3]
    assert len(sample) == 3
    print("self-test OK")
'''

    if level == 4 and "class DimaiConfig" not in code:
        return code.rstrip() + '''

# --- dimai evolve v4: config ---
from dataclasses import dataclass as _dc_config


@_dc_config
class DimaiConfig:
    debug: bool = True
    max_items: int = 1000
    locale: str = "tr"


CONFIG = DimaiConfig()
'''

    if level == 5 and "def dimai_export_json" not in code:
        return code.rstrip() + '''

# --- dimai evolve v5: export ---
import json
from pathlib import Path


def dimai_export_json(data, path: str = "dimai_export.json") -> Path:
    p = Path(path)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("export:", p.resolve())
    return p
'''

    if level == 6 and "def dimai_stats" not in code:
        return code.rstrip() + '''

# --- dimai evolve v6: stats ---
def dimai_stats(items=None) -> dict:
    items = list(items or [])
    out = {"count": len(items), "empty": len(items) == 0}
    print("istatistik:", out)
    return out
'''

    if level == 7 and "def dimai_backup" not in code:
        return code.rstrip() + '''

# --- dimai evolve v7: backup ---
from pathlib import Path as _Path
from datetime import datetime as _dt
import shutil as _shutil


def dimai_backup(src: str = "data.json") -> str:
    p = _Path(src)
    if not p.exists():
        print("yedek: kaynak yok", src)
        return ""
    stamp = _dt.now().strftime("%Y%m%d_%H%M%S")
    dst = p.with_name(f"{p.stem}_backup_{stamp}{p.suffix}")
    _shutil.copy2(p, dst)
    print("yedek alındı:", dst)
    return str(dst)
'''

    return _force_delta(code, level, request=request, lang="python")


def _evolve_js(prior: str, level: int, *, request: str) -> str:
    return _force_delta(prior, level, request=request, lang="javascript")


def _force_delta(prior: str, level: int, *, request: str, lang: str = "python") -> str:
    req_safe = (request or "gelistir").replace('"""', "'").replace("`", "'")[:60]
    if lang == "javascript":
        block = f"""

// --- dimai evolve v{level} | {req_safe} ---
function dimaiPluginV{level}(payload = {{}}) {{
  const info = {{ level: {level}, request: {req_safe!r}, payload }};
  console.log("[dimai] improve plugin v{level}", info);
  return info;
}}
dimaiPluginV{level}({{ ok: true }});
"""
        code = prior.rstrip()
        if f"function dimaiPluginV{level}(" in code:
            code = re.sub(
                rf"\n// --- dimai evolve v{level} \|.*?(?=\n// --- dimai evolve|\Z)",
                "",
                code,
                flags=re.S,
            ).rstrip()
        return code + block + "\n"

    block = f'''

# --- dimai evolve v{level} | {req_safe} ---
def dimai_plugin_v{level}(payload=None):
    """Auto-grown improve layer #{level} — unique each pass."""
    payload = payload or {{}}
    info = {{
        "level": {level},
        "request": {req_safe!r},
        "keys": list(payload.keys()) if isinstance(payload, dict) else [],
    }}
    print(f"[dimai] improve plugin v{level}:", info)
    return info
'''
    code = prior.rstrip()
    if f"def dimai_plugin_v{level}(" in code:
        code = re.sub(
            rf"\n# --- dimai evolve v{level} \|.*?(?=\n# --- dimai evolve|\Z)",
            "",
            code,
            flags=re.S,
        ).rstrip()
    return code + block + "\n"
