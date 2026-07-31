"""Lightweight Hugging Face data collection for on-server training.

Uses the free datasets-server REST API to stream small row batches (JSON)
instead of downloading whole datasets — fits in Render free tier memory.

Expanded for Claude-oriented coding instruction corpora (Python-leaning).
"""
from __future__ import annotations

import ast
import re
import warnings

import requests

API = "https://datasets-server.huggingface.co/rows"
HEADERS = {"User-Agent": "DimAI/1.0 (learning assistant)"}
TIMEOUT = (5, 12)  # (connect, read) — asılı kalmayı önler

# dataset -> (config, split, field containing code/markdown)
# Prefer instruction outputs that contain runnable Python.
SOURCES = [
    ("flytech/python-codes-25k", "default", "train", "output"),
    ("openai/openai_humaneval", "openai_humaneval", "test", "canonical_solution"),
    ("google-research-datasets/mbpp", "full", "train", "code"),
    ("sahil2801/CodeAlpaca-20k", "default", "train", "output"),
    ("iamtarun/python_code_instructions_18k_alpaca", "default", "train", "output"),
    ("nickrosh/Evol-Instruct-Code-80k-v1", "default", "train", "output"),
    ("ise-uiuc/Magicoder-Evol-Instruct-110K", "default", "train", "response"),
    ("bigcode/self-oss-instruct-sc2-exec-filter-50k", "default", "train", "response"),
    ("christopher/rosetta-code", "default", "train", "code"),
    # Turkish code / instruct (online autolearn)
    ("berhaan/Turkish-CodeAlpaca-20k", "default", "train", "output"),
    ("duxx/code-instruction-turkish", "default", "train", "answer"),
    ("erythropygia/Instruct-Python-Code-Turkish", "default", "train", "output"),
    ("alztrk/turkish-code-instructions", "default", "train", "response"),
    ("TFLai/Turkish-Alpaca", "default", "train", "output"),
    ("malhajar/alpaca-evol-instruct-turkish", "default", "train", "response"),
]

FENCE = re.compile(r"```(?:python|py)?\s*(.*?)```", re.S | re.I)


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
        if not any(tok in code for tok in ("def ", "class ", "import ", "from ")):
            # Rosetta / snippets may still be valid — try parse anyway
            pass
        try:
            ast.parse(code)
        except SyntaxError:
            continue
        except Exception:
            continue
        out.append(code)
    return out


# silence invalid-escape noise from third-party dataset snippets during parse
warnings.filterwarnings("ignore", category=SyntaxWarning)


def fetch_batch(offset: int, rows_per_source: int = 40) -> tuple[str, int]:
    """Fetch one batch from all sources at the given offset.

    Returns (new_corpus_text, next_offset).
    """
    import time

    budget_end = time.time() + 60  # toplam bütçe: 60 sn
    chunks: list[str] = []
    for dataset, config, split, field in SOURCES:
        if time.time() > budget_end:
            print("[collect] time budget exceeded, skipping rest", flush=True)
            break
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
                print(f"[collect] {dataset}: HTTP {r.status_code}", flush=True)
                continue
            n0 = len(chunks)
            for item in r.json().get("rows", []):
                row = item.get("row", {}) or {}
                # Rosetta: python only
                if dataset.endswith("rosetta-code"):
                    lang = str(row.get("language_name") or "").lower()
                    if lang not in {"python", "python 3", "python3"}:
                        continue
                raw = str(row.get(field) or "")
                chunks.extend(_extract_code(raw))
            print(f"[collect] {dataset}: +{len(chunks) - n0} chunks", flush=True)
        except Exception as exc:
            print(f"[collect] {dataset}: {exc}", flush=True)
            continue
    text = "\n\n".join(chunks)
    return text, offset + rows_per_source
