"""Ingest aq1048576/llama_3.1_instruct_tulu_chat into DimAI.

Streams the full JSONL from Hugging Face (embeddings dominate the ~10.5 GB
file). Writes ONLY prompt/response text into a local corpus — the complete
textual content of every row, without embedding vectors.

Revision pinned to the commit the user requested.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Iterator, Optional
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT_CORPUS = ROOT / "data" / "tulu_chat_corpus.txt"
OUT_LEARNED = ROOT / "data" / "tulu_learned_seed.json"
REV = "3e7a56ac4fb095c485d3595b7948be1bf7efd295"
URL = (
    "https://huggingface.co/datasets/aq1048576/llama_3.1_instruct_tulu_chat/"
    f"resolve/{REV}/llama_3.1_instruct_tulu_chat.jsonl"
)

MIN_PROMPT = 8
MIN_ANSWER = 20
MAX_PROMPT = 1200
MAX_ANSWER = 2500


def _pick_answer(obj: dict) -> str:
    if obj.get("tulu_success") and (obj.get("tulu_response") or "").strip():
        return str(obj["tulu_response"]).strip()
    return str(obj.get("response") or "").strip()


def _format_pair(prompt: str, answer: str) -> str:
    return f"User: {prompt}\nAssistant: {answer}\n"


def _iter_jsonl_stream(url: str) -> Iterator[dict]:
    req = Request(url, headers={"User-Agent": "DimAI-ingest/1.0"})
    with urlopen(req, timeout=120) as resp:
        buf = b""
        while True:
            chunk = resp.read(1024 * 1024)  # 1 MB
            if not chunk:
                break
            buf += chunk
            while True:
                nl = buf.find(b"\n")
                if nl < 0:
                    break
                line, buf = buf[:nl], buf[nl + 1 :]
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
        if buf.strip():
            try:
                yield json.loads(buf)
            except json.JSONDecodeError:
                pass


def ingest(
    max_rows: Optional[int] = None,
    learned_cap: int = 1500,
) -> dict:
    OUT_CORPUS.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT_CORPUS.with_suffix(".tmp")
    t0 = time.time()
    rows = 0
    kept = 0
    chars = 0
    skipped = 0
    learned: list[dict] = []
    sources: dict[str, int] = {}

    print(f"streaming {URL}", flush=True)
    with tmp.open("w", encoding="utf-8") as out:
        for obj in _iter_jsonl_stream(URL):
            rows += 1
            if max_rows and rows > max_rows:
                break
            prompt = str(obj.get("prompt") or "").strip()
            answer = _pick_answer(obj)
            src = str(obj.get("source") or "unknown")[:80]
            sources[src] = sources.get(src, 0) + 1

            if len(prompt) < MIN_PROMPT or len(answer) < MIN_ANSWER:
                skipped += 1
                continue
            # Drop obvious empty refusals-only noise? keep refusals — part of dataset
            p = prompt[:MAX_PROMPT]
            a = answer[:MAX_ANSWER]
            block = _format_pair(p, a)
            out.write(block)
            out.write("\n")
            kept += 1
            chars += len(block)

            # Seed learned store with diverse, medium-length Q&A (no code-only filter)
            if len(learned) < learned_cap and 40 <= len(p) <= 280 and 60 <= len(a) <= 1200:
                # light diversity: skip near-dup prompts by first 48 chars
                key = p[:48].lower()
                if not any(x["q"][:48].lower() == key for x in learned[-40:]):
                    learned.append(
                        {
                            "q": p[:300],
                            "a": a[:2000],
                            "url": f"hf://aq1048576/llama_3.1_instruct_tulu_chat#{obj.get('id','')}",
                            "quality": 0.85,
                            "source": src,
                        }
                    )

            if rows % 2000 == 0:
                rate = rows / max(time.time() - t0, 1e-9)
                print(
                    f"  rows={rows:,} kept={kept:,} chars={chars:,} "
                    f"{rate:.0f} row/s elapsed={(time.time()-t0)/60:.1f}m",
                    flush=True,
                )

    tmp.replace(OUT_CORPUS)
    OUT_LEARNED.write_text(json.dumps(learned, ensure_ascii=False, indent=2), encoding="utf-8")
    stats = {
        "rows": rows,
        "kept": kept,
        "skipped": skipped,
        "chars": chars,
        "learned_seed": len(learned),
        "seconds": round(time.time() - t0, 1),
        "corpus_path": str(OUT_CORPUS),
        "top_sources": sorted(sources.items(), key=lambda x: -x[1])[:12],
    }
    print("DONE", json.dumps(stats, ensure_ascii=False), flush=True)
    return stats


def merge_into_train(max_tulu_chars: int = 80_000_000) -> None:
    """Append tulu corpus onto train_corpus + active corpus (capped)."""
    tulu = OUT_CORPUS.read_text(encoding="utf-8") if OUT_CORPUS.exists() else ""
    if not tulu:
        raise SystemExit("tulu corpus missing — run ingest first")
    tulu = tulu[:max_tulu_chars]
    train_path = ROOT / "data" / "train_corpus.txt"
    # Prefer original code HF slice if present; else current train
    code_path = ROOT / "data" / "hf_python_corpus.txt"
    if code_path.exists() and code_path.stat().st_size > 1000:
        code = code_path.read_text(encoding="utf-8")
    else:
        code = train_path.read_text(encoding="utf-8") if train_path.exists() else ""
    # Full train archive on disk
    merged = (code.rstrip() + "\n\n" + tulu).strip() + "\n"
    train_path.write_text(merged, encoding="utf-8")
    # Active corpus for the tiny char-RNN: balance code + chat (12 MB cap)
    code_part = code[:4_000_000]
    tulu_part = tulu[:8_000_000]
    active = (code_part.rstrip() + "\n\n" + tulu_part).strip() + "\n"
    (ROOT / "data" / "corpus.txt").write_text(active[:12_000_000], encoding="utf-8")
    # Deploy: quality chat slice + some code
    deploy = ROOT / "data" / "deploy_corpus.txt"
    old = deploy.read_text(encoding="utf-8") if deploy.exists() else code[:500_000]
    chat_slice = tulu[:600_000]
    deploy.write_text((old.rstrip() + "\n\n" + chat_slice).strip()[:2_000_000] + "\n", encoding="utf-8")
    print(
        f"merged train={len(merged):,} chars; active code={len(code_part):,} + tulu={len(tulu_part):,}; "
        f"deploy+=chat {len(chat_slice):,}",
        flush=True,
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-rows", type=int, default=0, help="0 = all rows")
    ap.add_argument("--learned-cap", type=int, default=1500)
    ap.add_argument("--merge", action="store_true", help="merge into train/deploy after ingest")
    ap.add_argument("--merge-only", action="store_true")
    args = ap.parse_args()
    if args.merge_only:
        merge_into_train()
        return
    ingest(max_rows=args.max_rows or None, learned_cap=args.learned_cap)
    if args.merge:
        merge_into_train()


if __name__ == "__main__":
    main()
