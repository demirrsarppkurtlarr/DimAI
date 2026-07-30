"""Continue training the existing DimAI checkpoint until 200,000 steps.

Loads the saved checkpoint (vocab included), trains on the big HF corpus
with a smoothly decaying learning rate, saves every few thousand steps,
then restores the deploy-sized corpus.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

TARGET_STEPS = 200_000
LR_START = 0.02
LR_END = 0.004
LOG_EVERY = 2_000
SAVE_EVERY = 5_000


def main() -> None:
    root = Path(__file__).resolve().parent
    big = (root / "data" / "train_corpus.txt").read_text(encoding="utf-8")
    (root / "data" / "corpus.txt").write_text(big, encoding="utf-8")
    print(f"train corpus: {len(big):,} chars", flush=True)

    from model.trainer import CodeTrainer

    tr = CodeTrainer(hidden_size=160, seq_len=120)
    start = tr.state.steps
    print(f"resuming from {start:,} steps -> target {TARGET_STEPS:,}", flush=True)

    t0 = time.time()
    next_log = tr.state.steps + LOG_EVERY
    next_save = tr.state.steps + SAVE_EVERY
    loss = 0.0
    while tr.state.steps < TARGET_STEPS:
        p = (tr.state.steps - start) / max(1, TARGET_STEPS - start)
        lr = LR_START * (LR_END / LR_START) ** p
        loss = tr.train_steps(n=100, lr=lr)
        if tr.state.steps >= next_log:
            el = time.time() - t0
            rate = (tr.state.steps - start) / el
            eta = (TARGET_STEPS - tr.state.steps) / max(rate, 1e-9)
            print(
                f"steps={tr.state.steps:7,d} lr={lr:.4f} loss={loss:.3f} "
                f"{rate:.0f} st/s eta={eta/60:.0f}min",
                flush=True,
            )
            next_log += LOG_EVERY
        if tr.state.steps >= next_save:
            tr.save()
            next_save += SAVE_EVERY

    tr.save()
    print(f"reached {tr.state.steps:,} steps in {(time.time()-t0)/60:.1f} min", flush=True)

    for temp in (0.35, 0.55):
        s = tr.generate("def ", 160, temp)
        v = tr.longest_valid_prefix(s)
        print(f"--- temp={temp} valid={v is not None}")
        print((v or s)[:240], flush=True)

    ok = 0
    for _ in range(30):
        ok += int(tr.self_train_once()["ok"])
    print(f"self-train accepted {ok}/30, total steps {tr.state.steps}", flush=True)
    tr.save()

    deploy = (root / "data" / "deploy_corpus.txt").read_text(encoding="utf-8")
    (root / "data" / "corpus.txt").write_text(deploy, encoding="utf-8")
    print("deploy corpus restored")
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
