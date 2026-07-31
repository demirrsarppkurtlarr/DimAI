"""Ingest Turkish-heavy chat + code datasets from Hugging Face into DimAI.

Priority: Turkish instruct/chat (Alpaca/Evol/CoT/sohbet) + Turkish code
instructions, then complementary English code corpora.

Uses datasets-server only (Render-friendly). Writes:
  - data/tr_chat_learned_seed.json
  - data/tr_code_learned_seed.json
  - data/tr_chat_corpus.txt
  - data/tr_code_corpus.txt

These seeds are loaded at server boot into LearnedStore so chat/RAG
actually uses them — not just offline corpus files.
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
OUT_CHAT_SEED = ROOT / "data" / "tr_chat_learned_seed.json"
OUT_CODE_SEED = ROOT / "data" / "tr_code_learned_seed.json"
OUT_CHAT_CORPUS = ROOT / "data" / "tr_chat_corpus.txt"
OUT_CODE_CORPUS = ROOT / "data" / "tr_code_corpus.txt"

API = "https://datasets-server.huggingface.co/rows"
UA = "DimAI-tr-ingest/1.0"
FENCE = re.compile(r"```(?:python|py|dart|js|javascript)?\s*(.*?)```", re.S | re.I)
PAGE = 100

# kind: chat | code
SOURCES: list[dict[str, Any]] = [
    # -------- Turkish chat / instruct (weight) --------
    {
        "dataset": "TFLai/Turkish-Alpaca",
        "config": "default",
        "split": "train",
        "kind": "chat",
        "instruction": ("instruction",),
        "input": ("input",),
        "answer": ("output",),
        "cap": 1600,
        "lang": "tr",
    },
    {
        "dataset": "cenfis/alpaca-turkish-combined",
        "config": "default",
        "split": "train",
        "kind": "chat",
        "instruction": ("instruction",),
        "input": ("input",),
        "answer": ("output",),
        "cap": 1400,
        "lang": "tr",
    },
    {
        "dataset": "saillab/alpaca-turkish-cleaned",
        "config": "default",
        "split": "train",
        "kind": "chat",
        "instruction": ("instruction",),
        "input": ("input",),
        "answer": ("output",),
        "cap": 1200,
        "lang": "tr",
    },
    {
        "dataset": "malhajar/alpaca-evol-instruct-turkish",
        "config": "default",
        "split": "train",
        "kind": "chat",
        "instruction": ("evolved_instruct", "original_instruct"),
        "answer": ("response",),
        "cap": 1400,
        "lang": "tr",
    },
    {
        "dataset": "Bahadir26/turkce-sohbet-v2-17k",
        "config": "default",
        "split": "train",
        "kind": "chat",
        "messages": True,
        "cap": 3500,
        "lang": "tr",
    },
    {
        "dataset": "AlicanKiraz0/Turkish-CoT-Instruct-Dataset",
        "config": "default",
        "split": "train",
        "kind": "chat",
        "messages": True,
        "cap": 3000,
        "lang": "tr",
    },
    {
        "dataset": "Ba2han/Turkish_Chat-1402",
        "config": "default",
        "split": "train",
        "kind": "chat",
        "messages": True,
        "cap": 2000,
        "lang": "tr",
    },
    {
        "dataset": "merve/turkish_instructions",
        "config": "default",
        "split": "train",
        "kind": "chat",
        "instruction": ("talimat",),
        "input": (" giriş", "giriş", "giris"),
        "answer": (" çıktı", "çıktı", "cikti", "output"),
        "cap": 1500,
        "lang": "tr",
    },
    {
        "dataset": "turkish-nlp-suite/InstrucTurca",
        "config": "default",
        "split": "train",
        "kind": "chat",
        "instruction": ("Input", "input"),
        "answer": ("Output", "output"),
        "cap": 1500,
        "lang": "tr",
    },
    {
        "dataset": "halilibr/collected-turkish-instructions-v0.1",
        "config": "default",
        "split": "train",
        "kind": "chat",
        "instruction": ("question",),
        "answer": ("answer",),
        "cap": 2000,
        "lang": "tr",
    },
    {
        "dataset": "atasoglu/instruction-turkish",
        "config": "default",
        "split": "test",
        "kind": "chat",
        "instruction": ("prompt_turkish", "prompt"),
        "answer": ("completion_turkish", "completion"),
        "cap": 1500,
        "lang": "tr",
    },
    # -------- Turkish code --------
    {
        "dataset": "berhaan/Turkish-CodeAlpaca-20k",
        "config": "default",
        "split": "train",
        "kind": "code",
        "instruction": ("instruction",),
        "input": ("input",),
        "answer": ("output",),
        "cap": 2500,
        "lang": "tr",
    },
    {
        "dataset": "duxx/code-instruction-turkish",
        "config": "default",
        "split": "train",
        "kind": "code",
        "instruction": ("question",),
        "answer": ("answer",),
        "cap": 2500,
        "lang": "tr",
    },
    {
        "dataset": "erythropygia/Instruct-Python-Code-Turkish",
        "config": "default",
        "split": "train",
        "kind": "code",
        "instruction": ("instruction",),
        "answer": ("output",),
        "cap": 1500,
        "lang": "tr",
    },
    {
        "dataset": "alztrk/turkish-code-instructions",
        "config": "default",
        "split": "train",
        "kind": "code",
        "instruction": ("instruction",),
        "answer": ("response",),
        "cap": 1500,
        "lang": "tr",
    },
    {
        "dataset": "kilicai/turkish-sft-code-explanation-10k",
        "config": "default",
        "split": "train",
        "kind": "code",
        "messages": True,
        "cap": 2000,
        "lang": "tr",
    },
    # -------- Extra EN code (smaller share) --------
    {
        "dataset": "ise-uiuc/Magicoder-OSS-Instruct-75K",
        "config": "default",
        "split": "train",
        "kind": "code",
        "instruction": ("problem",),
        "answer": ("solution",),
        "lang_field": "lang",
        "lang_allow": {"python", "py"},
        "cap": 1500,
        "lang": "en",
    },
    {
        "dataset": "HuggingFaceH4/CodeAlpaca_20K",
        "config": "default",
        "split": "train",
        "kind": "code",
        "instruction": ("prompt",),
        "answer": ("completion",),
        "cap": 1200,
        "lang": "en",
    },
]


def _get_json(url: str) -> dict:
    for attempt in range(6):
        r = requests.get(url, headers={"User-Agent": UA}, timeout=45)
        if r.status_code == 429:
            time.sleep(2.0 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("HTTP 429 Too Many Requests")


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
        time.sleep(0.3)


def _first(row: dict, keys: tuple[str, ...] | None) -> str:
    if not keys:
        return ""
    for k in keys:
        if k in row and row[k] is not None:
            s = str(row[k]).strip()
            if s and s.lower() not in {"none", "null", "nan"}:
                return s
        # fuzzy: strip spaces in key names (merve dataset)
        for rk, rv in row.items():
            if str(rk).strip() == str(k).strip() and rv is not None:
                s = str(rv).strip()
                if s and s.lower() not in {"none", "null", "nan"}:
                    return s
    return ""


def _from_messages(row: dict) -> tuple[str, str]:
    conv = row.get("messages") or row.get("conversations") or row.get("chat") or []
    if isinstance(conv, str):
        try:
            conv = ast.literal_eval(conv)
        except Exception:
            try:
                conv = json.loads(conv)
            except Exception:
                return "", ""
    if not isinstance(conv, list):
        return "", ""
    user, assistant = "", ""
    for turn in conv:
        if not isinstance(turn, dict):
            continue
        role = str(turn.get("role") or turn.get("from") or "").lower()
        val = str(turn.get("content") or turn.get("value") or "").strip()
        if not val:
            continue
        if role in {"system"}:
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
        if len(code) < 40:
            continue
        if not any(tok in code for tok in ("def ", "class ", "import ", "from ", "function ", "void ")):
            # still keep short TR code alpaca snippets if parseable python
            pass
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            try:
                ast.parse(code)
            except SyntaxError:
                if "def " not in code and "class " not in code:
                    continue
        out.append(code[:4000])
    return out


def _looks_turkish(text: str) -> bool:
    t = text or ""
    if any(ch in t for ch in "çğıöşüÇĞİÖŞÜ"):
        return True
    # common TR tokens without diacritics
    fold = (
        t.lower()
        .replace("ı", "i")
        .replace("İ", "i")
        .translate(str.maketrans("çğıöşü", "cgiosu"))
    )
    hits = sum(
        1
        for w in (
            " nedir", "nasil", "icin", "bir ", "ve ", "ile ", "olan", "olarak",
            "yaz", "olustur", "acikla", "ornek", "fonksiyon", "kod",
        )
        if w in f" {fold} "
    )
    return hits >= 2


def ingest(
    *,
    chat_seed_cap: int = 7000,
    code_seed_cap: int = 3500,
    max_chat_chars: int = 8_000_000,
    max_code_chars: int = 5_000_000,
) -> dict:
    OUT_CHAT_SEED.parent.mkdir(parents=True, exist_ok=True)
    chat_seed: list[dict] = []
    code_seed: list[dict] = []
    seen_chat: set[str] = set()
    seen_code: set[str] = set()
    chat_chars = 0
    code_chars = 0
    stats: dict[str, int] = {}
    t0 = time.time()

    chat_tmp = OUT_CHAT_CORPUS.with_suffix(".tmp")
    code_tmp = OUT_CODE_CORPUS.with_suffix(".tmp")

    with chat_tmp.open("w", encoding="utf-8") as chat_out, code_tmp.open(
        "w", encoding="utf-8"
    ) as code_out:
        for src in SOURCES:
            ds = src["dataset"]
            kind = src["kind"]
            cap = int(src.get("cap") or 2000)
            # Fair seed slots per source so Alpaca cannot starve sohbet/CoT
            seed_budget = 900 if kind == "chat" else 700
            seed_from_src = 0
            # Per-source char budget from remaining global pool
            remaining = max(1, sum(1 for s in SOURCES[SOURCES.index(src) :] if s["kind"] == kind))
            if kind == "chat":
                char_budget = max(250_000, (max_chat_chars - chat_chars) // remaining)
            else:
                char_budget = max(200_000, (max_code_chars - code_chars) // remaining)
            print(
                f"→ [{kind}/{src.get('lang','?')}] {ds} (rows≤{cap}, chars≈{char_budget:,})",
                flush=True,
            )
            n = 0
            src_chars0 = chat_chars if kind == "chat" else code_chars
            for row in _iter_rows(ds, src["config"], src["split"], cap):
                used = (chat_chars if kind == "chat" else code_chars) - src_chars0
                if used >= char_budget:
                    break
                if kind == "chat" and chat_chars >= max_chat_chars:
                    break
                if kind == "code" and code_chars >= max_code_chars:
                    break

                if src.get("lang_field"):
                    lang = str(row.get(src["lang_field"]) or "").strip().lower()
                    allow = {x.lower() for x in (src.get("lang_allow") or set())}
                    if allow and lang not in allow:
                        continue

                if src.get("messages"):
                    prompt, answer = _from_messages(row)
                    extra = ""
                else:
                    prompt = _first(row, tuple(src.get("instruction") or ()))
                    extra = _first(row, tuple(src.get("input") or ()))
                    answer = _first(row, tuple(src.get("answer") or ()))

                if extra and extra not in prompt:
                    prompt = f"{prompt}\n\nGirdi:\n{extra}".strip()
                prompt = (prompt or "").strip()
                answer = (answer or "").strip()
                if len(prompt) < 8 or len(answer) < 16:
                    continue

                prompt_s = prompt[:900]
                answer_s = answer[:2800]
                block = f"User: {prompt_s}\nAssistant: {answer_s}\n\n"

                if kind == "chat":
                    chat_out.write(block)
                    chat_chars += len(block)
                    if (
                        len(chat_seed) < chat_seed_cap
                        and seed_from_src < seed_budget
                    ):
                        key = prompt_s[:56].lower()
                        if key not in seen_chat and 12 <= len(prompt_s) <= 420:
                            chat_seed.append(
                                {
                                    "q": prompt_s[:300],
                                    "a": answer_s[:2500],
                                    "url": f"hf://{ds}",
                                    "quality": 0.92,
                                    "source": ds,
                                    "lang": "tr",
                                }
                            )
                            seen_chat.add(key)
                            seed_from_src += 1
                else:
                    code_out.write(block)
                    code_chars += len(block)
                    codes = _extract_code(answer_s)
                    for c in codes[:2]:
                        code_out.write(c + "\n\n")
                        code_chars += len(c)
                    if (
                        len(code_seed) < code_seed_cap
                        and seed_from_src < seed_budget
                    ):
                        key = prompt_s[:56].lower()
                        if key not in seen_code and 12 <= len(prompt_s) <= 420:
                            entry = {
                                "q": prompt_s[:300],
                                "a": answer_s[:2500],
                                "url": f"hf://{ds}",
                                "quality": 0.93,
                                "source": ds,
                                "lang": src.get("lang") or "tr",
                            }
                            if codes:
                                entry["c"] = codes[0][:3000]
                                entry["l"] = "python"
                            code_seed.append(entry)
                            seen_code.add(key)
                            seed_from_src += 1

                n += 1
                if n % 500 == 0:
                    print(
                        f"  {ds}: +{n} chat_chars={chat_chars:,} code_chars={code_chars:,}",
                        flush=True,
                    )

            stats[ds] = n
            print(f"  {ds}: +{n}", flush=True)
            time.sleep(0.8)

    chat_tmp.replace(OUT_CHAT_CORPUS)
    code_tmp.replace(OUT_CODE_CORPUS)
    OUT_CHAT_SEED.write_text(json.dumps(chat_seed, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_CODE_SEED.write_text(json.dumps(code_seed, ensure_ascii=False, indent=2), encoding="utf-8")
    result = {
        "chat_seed": len(chat_seed),
        "code_seed": len(code_seed),
        "chat_chars": chat_chars,
        "code_chars": code_chars,
        "seconds": round(time.time() - t0, 1),
        "per_source": stats,
    }
    print("DONE", json.dumps(result, ensure_ascii=False), flush=True)
    return result


def merge_into_active(*, active_cap: int = 12_000_000) -> None:
    """Blend TR chat+code into active/train corpora used by char-RNN."""
    chat = OUT_CHAT_CORPUS.read_text(encoding="utf-8") if OUT_CHAT_CORPUS.exists() else ""
    code = OUT_CODE_CORPUS.read_text(encoding="utf-8") if OUT_CODE_CORPUS.exists() else ""
    prior_code = ""
    hf = ROOT / "data" / "hf_python_corpus.txt"
    if hf.exists():
        prior_code = hf.read_text(encoding="utf-8")[:2_500_000]
    instruct = ROOT / "data" / "code_instruct_corpus.txt"
    if instruct.exists():
        prior_code = (prior_code + "\n\n" + instruct.read_text(encoding="utf-8")[:2_000_000]).strip()

    # Active: Turkish chat dominates, then code
    active = (
        chat[:5_500_000]
        + "\n\n"
        + code[:3_500_000]
        + "\n\n"
        + prior_code[:2_000_000]
    ).strip() + "\n"
    (ROOT / "data" / "corpus.txt").write_text(active[:active_cap], encoding="utf-8")

    train = (prior_code + "\n\n" + code[:4_000_000] + "\n\n" + chat[:6_000_000]).strip() + "\n"
    (ROOT / "data" / "train_corpus.txt").write_text(train, encoding="utf-8")

    deploy = ROOT / "data" / "deploy_corpus.txt"
    old = deploy.read_text(encoding="utf-8") if deploy.exists() else ""
    deploy.write_text(
        (chat[:900_000] + "\n\n" + code[:600_000] + "\n\n" + old[:800_000]).strip()[:2_500_000]
        + "\n",
        encoding="utf-8",
    )
    print(
        f"merged active={min(len(active), active_cap):,} train={len(train):,} "
        f"chat={len(chat):,} code={len(code):,}",
        flush=True,
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chat-seed-cap", type=int, default=7000)
    ap.add_argument("--code-seed-cap", type=int, default=3500)
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--merge-only", action="store_true")
    args = ap.parse_args()
    if args.merge_only:
        merge_into_active()
        return
    ingest(chat_seed_cap=args.chat_seed_cap, code_seed_cap=args.code_seed_cap)
    if args.merge:
        merge_into_active()


if __name__ == "__main__":
    main()
