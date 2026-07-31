"""Download a moderate, detailed Python code slice from Hugging Face (no AI API).

Preferred path: `python data/ingest_code_instruct.py --merge` (datasets-server,
multi-source instruction corpora, RAG seed).

This module remains for local `datasets` library pulls when available.
"""
from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "data" / "hf_python_corpus.txt"
MERGED_PATH = ROOT / "data" / "corpus.txt"

DEFAULT_MAX_CHARS = 2_000_000  # ~2 MB
MIN_CHARS = 60
MAX_CHUNK_CHARS = 3500


def extract_top_level_defs(code: str) -> list[str]:
    chunks: list[str] = []
    code = code.replace("\t", "    ")
    try:
        tree = ast.parse(code)
    except SyntaxError:
        parts = re.split(r"(?m)(?=^(?:def |class |async def ))", code)
        for part in parts:
            part = part.strip()
            if MIN_CHARS <= len(part) <= MAX_CHUNK_CHARS and part.startswith(
                ("def ", "class ", "async def ")
            ):
                chunks.append(part)
        return chunks

    lines = code.splitlines()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = node.lineno - 1
            end = getattr(node, "end_lineno", None) or (start + 1)
            block = "\n".join(lines[start:end]).strip()
            if MIN_CHARS <= len(block) <= MAX_CHUNK_CHARS:
                chunks.append(block)
    return chunks


def add_chunks(bucket: list[str], code: str, total: list[int], max_chars: int) -> None:
    if total[0] >= max_chars or not code or not isinstance(code, str):
        return
    for chunk in extract_top_level_defs(code[:14000])[:4]:
        if total[0] >= max_chars:
            return
        bucket.append(chunk.strip())
        total[0] += len(chunk)


def add_raw_if_valid(bucket: list[str], code: str, total: list[int], max_chars: int) -> None:
    code = (code or "").strip()
    if total[0] >= max_chars:
        return
    if not (MIN_CHARS <= len(code) <= MAX_CHUNK_CHARS):
        return
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return
    if not tree.body:
        return
    bucket.append(code)
    total[0] += len(code)


def fetch_flytech(bucket: list[str], total: list[int], max_chars: int) -> None:
    from datasets import load_dataset

    print("→ flytech/python-codes-25k")
    ds = load_dataset("flytech/python-codes-25k", split="train", streaming=True)
    n = 0
    for row in ds:
        if total[0] >= max_chars * 0.45:
            break
        code = row.get("output") or row.get("code") or row.get("text") or ""
        if "```" in code:
            m = re.search(r"```(?:python)?\n(.*?)```", code, re.S)
            if m:
                code = m.group(1)
        add_chunks(bucket, code, total, max_chars)
        n += 1
        if n % 300 == 0:
            print(f"  flytech rows={n} chars={total[0]}")
    print(f"  flytech done rows={n} chars={total[0]}")


def fetch_mbpp(bucket: list[str], total: list[int], max_chars: int) -> None:
    from datasets import load_dataset

    print("→ google-research-datasets/mbpp")
    ds = load_dataset("google-research-datasets/mbpp", "full", split="train")
    for row in ds:
        if total[0] >= max_chars * 0.65:
            break
        code = row.get("code") or ""
        add_raw_if_valid(bucket, code, total, max_chars)
    print(f"  mbpp chars={total[0]}")


def fetch_humaneval(bucket: list[str], total: list[int], max_chars: int) -> None:
    from datasets import load_dataset

    print("→ openai/openai_humaneval")
    ds = load_dataset("openai/openai_humaneval", split="test")
    for row in ds:
        prompt = row.get("prompt") or ""
        canon = row.get("canonical_solution") or ""
        add_raw_if_valid(bucket, (prompt + canon).strip(), total, max_chars)
    print(f"  humaneval chars={total[0]}")


def fetch_magicoder(bucket: list[str], total: list[int], max_chars: int) -> None:
    from datasets import load_dataset

    print("→ ise-uiuc/Magicoder-OSS-Instruct-75K (python only)")
    ds = load_dataset("ise-uiuc/Magicoder-OSS-Instruct-75K", split="train", streaming=True)
    n = 0
    kept = 0
    for row in ds:
        if total[0] >= max_chars:
            break
        if (row.get("lang") or "").lower() not in {"python", "py"}:
            continue
        code = row.get("solution") or ""
        if "```" in code:
            blocks = re.findall(r"```(?:python)?\n(.*?)```", code, re.S)
            for block in blocks:
                add_chunks(bucket, block, total, max_chars)
        else:
            add_chunks(bucket, code, total, max_chars)
        kept += 1
        n += 1
        if kept % 200 == 0:
            print(f"  magicoder kept={kept} chars={total[0]}")
    print(f"  magicoder done kept={kept} chars={total[0]}")


def fetch_evol_instruct(bucket: list[str], total: list[int], max_chars: int) -> None:
    from datasets import load_dataset

    print("→ nickrosh/Evol-Instruct-Code-80k-v1")
    ds = load_dataset("nickrosh/Evol-Instruct-Code-80k-v1", split="train", streaming=True)
    n = 0
    for row in ds:
        if total[0] >= max_chars:
            break
        out = row.get("output") or ""
        if "```" in out:
            blocks = re.findall(r"```(?:python)?\n(.*?)```", out, re.S)
            for block in blocks:
                if "def " in block or "class " in block:
                    add_chunks(bucket, block, total, max_chars)
        elif "def " in out:
            add_chunks(bucket, out, total, max_chars)
        n += 1
        if n % 400 == 0:
            print(f"  evol rows={n} chars={total[0]}")
    print(f"  evol done rows={n} chars={total[0]}")


def fetch(max_chars: int = DEFAULT_MAX_CHARS) -> str:
    bucket: list[str] = []
    total = [0]

    fetch_humaneval(bucket, total, max_chars)
    fetch_mbpp(bucket, total, max_chars)
    fetch_flytech(bucket, total, max_chars)
    fetch_magicoder(bucket, total, max_chars)
    if total[0] < max_chars:
        fetch_evol_instruct(bucket, total, max_chars)

    unique = list(dict.fromkeys(bucket))
    text = "\n\n".join(unique) + "\n"
    print(f"TOTAL chunks={len(unique)} chars={len(text)}")
    return text


def merge_into_corpus(hf_text: str) -> None:
    import sys

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from data.build_corpus import build_corpus

    seed = build_corpus()
    merged = seed.strip() + "\n\n" + hf_text.strip() + "\n"
    MERGED_PATH.write_text(merged, encoding="utf-8")
    print(f"Merged corpus -> {MERGED_PATH} ({len(merged)} chars)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    parser.add_argument("--no-merge", action="store_true")
    parser.add_argument(
        "--via-server",
        action="store_true",
        help="Use data/ingest_code_instruct.py (recommended, no datasets lib)",
    )
    args = parser.parse_args()

    if args.via_server:
        from data.ingest_code_instruct import ingest, merge_into_train

        ingest(learned_cap=3500, max_chars=max(args.max_chars, 4_000_000))
        if not args.no_merge:
            merge_into_train()
        return

    text = fetch(max_chars=args.max_chars)
    OUT_PATH.write_text(text, encoding="utf-8")
    print(f"Wrote {OUT_PATH}")
    if not args.no_merge:
        merge_into_corpus(text)


if __name__ == "__main__":
    main()
