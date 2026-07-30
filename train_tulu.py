#!/usr/bin/env python3
"""Train DimAI on the merged code + Tulu chat corpus after ingest."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

TARGET = int(os.environ.get("DIMAI_TULU_TARGET", "550000"))
EXTRA = int(os.environ.get("DIMAI_TULU_EXTRA", "80000"))
LR = 0.008


def main() -> None:
    root = Path(__file__).resolve().parent
    tulu = root / "data" / "tulu_chat_corpus.txt"
    if not tulu.exists() or tulu.stat().st_size < 1000:
        raise SystemExit("tulu_chat_corpus.txt missing — run data/ingest_tulu_chat.py first")

    # Ensure merge
    from data.ingest_tulu_chat import merge_into_train

    merge_into_train()

    from model.trainer import CodeTrainer

    tr = CodeTrainer(hidden_size=160, seq_len=120)
    start = tr.state.steps
    target = max(TARGET, start + EXTRA)
    print(f"tulu-train {start:,} -> {target:,} corpus={len(tr.corpus):,} chars", flush=True)
    t0 = time.time()
    next_log = start + 2000
    next_save = start + 5000
    while tr.state.steps < target:
        loss = tr.train_steps(n=100, lr=LR)
        if tr.state.steps >= next_log:
            rate = (tr.state.steps - start) / max(time.time() - t0, 1e-9)
            eta = (target - tr.state.steps) / max(rate, 1e-9)
            print(
                f"steps={tr.state.steps:,} loss={loss:.3f} {rate:.0f} st/s eta={eta/60:.0f}min",
                flush=True,
            )
            next_log += 2000
        if tr.state.steps >= next_save:
            tr.save()
            next_save += 5000
    tr.save()
    for prompt in ("User: What is Python?\nAssistant:", "User: Merhaba\nAssistant:", "def "):
        s = tr.generate(prompt, 160, 0.5)
        print("---", repr(prompt))
        print(s[:220], flush=True)
    try:
        from model import persist

        if persist.upload_checkpoint(root / "checkpoints"):
            print("checkpoint uploaded", flush=True)
    except Exception as exc:
        print("upload skipped", exc, flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
