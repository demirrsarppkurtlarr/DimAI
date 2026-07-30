"""Lightweight Hugging Face data collection for on-server training.

Uses the free datasets-server REST API to stream small row batches (JSON)
instead of downloading whole datasets — fits in Render free tier memory.
"""
from __future__ import annotations

import ast
import re

import requests

API = "https://datasets-server.huggingface.co/rows"
HEADERS = {"User-Agent": "DimAI/1.0 (learning assistant)"}
TIMEOUT = 20

# dataset -> (config, split, field containing code/markdown)
SOURCES = [
    ("flytech/python-codes-25k", "default", "train", "output"),
    ("openai/openai_humaneval", "openai_humaneval", "test", "canonical_solution"),
    ("google-research-datasets/mbpp", "full", "train", "code"),
]

FENCE = re.compile(r"```(?:python)?\s*(.*?)```", re.S)


def _extract_code(text: str) -> list[str]:
    """Pull python code out of markdown fences, or accept raw code."""
    blocks = FENCE.findall(text)
    if not blocks:
        blocks = [text]
    out = []
    for b in blocks:
        code = "".join(ch for ch in b if ch == "\n" or 32 <= ord(ch) < 127).strip()
        if len(code) < 30:
            continue
        try:
            ast.parse(code)
        except SyntaxError:
            continue
        out.append(code)
    return out


def fetch_batch(offset: int, rows_per_source: int = 40) -> tuple[str, int]:
    """Fetch one batch from all sources at the given offset.

    Returns (new_corpus_text, next_offset).
    """
    chunks: list[str] = []
    for dataset, config, split, field in SOURCES:
        try:
            r = requests.get(
                API,
                params={
                    "dataset": dataset,
                    "config": config,
                    "split": split,
                    "offset": offset,
                    "length": min(rows_per_source, 100),
                },
                headers=HEADERS,
                timeout=TIMEOUT,
            )
            if r.status_code != 200:
                continue
            for item in r.json().get("rows", []):
                raw = str(item.get("row", {}).get(field) or "")
                chunks.extend(_extract_code(raw))
        except Exception:
            continue
    text = "\n\n".join(chunks)
    return text, offset + rows_per_source
