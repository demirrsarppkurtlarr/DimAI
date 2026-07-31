"""Ingest open Hugging Face coding instruction datasets into DimAI.

Uses the free datasets-server REST API (no gated downloads, no giant
`datasets` wheel required on Render). Builds:

  - data/code_instruct_corpus.txt   — User/Assistant + pure Python for char-RNN
  - data/code_learned_seed.json     — instruction→solution Q&A for RAG/learned

Philosophy: absorb concepts & patterns from HF; DimAI still invents code
via design-first codegen — this seed improves recall and training signal,
not wholesale tutorial paste into user replies.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import time
import warnings
from pathlib import Path
from typing import Any, Iterator, Optional
from urllib.parse import urlencode
# requests used inside _get_json (already in requirements.txt)

ROOT = Path(__file__).resolve().parents[1]
OUT_CORPUS = ROOT / "data" / "code_instruct_corpus.txt"
OUT_LEARNED = ROOT / "data" / "code_learned_seed.json"
API = "https://datasets-server.huggingface.co/rows"
UA = "DimAI-code-ingest/1.0"

FENCE = re.compile(r"```(?:python|py)?\s*(.*?)```", re.S | re.I)
PY_HINT = re.compile(
    r"\b(python|py\b|def |class |import |from \w+ import|pytest|django|flask)\b",
    re.I,
)

# Balanced caps so one noisy Alpaca dump cannot starve Evol/Magicoder/HumanEval.
SOURCES: list[dict[str, Any]] = [
    {
        "dataset": "sahil2801/CodeAlpaca-20k",
        "config": "default",
        "split": "train",
        "instruction": ("instruction",),
        "input": ("input",),
        "answer": ("output",),
        "cap": 1200,
    },
    {
        "dataset": "iamtarun/python_code_instructions_18k_alpaca",
        "config": "default",
        "split": "train",
        "instruction": ("instruction",),
        "input": ("input",),
        "answer": ("output",),
        "cap": 1800,
        "python_only": True,
    },
    {
        "dataset": "nickrosh/Evol-Instruct-Code-80k-v1",
        "config": "default",
        "split": "train",
        "instruction": ("instruction",),
        "answer": ("output",),
        "cap": 2200,
    },
    {
        "dataset": "ise-uiuc/Magicoder-Evol-Instruct-110K",
        "config": "default",
        "split": "train",
        "instruction": ("instruction",),
        "answer": ("response",),
        "cap": 2200,
    },
    {
        "dataset": "bigcode/self-oss-instruct-sc2-exec-filter-50k",
        "config": "default",
        "split": "train",
        "instruction": ("instruction", "prompt"),
        "answer": ("response",),
        "cap": 1500,
        "python_only": True,
    },
    {
        "dataset": "flytech/python-codes-25k",
        "config": "default",
        "split": "train",
        "instruction": ("instruction",),
        "input": ("input",),
        "answer": ("output",),
        "cap": 1500,
        "python_only": True,
    },
    {
        "dataset": "openai/openai_humaneval",
        "config": "openai_humaneval",
        "split": "test",
        "instruction": ("prompt",),
        "answer": ("canonical_solution",),
        "cap": 200,
        "combine_prompt_answer": True,
        "python_only": True,
    },
    {
        "dataset": "google-research-datasets/mbpp",
        "config": "full",
        "split": "train",
        "instruction": ("text",),
        "answer": ("code",),
        "cap": 974,
        "python_only": True,
    },
    {
        "dataset": "ajibawa-2023/Python-Code-23k-ShareGPT",
        "config": "default",
        "split": "train",
        "conversations": True,
        "cap": 1500,
        "python_only": True,
    },
    {
        "dataset": "christopher/rosetta-code",
        "config": "default",
        "split": "train",
        "instruction": ("task_description", "task_name"),
        "answer": ("code",),
        "lang_field": "language_name",
        "lang_allow": {"python", "python 3", "python3"},
        "cap": 1500,
        "python_only": True,
    },
]

PAGE = 100
TIMEOUT = 45


def _get_json(url: str) -> dict:
    import requests

    r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
    if r.status_code == 429:
        raise RuntimeError("HTTP 429 Too Many Requests")
    r.raise_for_status()
    return r.json()


def _iter_rows(dataset: str, config: str, split: str, limit: int) -> Iterator[dict]:
    offset = 0
    while offset < limit:
        length = min(PAGE, limit - offset)
        qs = urlencode(
            {
                "dataset": dataset,
                "config": config,
                "split": split,
                "offset": offset,
                "length": length,
            }
        )
        payload = None
        for attempt in range(6):
            try:
                payload = _get_json(f"{API}?{qs}")
                break
            except Exception as exc:
                msg = str(exc)
                code = getattr(exc, "response", None)
                status = getattr(code, "status_code", None) if code is not None else None
                if status == 429 or "429" in msg or "Too Many" in msg:
                    time.sleep(2.0 * (attempt + 1))
                    continue
                print(f"  [warn] {dataset}@{offset}: {exc}", flush=True)
                return
        if payload is None:
            print(f"  [warn] {dataset}@{offset}: rate limited, moving on", flush=True)
            return
        rows = payload.get("rows") or []
        if not rows:
            break
        for item in rows:
            row = item.get("row") or {}
            if isinstance(row, dict):
                yield row
        offset += len(rows)
        if len(rows) < length:
            break
        time.sleep(0.35)  # be nice to datasets-server



def _first(row: dict, keys: tuple[str, ...] | None) -> str:
    if not keys:
        return ""
    for k in keys:
        v = row.get(k)
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return ""


def _from_conversations(row: dict) -> tuple[str, str]:
    conv = row.get("conversations") or row.get("messages") or []
    if isinstance(conv, str):
        try:
            conv = ast.literal_eval(conv)
        except Exception:
            return "", ""
    if not isinstance(conv, list):
        return "", ""
    human, assistant = "", ""
    for turn in conv:
        if not isinstance(turn, dict):
            continue
        role = str(turn.get("from") or turn.get("role") or "").lower()
        val = str(turn.get("value") or turn.get("content") or "").strip()
        if role in {"human", "user"} and not human:
            human = val
        elif role in {"gpt", "assistant", "bot"} and human and not assistant:
            assistant = val
    return human, assistant


def _extract_python(text: str) -> list[str]:
    blocks = FENCE.findall(text or "")
    if not blocks:
        blocks = [text or ""]
    out: list[str] = []
    for b in blocks:
        code = "".join(ch for ch in b if ch == "\n" or 32 <= ord(ch) < 127).strip()
        if len(code) < 40:
            continue
        if not any(tok in code for tok in ("def ", "class ", "import ", "from ")):
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            try:
                ast.parse(code)
            except SyntaxError:
                continue
        out.append(code[:4000])
    return out


def _looks_python(instruction: str, answer: str, *, force: bool) -> bool:
    if force:
        return True
    blob = f"{instruction}\n{answer}"
    if PY_HINT.search(blob):
        return True
    if _extract_python(answer):
        return True
    return False


def _format_pair(prompt: str, answer: str) -> str:
    return f"User: {prompt}\nAssistant: {answer}\n"


def ingest(
    *,
    learned_cap: int = 3500,
    max_chars: int = 6_000_000,
    per_source_override: Optional[int] = None,
) -> dict:
    OUT_CORPUS.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT_CORPUS.with_suffix(".tmp")
    t0 = time.time()
    kept = 0
    chars = 0
    skipped = 0
    learned: list[dict] = []
    seen_q: set[str] = set()
    stats: dict[str, int] = {}

    with tmp.open("w", encoding="utf-8") as out:
        for src in SOURCES:
            if chars >= max_chars:
                break
            ds = src["dataset"]
            cap = int(per_source_override or src.get("cap") or 2000)
            # Reserve remaining char budget across remaining sources
            remaining_sources = max(1, len(SOURCES) - SOURCES.index(src))
            char_budget = max(200_000, (max_chars - chars) // remaining_sources)
            print(f"→ {ds} (rows≤{cap}, char_budget≈{char_budget:,})", flush=True)
            n_src = 0
            src_chars0 = chars
            for row in _iter_rows(ds, src["config"], src["split"], cap):
                if chars >= max_chars or (chars - src_chars0) >= char_budget:
                    break
                if src.get("lang_field"):
                    lang = str(row.get(src["lang_field"]) or "").strip().lower()
                    allow = {x.lower() for x in src.get("lang_allow") or set()}
                    if allow and lang not in allow:
                        skipped += 1
                        continue

                if src.get("conversations"):
                    instruction, answer = _from_conversations(row)
                    extra = ""
                else:
                    instruction = _first(row, tuple(src.get("instruction") or ()))
                    extra = _first(row, tuple(src.get("input") or ()))
                    answer = _first(row, tuple(src.get("answer") or ()))
                    if src.get("combine_prompt_answer") and instruction and answer:
                        # HumanEval: show prompt as task, full function as answer
                        answer = (instruction.rstrip() + "\n" + answer.lstrip()).strip()

                if extra and extra not in instruction:
                    prompt = f"{instruction}\n\nInput:\n{extra}".strip()
                else:
                    prompt = instruction.strip()

                if len(prompt) < 12 or len(answer) < 24:
                    skipped += 1
                    continue
                if not _looks_python(prompt, answer, force=bool(src.get("python_only"))):
                    # soft filter: keep only python-leaning rows for mixed sets
                    if not _extract_python(answer) and "def " not in answer:
                        skipped += 1
                        continue

                prompt = prompt[:900]
                answer = answer[:3500]
                block = _format_pair(prompt, answer)
                out.write(block)
                out.write("\n")
                # Also drop pure python into corpus for char-RNN
                for code in _extract_python(answer)[:2]:
                    out.write(code)
                    out.write("\n\n")
                    chars += len(code)

                kept += 1
                chars += len(block)
                n_src += 1

                if len(learned) < learned_cap:
                    key = prompt[:64].lower()
                    if key not in seen_q and 20 <= len(prompt) <= 400:
                        codes = _extract_python(answer)
                        entry = {
                            "q": prompt[:300],
                            "a": answer[:2500],
                            "url": f"hf://{ds}",
                            "quality": 0.9,
                            "source": ds,
                        }
                        if codes:
                            entry["c"] = codes[0][:3000]
                            entry["l"] = "python"
                        learned.append(entry)
                        seen_q.add(key)

                if n_src % 500 == 0:
                    print(f"  {ds}: kept_src={n_src} total_chars={chars:,}", flush=True)

            stats[ds] = n_src
            print(f"  {ds}: +{n_src} pairs", flush=True)
            time.sleep(1.0)  # cool-down between datasets

    tmp.replace(OUT_CORPUS)
    OUT_LEARNED.write_text(json.dumps(learned, ensure_ascii=False, indent=2), encoding="utf-8")
    result = {
        "kept": kept,
        "skipped": skipped,
        "chars": chars,
        "learned_seed": len(learned),
        "seconds": round(time.time() - t0, 1),
        "per_source": stats,
        "corpus": str(OUT_CORPUS),
        "learned": str(OUT_LEARNED),
    }
    print("DONE", json.dumps(result, ensure_ascii=False), flush=True)
    return result


def merge_into_train(*, code_chars: int = 4_000_000, active_cap: int = 12_000_000) -> None:
    """Blend code-instruct into train/active corpora (capped for tiny RNN)."""
    code_instruct = OUT_CORPUS.read_text(encoding="utf-8") if OUT_CORPUS.exists() else ""
    if not code_instruct:
        raise SystemExit("code instruct corpus missing — run ingest first")
    code_instruct = code_instruct[:code_chars]

    hf = ROOT / "data" / "hf_python_corpus.txt"
    train_path = ROOT / "data" / "train_corpus.txt"
    base = ""
    if hf.exists() and hf.stat().st_size > 1000:
        base = hf.read_text(encoding="utf-8")
    elif train_path.exists():
        base = train_path.read_text(encoding="utf-8")[:20_000_000]

    merged = (base.rstrip() + "\n\n" + code_instruct).strip() + "\n"
    train_path.write_text(merged, encoding="utf-8")

    active = (base[:3_000_000].rstrip() + "\n\n" + code_instruct[:5_000_000]).strip() + "\n"
    (ROOT / "data" / "corpus.txt").write_text(active[:active_cap], encoding="utf-8")

    deploy = ROOT / "data" / "deploy_corpus.txt"
    old = deploy.read_text(encoding="utf-8") if deploy.exists() else base[:400_000]
    deploy.write_text(
        (old.rstrip() + "\n\n" + code_instruct[:800_000]).strip()[:2_500_000] + "\n",
        encoding="utf-8",
    )
    print(
        f"merged train={len(merged):,} active={min(len(active), active_cap):,} "
        f"instruct_slice={len(code_instruct):,}",
        flush=True,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest HF coding instruction datasets")
    ap.add_argument("--learned-cap", type=int, default=3500)
    ap.add_argument("--max-chars", type=int, default=6_000_000)
    ap.add_argument("--per-source", type=int, default=0, help="override per-dataset row cap")
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--merge-only", action="store_true")
    args = ap.parse_args()
    if args.merge_only:
        merge_into_train()
        return
    ingest(
        learned_cap=args.learned_cap,
        max_chars=args.max_chars,
        per_source_override=args.per_source or None,
    )
    if args.merge:
        merge_into_train()


if __name__ == "__main__":
    main()
