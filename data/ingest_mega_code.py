#!/usr/bin/env python3
"""Mega coding ingest — 7 fresh Hugging Face code datasets for DimAI.

Streams via the free datasets-server rows API (no gated downloads):
  - m-a-p/CodeFeedback-Filtered-Instruction (156k, quality-filtered)
  - glaiveai/glaive-code-assistant-v2 (~215k Q&A)
  - ise-uiuc/Magicoder-OSS-Instruct-75K
  - mrbesher/python-code-instructions-18k-alpaca-tr  (TURKISH!)
  - Vezora/Tested-143k-Python-Alpaca (execution-tested python)
  - jtatman/python-code-dataset-500k
  - vikp/python_code_instructions_filtered

Output:
  - data/mega_code_seed.json — committed RAG/kb_index seed (q/a/c/l/quality)

Usage:
  python data/ingest_mega_code.py            # all sources
  python data/ingest_mega_code.py --limit-rows 400   # quick pass
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import time
from pathlib import Path
from typing import Any, Iterator, Optional

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT_SEED = ROOT / "data" / "mega_code_seed.json"
API = "https://datasets-server.huggingface.co/rows"
UA = "DimAI-mega-code/1.0"
FENCE = re.compile(r"```(?:python|py)?\s*\n?(.*?)```", re.S | re.I)
PAGE = 100

SOURCES: list[dict[str, Any]] = [
    {
        "dataset": "Vezora/Tested-143k-Python-Alpaca",
        "config": "default", "split": "train",
        "q": "instruction", "a": "output",
        "rows": 1400, "seed_cap": 1200, "lang": "en", "quality": 0.92,
    },
    {
        "dataset": "m-a-p/CodeFeedback-Filtered-Instruction",
        "config": "default", "split": "train",
        "q": "query", "a": "answer",
        "rows": 1400, "seed_cap": 1100, "lang": "en", "quality": 0.9,
    },
    {
        "dataset": "mrbesher/python-code-instructions-18k-alpaca-tr",
        "config": "default", "split": "train",
        "q": "instruction", "a": "output", "extra_input": "input",
        "rows": 1600, "seed_cap": 1400, "lang": "tr", "quality": 0.9,
    },
    {
        "dataset": "ise-uiuc/Magicoder-OSS-Instruct-75K",
        "config": "default", "split": "train",
        "q": "problem", "a": "solution", "lang_col": "lang",
        "rows": 1200, "seed_cap": 900, "lang": "en", "quality": 0.88,
    },
    {
        "dataset": "glaiveai/glaive-code-assistant-v2",
        "config": "default", "split": "train",
        "q": "question", "a": "answer",
        "rows": 1200, "seed_cap": 900, "lang": "en", "quality": 0.85,
    },
    {
        "dataset": "jtatman/python-code-dataset-500k",
        "config": "default", "split": "train",
        "q": "instruction", "a": "output",
        "rows": 1000, "seed_cap": 700, "lang": "en", "quality": 0.8,
    },
    {
        "dataset": "NickIBrody/python-code-instructions-85k",
        "config": "default", "split": "train",
        "q": "instruction", "a": "output",
        "rows": 1000, "seed_cap": 700, "lang": "en", "quality": 0.82,
    },
]


def _iter_rows(dataset: str, config: str, split: str, limit: int) -> Iterator[dict]:
    offset = 0
    while offset < limit:
        rows = None
        for attempt in range(4):
            try:
                r = requests.get(
                    API,
                    params={
                        "dataset": dataset, "config": config, "split": split,
                        "offset": offset, "length": min(PAGE, limit - offset),
                    },
                    headers={"User-Agent": UA},
                    timeout=30,
                )
                if r.status_code == 200:
                    rows = r.json().get("rows") or []
                    break
                # 429/5xx: back off and retry
                time.sleep(2.0 * (attempt + 1))
            except Exception:
                time.sleep(2.0 * (attempt + 1))
        if not rows:
            return
        for item in rows:
            yield item.get("row") or {}
        offset += len(rows)
        time.sleep(0.6)


def _valid_python(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except Exception:
        return False


def _extract_code(answer: str) -> tuple[str, str]:
    """Return (code, cleaned_answer)."""
    m = FENCE.search(answer or "")
    if m:
        code = m.group(1).strip()
        cleaned = FENCE.sub("", answer).strip()
        return code, cleaned or answer[:400]
    # Raw code heuristic
    a = (answer or "").strip()
    if a.count("\n") >= 2 and ("def " in a or "class " in a or "import " in a):
        if _valid_python(a):
            return a, ""
    return "", a


def _keywords(text: str) -> list[str]:
    words = re.findall(r"[a-zA-ZçğıöşüÇĞİÖŞÜ0-9_]{3,}", (text or "").casefold())
    stop = {"the", "and", "for", "with", "that", "this", "bir", "için", "gibi", "olan", "write", "create", "python"}
    out, seen = [], set()
    for w in words:
        if w in stop or w in seen:
            continue
        seen.add(w)
        out.append(w)
    return out[:10]


def ingest(limit_rows: Optional[int] = None) -> int:
    entries: list[dict] = []
    seen_q: set[str] = set()
    for src in SOURCES:
        ds = src["dataset"]
        rows_cap = int(limit_rows or src["rows"])
        taken = 0
        for row in _iter_rows(ds, src["config"], src["split"], rows_cap):
            if taken >= src["seed_cap"]:
                break
            q = str(row.get(src["q"]) or "").strip()
            extra = str(row.get(src.get("extra_input") or "") or "").strip()
            if extra and extra.casefold() not in {"not applicable", "n/a", ""}:
                q = f"{q}\n{extra}".strip()
            a_raw = str(row.get(src["a"]) or "").strip()
            if len(q) < 12 or len(a_raw) < 30:
                continue
            # Skip mostly-URL or template junk (long problem statements are OK)
            if q.count("http") > 1 or len(q) > 2000:
                continue
            code, cleaned = _extract_code(a_raw)
            lang = src["lang"]
            if src.get("lang_col"):
                row_lang = str(row.get(src["lang_col"]) or "").casefold()
                if row_lang and row_lang not in {"python", "py"}:
                    # keep only python-family for the trainer; others still OK for RAG
                    if len(code) > 2500:
                        continue
            if code and len(code) > 3500:
                code = code[:3500]
            if not code and len(cleaned) < 60:
                continue
            key = q[:100].casefold()
            if key in seen_q:
                continue
            seen_q.add(key)
            entry = {
                "q": q[:420],
                "a": (cleaned or a_raw)[:2500],
                "url": f"https://huggingface.co/datasets/{ds}",
                "quality": src["quality"],
                "source": ds,
                "kw": _keywords(q),
            }
            if code:
                entry["c"] = code
                entry["l"] = "python"
            entries.append(entry)
            taken += 1
        print(f"[mega] {ds}: {taken} entries")
    OUT_SEED.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    print(f"[mega] wrote {OUT_SEED} ({len(entries)} entries, {OUT_SEED.stat().st_size/1e6:.1f} MB)")
    return len(entries)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit-rows", type=int, default=None)
    args = ap.parse_args()
    ingest(limit_rows=args.limit_rows)
