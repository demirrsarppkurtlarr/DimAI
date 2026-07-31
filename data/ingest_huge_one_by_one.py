"""Integrate HUGE Hugging Face datasets into DimAI — one dataset at a time.

Target scale: sources that are 100M–1B+ rows/tokens class (e.g.
tascib/turkish-llm-dataset ~153M estimated rows, the-stack python tens of
millions of files, OpenOrca ~3M instruct pairs).

Constraints (Render free / ephemeral disk / tiny char-RNN):
  - We STREAM via datasets-server; we do NOT download full multi-GB dumps.
  - Each dataset is ingested separately (`--dataset <id>`) with a fair slice.
  - Slices feed: corpus shards + learned RAG seeds loaded at boot.

This is the honest path to absorb 500M-scale *sources* into DimAI without
pretending a free-tier box can hold hundreds of millions of raw rows.
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

import requests

ROOT = Path(__file__).resolve().parents[1]
SHARD_DIR = ROOT / "data" / "huge_shards"
MANIFEST = ROOT / "data" / "huge_manifest.json"
COMBINED_SEED = ROOT / "data" / "huge_learned_seed.json"
API = "https://datasets-server.huggingface.co/rows"
SIZE_API = "https://datasets-server.huggingface.co/size"
UA = "DimAI-huge-ingest/1.0"
FENCE = re.compile(r"```(?:python|py)?\s*(.*?)```", re.S | re.I)
PAGE = 100

# One-by-one registry. estimated_rows from HF size API / docs (order of magnitude).
# kind: pretrain_text | chat | code
HUGE_SOURCES: list[dict[str, Any]] = [
    {
        "id": "tascib/turkish-llm-dataset",
        "kind": "pretrain_text",
        "lang": "tr",
        "config": "default",
        "split": "train",
        "text": ("text",),
        "estimated_rows": 152_904_318,
        "estimated_tokens": 500_000_000,  # order-of-magnitude (multi-GB TR corpus)
        "row_cap": 8000,
        "char_cap": 4_000_000,
        "seed_cap": 1200,
    },
    {
        "id": "epfml/FineWeb2-HQ",
        "kind": "pretrain_text",
        "lang": "tr",
        "config": "tur_Latn",
        "split": "train",
        "text": ("text",),
        "estimated_rows": 50_000_000,
        "estimated_tokens": 200_000_000,
        "row_cap": 5000,
        "char_cap": 3_000_000,
        "seed_cap": 800,
    },
    {
        "id": "Open-Orca/OpenOrca",
        "kind": "chat",
        "lang": "en",
        "config": "default",
        "split": "train",
        "instruction": ("question",),
        "answer": ("response",),
        "estimated_rows": 2_942_000,
        "estimated_tokens": 1_000_000_000,
        "row_cap": 6000,
        "char_cap": 3_500_000,
        "seed_cap": 1500,
    },
    {
        "id": "Open-Orca/SlimOrca",
        "kind": "chat",
        "lang": "en",
        "config": "default",
        "split": "train",
        "messages": True,
        "estimated_rows": 500_000,
        "estimated_tokens": 200_000_000,
        "row_cap": 4000,
        "char_cap": 2_500_000,
        "seed_cap": 1000,
    },
    {
        "id": "HuggingFaceH4/ultrachat_200k",
        "kind": "chat",
        "lang": "en",
        "config": "default",
        "split": "train_sft",
        "messages": True,
        "estimated_rows": 200_000,
        "estimated_tokens": 150_000_000,
        "row_cap": 4000,
        "char_cap": 2_500_000,
        "seed_cap": 1000,
    },
    {
        "id": "OpenAssistant/oasst1",
        "kind": "chat",
        "lang": "multi",
        "config": "default",
        "split": "train",
        "oasst": True,
        "estimated_rows": 80_000,
        "estimated_tokens": 40_000_000,
        "row_cap": 5000,
        "char_cap": 2_000_000,
        "seed_cap": 900,
    },
    {
        "id": "Aeala/ShareGPT_Vicuna_unfiltered",
        "kind": "chat",
        "lang": "en",
        "config": "default",
        "split": "train",
        "messages": True,
        "estimated_rows": 90_000,
        "estimated_tokens": 80_000_000,
        "row_cap": 4000,
        "char_cap": 2_500_000,
        "seed_cap": 1000,
    },
    {
        "id": "zahide/turkish-instructions-220k",
        "kind": "chat",
        "lang": "tr",
        "config": "default",
        "split": "train",
        "instruction": ("instruction",),
        "answer": ("output",),
        "estimated_rows": 220_000,
        "estimated_tokens": 80_000_000,
        "row_cap": 5000,
        "char_cap": 3_000_000,
        "seed_cap": 1500,
    },
    {
        "id": "matrixportalx/aya-turkish-alpaca",
        "kind": "chat",
        "lang": "tr",
        "config": "default",
        "split": "train",
        "instruction": ("instruction",),
        "input": ("input",),
        "answer": ("output",),
        "estimated_rows": 1_000_000,
        "estimated_tokens": 300_000_000,
        "row_cap": 5000,
        "char_cap": 3_000_000,
        "seed_cap": 1500,
    },
    {
        "id": "xszheng2020/the_stack_dedup_python",
        "kind": "code",
        "lang": "code",
        "config": "default",
        "split": "train",
        "text": ("content", "file_content", "text", "code"),
        "estimated_rows": 12_962_249,
        "estimated_tokens": 10_000_000_000,
        "row_cap": 4000,
        "char_cap": 3_500_000,
        "seed_cap": 800,
    },
    {
        "id": "jon-tow/starcoderdata-python-edu",
        "kind": "code",
        "lang": "code",
        "config": "default",
        "split": "train",
        "text": ("content",),
        "estimated_rows": 1_000_000,
        "estimated_tokens": 2_000_000_000,
        "row_cap": 4000,
        "char_cap": 3_000_000,
        "seed_cap": 800,
    },
    {
        "id": "PatrickHaller/the-stack-python-1M",
        "kind": "code",
        "lang": "code",
        "config": "default",
        "split": "train",
        "text": ("content", "file_content", "text", "code"),
        "estimated_rows": 1_000_000,
        "estimated_tokens": 2_000_000_000,
        "row_cap": 3500,
        "char_cap": 2_500_000,
        "seed_cap": 700,
    },
    {
        "id": "TokenBender/code_instructions_122k_alpaca_style",
        "kind": "code",
        "lang": "en",
        "config": "default",
        "split": "train",
        "instruction": ("instruction",),
        "input": ("input",),
        "answer": ("output",),
        "estimated_rows": 122_000,
        "estimated_tokens": 60_000_000,
        "row_cap": 5000,
        "char_cap": 3_000_000,
        "seed_cap": 1200,
    },
    {
        "id": "iamtarun/code_instructions_120k_alpaca",
        "kind": "code",
        "lang": "en",
        "config": "default",
        "split": "train",
        "instruction": ("instruction",),
        "input": ("input",),
        "answer": ("output",),
        "estimated_rows": 120_000,
        "estimated_tokens": 60_000_000,
        "row_cap": 5000,
        "char_cap": 3_000_000,
        "seed_cap": 1200,
    },
    {
        "id": "Nan-Do/instructional_code-search-net-python",
        "kind": "code",
        "lang": "en",
        "config": "default",
        "split": "train",
        "instruction": ("INSTRUCTION",),
        "answer": ("RESPONSE",),
        "estimated_rows": 400_000,
        "estimated_tokens": 100_000_000,
        "row_cap": 4000,
        "char_cap": 2_500_000,
        "seed_cap": 1000,
    },
]


def _slug(ds_id: str) -> str:
    return ds_id.replace("/", "__")


def _get_json(url: str) -> dict:
    for attempt in range(6):
        r = requests.get(url, headers={"User-Agent": UA}, timeout=50)
        if r.status_code == 429:
            time.sleep(2.2 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("rate limited")


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
        try:
            payload = _get_json(f"{API}?{qs}")
        except Exception as exc:
            print(f"  [warn] {dataset}@{offset}: {exc}", flush=True)
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
        time.sleep(0.28)


def _first(row: dict, keys: tuple[str, ...] | None) -> str:
    if not keys:
        return ""
    for k in keys:
        v = row.get(k)
        if v is None:
            continue
        s = str(v).strip()
        if s and s.lower() not in {"none", "null", "nan"}:
            return s
    return ""


def _from_messages(row: dict) -> tuple[str, str]:
    conv = row.get("conversations") or row.get("messages") or row.get("data") or []
    if isinstance(conv, str):
        try:
            conv = ast.literal_eval(conv)
        except Exception:
            try:
                conv = json.loads(conv)
            except Exception:
                return "", ""
    # UltraChat: list of alternating strings
    if isinstance(conv, list) and conv and isinstance(conv[0], str):
        if len(conv) >= 2:
            return str(conv[0]).strip(), str(conv[1]).strip()
        return "", ""
    if not isinstance(conv, list):
        return "", ""
    user, assistant = "", ""
    for turn in conv:
        if not isinstance(turn, dict):
            continue
        role = str(turn.get("role") or turn.get("from") or "").lower()
        val = str(
            turn.get("content")
            or turn.get("value")
            or turn.get("text")
            or ""
        ).strip()
        if not val or role == "system":
            continue
        if role in {"user", "human"} and not user:
            user = val
        elif role in {"assistant", "gpt", "bot", "model"} and user and not assistant:
            assistant = val
    return user, assistant


def _extract_code(text: str) -> list[str]:
    blocks = FENCE.findall(text or "")
    if not blocks:
        blocks = [text or ""]
    out: list[str] = []
    for b in blocks:
        code = "".join(ch for ch in b if ch == "\n" or 32 <= ord(ch) < 127).strip()
        if len(code) < 50:
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            try:
                import ast as _ast

                _ast.parse(code)
            except SyntaxError:
                if "def " not in code and "class " not in code:
                    continue
        out.append(code[:4000])
    return out


def list_sources() -> None:
    total_tokens = sum(int(s.get("estimated_tokens") or 0) for s in HUGE_SOURCES)
    total_rows = sum(int(s.get("estimated_rows") or 0) for s in HUGE_SOURCES)
    print(f"sources={len(HUGE_SOURCES)} est_rows≈{total_rows:,} est_tokens≈{total_tokens:,}")
    for i, s in enumerate(HUGE_SOURCES, 1):
        print(
            f"{i:02d}. {s['id']}  kind={s['kind']} lang={s['lang']} "
            f"rows≈{s.get('estimated_rows',0):,} tokens≈{s.get('estimated_tokens',0):,}"
        )


def ingest_one(src: dict[str, Any]) -> dict:
    ds = src["id"]
    slug = _slug(ds)
    out_dir = SHARD_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    corpus_path = out_dir / "corpus.txt"
    seed_path = out_dir / "seed.json"
    meta_path = out_dir / "meta.json"

    print(
        f"\n=== INGEST {ds} ===\n"
        f"  kind={src['kind']} est_rows≈{src.get('estimated_rows',0):,} "
        f"est_tokens≈{src.get('estimated_tokens',0):,}\n"
        f"  slice rows≤{src['row_cap']} chars≤{src['char_cap']:,}",
        flush=True,
    )
    t0 = time.time()
    chars = 0
    kept = 0
    seed: list[dict] = []
    seen: set[str] = set()

    with corpus_path.open("w", encoding="utf-8") as out:
        for row in _iter_rows(ds, src["config"], src["split"], int(src["row_cap"])):
            if chars >= int(src["char_cap"]):
                break

            # OASST: pair consecutive assistant replies under Turkish/English prompts loosely
            if src.get("oasst"):
                role = str(row.get("role") or "")
                text = str(row.get("text") or "").strip()
                lang = str(row.get("lang") or "")
                if role != "assistant" or len(text) < 40:
                    continue
                # Prefer tr + en only
                if lang and lang not in {"tr", "en"}:
                    continue
                prompt = f"({lang or 'chat'}) OpenAssistant cevabı bağlamı"
                answer = text
            elif src.get("messages"):
                prompt, answer = _from_messages(row)
            elif src.get("instruction"):
                prompt = _first(row, tuple(src.get("instruction") or ()))
                extra = _first(row, tuple(src.get("input") or ()))
                answer = _first(row, tuple(src.get("answer") or ()))
                if extra and extra not in prompt:
                    prompt = f"{prompt}\n\nInput:\n{extra}".strip()
            else:
                # raw text / code file
                answer = _first(row, tuple(src.get("text") or ("text",)))
                prompt = ""
                if src["kind"] == "pretrain_text" and answer:
                    # turn into weak instruct for RAG: first sentence as q
                    head = answer.strip().split("\n", 1)[0][:120]
                    prompt = f"Şu metni özetle / devamını hatırla: {head}"
                elif src["kind"] == "code" and answer:
                    prompt = "Aşağıdaki kodu açıkla ve ne işe yaradığını söyle."

            prompt = (prompt or "").strip()
            answer = (answer or "").strip()
            if len(answer) < 40:
                continue
            if src["kind"] != "pretrain_text" and len(prompt) < 8:
                continue

            prompt_s = prompt[:900] if prompt else answer[:120]
            answer_s = answer[:3500]
            if src["kind"] in {"chat", "code"} and prompt:
                block = f"User: {prompt_s}\nAssistant: {answer_s}\n\n"
            else:
                block = answer_s + "\n\n"
            out.write(block)
            chars += len(block)
            kept += 1

            if len(seed) < int(src["seed_cap"]):
                key = answer_s[:96].lower()
                if key not in seen and 20 <= len(answer_s):
                    entry = {
                        "q": prompt_s[:300],
                        "a": answer_s[:2500],
                        "url": f"hf://{ds}",
                        "quality": 0.88,
                        "source": ds,
                        "lang": src.get("lang") or "",
                    }
                    if src["kind"] == "code":
                        codes = _extract_code(answer_s)
                        if codes:
                            entry["c"] = codes[0][:3000]
                            entry["l"] = "python"
                        elif "def " in answer_s or "class " in answer_s or "import " in answer_s:
                            entry["c"] = answer_s[:3000]
                            entry["l"] = "python"
                    seed.append(entry)
                    seen.add(key)

            if kept % 400 == 0:
                print(f"  {ds}: kept={kept} chars={chars:,}", flush=True)

    seed_path.write_text(json.dumps(seed, ensure_ascii=False, indent=2), encoding="utf-8")
    meta = {
        "dataset": ds,
        "kind": src["kind"],
        "lang": src.get("lang"),
        "estimated_rows": src.get("estimated_rows"),
        "estimated_tokens": src.get("estimated_tokens"),
        "kept_rows": kept,
        "chars": chars,
        "seed": len(seed),
        "seconds": round(time.time() - t0, 1),
        "corpus": str(corpus_path),
        "seed_path": str(seed_path),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print("  DONE", json.dumps(meta, ensure_ascii=False), flush=True)
    return meta


def rebuild_manifest_and_combined_seed(*, seed_limit: int = 8000) -> dict:
    SHARD_DIR.mkdir(parents=True, exist_ok=True)
    metas = []
    per_source_seeds: list[list[dict]] = []
    total_est_tokens = 0
    total_slice_chars = 0

    for src in HUGE_SOURCES:
        slug = _slug(src["id"])
        meta_path = SHARD_DIR / slug / "meta.json"
        seed_path = SHARD_DIR / slug / "seed.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            metas.append(meta)
            total_est_tokens += int(meta.get("estimated_tokens") or 0)
            total_slice_chars += int(meta.get("chars") or 0)
        rows: list[dict] = []
        if seed_path.exists():
            try:
                rows = json.loads(seed_path.read_text(encoding="utf-8"))
            except Exception:
                rows = []
        per_source_seeds.append(rows)

    # Fair round-robin so OpenOrca cannot starve code/TR shards
    combined: list[dict] = []
    seen: set[str] = set()
    max_len = max((len(x) for x in per_source_seeds), default=0)
    for i in range(max_len):
        for rows in per_source_seeds:
            if i >= len(rows) or len(combined) >= seed_limit:
                continue
            row = rows[i]
            key = str(row.get("q") or "")[:40] + "|" + str(row.get("a") or "")[:40]
            key = key.lower()
            if not key.strip("|") or key in seen:
                continue
            combined.append(row)
            seen.add(key)
        if len(combined) >= seed_limit:
            break

    COMBINED_SEED.write_text(
        json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    manifest = {
        "datasets_integrated": len(metas),
        "datasets_registered": len(HUGE_SOURCES),
        "estimated_source_tokens_sum": total_est_tokens,
        "slice_chars_sum": total_slice_chars,
        "combined_seed": len(combined),
        "note": "Full dumps are not stored; each source contributes a streamed slice. estimated_source_tokens_sum is the HF-scale of the *sources*.",
        "items": metas,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("MANIFEST", json.dumps({k: manifest[k] for k in manifest if k != "items"}, ensure_ascii=False), flush=True)
    return manifest


def merge_corpora_into_active(*, active_cap: int = 12_000_000) -> None:
    parts: list[str] = []
    # Prefer TR pretrain + TR chat first
    order = sorted(
        HUGE_SOURCES,
        key=lambda s: (
            0 if s.get("lang") == "tr" else 1,
            0 if s["kind"] == "chat" else 1 if s["kind"] == "code" else 2,
        ),
    )
    for src in order:
        p = SHARD_DIR / _slug(src["id"]) / "corpus.txt"
        if p.exists():
            parts.append(p.read_text(encoding="utf-8")[:2_000_000])
    # keep previous TR seeds corpus if present
    for extra in (
        ROOT / "data" / "tr_chat_corpus.txt",
        ROOT / "data" / "tr_code_corpus.txt",
        ROOT / "data" / "code_instruct_corpus.txt",
    ):
        if extra.exists():
            parts.append(extra.read_text(encoding="utf-8")[:1_500_000])
    blob = "\n\n".join(parts).strip() + "\n"
    (ROOT / "data" / "corpus.txt").write_text(blob[:active_cap], encoding="utf-8")
    (ROOT / "data" / "train_corpus.txt").write_text(blob[:20_000_000], encoding="utf-8")
    print(f"active corpus={min(len(blob), active_cap):,}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--dataset", type=str, default="", help="HF id to ingest (one)")
    ap.add_argument("--all", action="store_true", help="ingest every registered source one-by-one")
    ap.add_argument("--rebuild", action="store_true", help="rebuild manifest + combined seed")
    ap.add_argument("--merge", action="store_true")
    args = ap.parse_args()

    if args.list:
        list_sources()
        return

    if args.dataset:
        src = next((s for s in HUGE_SOURCES if s["id"] == args.dataset), None)
        if not src:
            raise SystemExit(f"unknown dataset: {args.dataset}")
        ingest_one(src)
        rebuild_manifest_and_combined_seed()
        if args.merge:
            merge_corpora_into_active()
        return

    if args.all:
        list_sources()
        for src in HUGE_SOURCES:
            try:
                ingest_one(src)
            except Exception as exc:
                print(f"FAILED {src['id']}: {exc}", flush=True)
            time.sleep(1.0)
        rebuild_manifest_and_combined_seed()
        if args.merge:
            merge_corpora_into_active()
        return

    if args.rebuild or args.merge:
        rebuild_manifest_and_combined_seed()
        if args.merge:
            merge_corpora_into_active()
        return

    ap.print_help()


if __name__ == "__main__":
    main()
