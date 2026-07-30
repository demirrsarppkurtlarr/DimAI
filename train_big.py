"""Big offline training run for DimAI.

1. Builds a large ASCII-clean training corpus from the HF download.
2. Trains a fresh model for many steps with lr schedule.
3. Saves checkpoint, then restores a deploy-sized corpus.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

TRAIN_STEPS = 30000
HIDDEN = 160
SEQ = 120
DEPLOY_EXTRA = 1_000_000  # deploy corpus: seed + 1MB


def build_corpora() -> None:
    from data.build_corpus import build_corpus

    root = Path(__file__).resolve().parent
    hf = (root / "data" / "hf_python_corpus.txt").read_text(encoding="utf-8")
    seed = build_corpus()

    # ASCII-only keeps vocab small (~95 chars) => fast, stable model
    clean = "".join(ch for ch in hf if ch == "\n" or 32 <= ord(ch) < 127)
    big = seed.strip() + "\n\n" + clean.strip() + "\n"
    (root / "data" / "train_corpus.txt").write_text(big, encoding="utf-8")
    print(f"train corpus: {len(big):,} chars")

    deploy = seed.strip() + "\n\n" + clean[:DEPLOY_EXTRA].strip() + "\n"
    (root / "data" / "corpus.txt").write_text(big, encoding="utf-8")  # train reads this
    (root / "data" / "deploy_corpus.txt").write_text(deploy, encoding="utf-8")
    print(f"deploy corpus: {len(deploy):,} chars")


def main() -> None:
    build_corpora()

    root = Path(__file__).resolve().parent
    for f in ("model.npz", "model.json", "trainer_state.json"):
        (root / "checkpoints" / f).unlink(missing_ok=True)

    from model.trainer import CodeTrainer

    t0 = time.time()
    tr = CodeTrainer(hidden_size=HIDDEN, seq_len=SEQ)
    print(f"vocab={tr.vocab.size} corpus={len(tr.corpus):,}")

    phases = 20
    per_phase = TRAIN_STEPS // phases
    for p in range(phases):
        lr = 0.075 * (0.88 ** p)
        loss = 0.0
        done = 0
        while done < per_phase:
            loss = tr.train_steps(n=50, lr=lr)
            done += 50
        el = time.time() - t0
        rate = tr.state.steps / el
        print(
            f"phase {p+1:2d}/{phases} steps={tr.state.steps:6d} lr={lr:.4f} "
            f"loss={loss:.3f} {rate:.0f} st/s elapsed={el:.0f}s",
            flush=True,
        )
        tr.save()

    # quick sample check
    for temp in (0.35, 0.55):
        s = tr.generate("def ", 160, temp)
        v = tr.longest_valid_prefix(s)
        print(f"--- temp={temp} valid={v is not None}")
        print((v or s)[:240])

    # self-train rounds
    ok = 0
    for _ in range(30):
        ok += int(tr.self_train_once()["ok"])
    print(f"self-train accepted {ok}/30, total steps {tr.state.steps}")
    tr.save()

    # restore deploy corpus
    deploy = (root / "data" / "deploy_corpus.txt").read_text(encoding="utf-8")
    (root / "data" / "corpus.txt").write_text(deploy, encoding="utf-8")
    print("deploy corpus restored")
    print(f"TOTAL time {(time.time()-t0)/60:.1f} min")


if __name__ == "__main__":
    main()
