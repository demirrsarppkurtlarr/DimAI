"""Train and continuously self-improve the code model. No external AI APIs."""
from __future__ import annotations

import ast
import json
import random
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import numpy as np

from model.char_rnn import CharRNN, Vocab

ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = ROOT / "data" / "corpus.txt"
CHECKPOINT = ROOT / "checkpoints" / "model.npz"
STATE_PATH = ROOT / "checkpoints" / "trainer_state.json"

PROMPTS = [
    "def ",
    "def add",
    "def sum_",
    "def is_",
    "class ",
    "if __name__",
    "def main",
    "def filter_",
    "def map_",
    "def try_",
]


@dataclass
class TrainerState:
    steps: int = 0
    self_train_rounds: int = 0
    accepted: int = 0
    rejected: int = 0
    last_loss: float = 0.0
    last_accepted: str = ""
    running: bool = False
    message: str = "idle"
    history: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "steps": self.steps,
            "self_train_rounds": self.self_train_rounds,
            "accepted": self.accepted,
            "rejected": self.rejected,
            "last_loss": self.last_loss,
            "last_accepted": self.last_accepted[-500:],
            "running": self.running,
            "message": self.message,
            "history": self.history[-50:],
        }


class CodeTrainer:
    def __init__(self, hidden_size: int = 128, seq_len: int = 80):
        self.hidden_size = hidden_size
        self.seq_len = seq_len
        self.lock = threading.RLock()
        self.state = TrainerState()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.rng = np.random.default_rng(7)
        self.corpus = ""
        self.vocab: Optional[Vocab] = None
        self.model: Optional[CharRNN] = None
        self.replay: List[str] = []
        self._load_or_init()

    def _load_or_init(self) -> None:
        if not CORPUS_PATH.exists():
            from data.build_corpus import main as build_main
            build_main()
        self.corpus = CORPUS_PATH.read_text(encoding="utf-8")
        if CHECKPOINT.exists() and CHECKPOINT.with_suffix(".json").exists():
            self.model, self.vocab, meta = CharRNN.load(CHECKPOINT)
            self.state.steps = int(meta.get("steps", 0))
            self.state.accepted = int(meta.get("accepted", 0))
            self.state.rejected = int(meta.get("rejected", 0))
            self.state.self_train_rounds = int(meta.get("self_train_rounds", 0))
            self.state.message = "checkpoint loaded"
        else:
            self.vocab = Vocab.from_text(self.corpus)
            self.model = CharRNN(self.vocab.size, self.hidden_size)
            self.state.message = "new model initialized"

    def save(self) -> None:
        with self.lock:
            assert self.model and self.vocab
            meta = {
                "steps": self.state.steps,
                "accepted": self.state.accepted,
                "rejected": self.state.rejected,
                "self_train_rounds": self.state.self_train_rounds,
                "last_loss": self.state.last_loss,
            }
            self.model.save(CHECKPOINT, self.vocab, meta)
            STATE_PATH.write_text(json.dumps(self.state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def _random_slice_ids(self) -> List[int]:
        assert self.vocab
        # Bias training windows toward real code starts for faster structure learning
        if self.rng.random() < 0.55:
            anchors = ["def ", "class ", "if __name__"]
            anchor = anchors[int(self.rng.integers(0, len(anchors)))]
            positions = []
            start_at = 0
            while True:
                found = self.corpus.find(anchor, start_at)
                if found < 0:
                    break
                positions.append(found)
                start_at = found + len(anchor)
            if positions:
                pos = positions[int(self.rng.integers(0, len(positions)))]
                chunk = self.corpus[pos : pos + self.seq_len + 1]
                ids = self.vocab.encode(chunk)
                if len(ids) >= 16:
                    return ids
        ids = self.vocab.encode(self.corpus)
        if len(ids) <= self.seq_len + 1:
            return ids
        start = int(self.rng.integers(0, len(ids) - self.seq_len - 1))
        return ids[start : start + self.seq_len + 1]

    def train_steps(self, n: int = 50, lr: float = 0.05) -> float:
        with self.lock:
            assert self.model and self.vocab
            losses = []
            for _ in range(n):
                seq = self._random_slice_ids()
                loss = self.model.train_sequence(seq, lr=lr)
                losses.append(loss)
                self.state.steps += 1
            self.state.last_loss = float(np.mean(losses)) if losses else 0.0
            self.state.message = f"trained {n} steps, loss={self.state.last_loss:.3f}"
            return self.state.last_loss

    def generate(self, prompt: str = "def ", n_chars: int = 180, temperature: float = 0.7) -> str:
        with self.lock:
            assert self.model and self.vocab
            seed = prompt if prompt else "def "
            # map unknown chars away
            seed_ids = self.vocab.encode(seed)
            if not seed_ids:
                seed_ids = self.vocab.encode("def ")
            ids = self.model.sample(seed_ids, n_chars=n_chars, temperature=temperature, rng=self.rng)
            text = self.vocab.decode(ids)
            return text

    @staticmethod
    def longest_valid_prefix(code: str) -> Optional[str]:
        code = code.replace("\t", "    ")
        lines = code.splitlines()
        best = None
        for end in range(len(lines), 0, -1):
            cand = "\n".join(lines[:end]).strip()
            if len(cand) < 24:
                continue
            if not (cand.startswith("def ") or cand.startswith("class ") or cand.startswith("if ")):
                continue
            try:
                tree = ast.parse(cand)
            except SyntaxError:
                continue
            if not tree.body:
                continue
            # Require at least one function/class with a body statement
            ok_node = False
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if node.body:
                        ok_node = True
                        break
                elif isinstance(node, ast.If) and node.body:
                    ok_node = True
                    break
            if ok_node:
                best = cand
                break
        return best

    @classmethod
    def is_valid_python(cls, code: str) -> bool:
        return cls.longest_valid_prefix(code) is not None

    def append_to_corpus(self, code: str) -> None:
        block = "\n\n" + code.strip() + "\n\n"
        # Always append on disk so in-memory stale corpus cannot wipe HF data
        with CORPUS_PATH.open("a", encoding="utf-8") as f:
            f.write(block)
        self.corpus += block

    # ------------------------------------------------------------------
    # Improved self-training: adaptive temperature/lr, quality filter,
    # replay buffer of accepted snippets, deduplication.
    # ------------------------------------------------------------------

    def _acceptance_rate(self) -> float:
        total = self.state.accepted + self.state.rejected
        return self.state.accepted / total if total else 0.0

    def _adaptive_lr(self) -> float:
        # Cool down as the model matures
        base = 0.05
        decay = 0.9997 ** max(self.state.steps - 2000, 0)
        return max(base * decay, 0.008)

    def _adaptive_temperature(self) -> float:
        # Explore more when the model is accepting a lot; play safe when failing
        rate = self._acceptance_rate()
        if rate < 0.15:
            return 0.4
        if rate < 0.35:
            return 0.55
        return 0.7

    @staticmethod
    def _quality_score(code: str) -> float:
        """Heuristic quality: reward structure, penalize repetition."""
        lines = [ln for ln in code.splitlines() if ln.strip()]
        if not lines:
            return 0.0
        score = 0.0
        if code.startswith(("def ", "class ")):
            score += 1.0
        if "return" in code or "print(" in code:
            score += 0.6
        if len(lines) >= 3:
            score += 0.5
        # repetition penalty: many identical lines = degenerate output
        unique_ratio = len(set(lines)) / len(lines)
        score *= unique_ratio
        # nonsense identifier penalty: too many 1-2 char words
        words = re.findall(r"[a-zA-Z_]{1,}", code)
        if words:
            short = sum(1 for w in words if len(w) <= 2 and w not in ("a", "b", "i", "j", "n", "x", "y", "s", "f", "k", "v"))
            score *= max(0.2, 1.0 - short / max(len(words), 1))
        return score

    def self_train_once(self) -> dict:
        prompt = random.choice(PROMPTS)
        temp = self._adaptive_temperature()
        generated = self.generate(prompt=prompt, n_chars=220, temperature=temp)
        snippet = generated.strip()
        parts = snippet.split("\n\n")
        if len(parts) > 1 and len(parts[0]) > 30:
            snippet = parts[0]
        valid = self.longest_valid_prefix(snippet)
        quality = self._quality_score(valid) if valid else 0.0
        ok = valid is not None and quality >= 0.8
        if valid:
            snippet = valid
        result = {"prompt": prompt, "ok": ok, "snippet": snippet[:400], "quality": round(quality, 2)}
        lr = self._adaptive_lr()
        with self.lock:
            self.state.self_train_rounds += 1
            if ok:
                self.state.accepted += 1
                self.state.last_accepted = snippet
                # dedup: only grow corpus with genuinely new snippets
                if snippet not in self.corpus:
                    self.append_to_corpus(snippet)
                self.replay.append(snippet)
                if len(self.replay) > 200:
                    self.replay.pop(0)
                self.state.message = f"kabul (kalite {quality:.1f}) — pekiştiriliyor"
                ids = self.vocab.encode(snippet) if self.vocab else []
                if self.model and len(ids) >= 2:
                    reps = 3 + int(min(quality, 2.0) * 2)  # better code → more reinforcement
                    for _ in range(reps):
                        self.model.train_sequence(ids[: min(len(ids), self.seq_len + 1)], lr=lr * 0.8)
                        self.state.steps += 1
                loss = self.train_steps(n=8, lr=lr)
            else:
                self.state.rejected += 1
                self.state.message = "red — temel veriyle tekrar çalışılıyor"
                loss = self.train_steps(n=14, lr=lr)
                # replay: rehearse previously accepted good code
                if self.replay and self.model and self.vocab:
                    sample = random.choice(self.replay)
                    ids = self.vocab.encode(sample)
                    if len(ids) >= 2:
                        self.model.train_sequence(ids[: self.seq_len + 1], lr=lr * 0.6)
                        self.state.steps += 1
            result["loss"] = loss
            self.state.history.append(
                {
                    "t": time.time(),
                    "ok": ok,
                    "prompt": prompt,
                    "preview": snippet[:120],
                    "loss": self.state.last_loss,
                }
            )
        return result

    def bootstrap_train(self, steps: int = 400) -> float:
        self.state.message = "bootstrap training"
        # decaying lr
        chunks = max(steps // 50, 1)
        loss = 0.0
        for i in range(chunks):
            lr = 0.08 * (0.92 ** i)
            loss = self.train_steps(n=50, lr=lr)
        self.save()
        self.state.message = f"bootstrap done, loss={loss:.3f}"
        return loss

    def start_autolearn(self, interval_sec: float = 1.5) -> None:
        if self._thread and self._thread.is_alive():
            self.state.running = True
            return

        self._stop.clear()

        def loop():
            self.state.running = True
            self.state.message = "autolearn running"
            while not self._stop.is_set():
                try:
                    self.self_train_once()
                    if self.state.self_train_rounds % 10 == 0:
                        self.save()
                except Exception as exc:  # keep loop alive
                    self.state.message = f"error: {exc}"
                time.sleep(interval_sec)
            self.state.running = False
            self.state.message = "autolearn stopped"
            self.save()

        self._thread = threading.Thread(target=loop, daemon=True, name="autolearn")
        self._thread.start()

    def stop_autolearn(self) -> None:
        self._stop.set()
        self.state.running = False
        self.state.message = "stopping autolearn"


# singleton used by server
trainer = CodeTrainer()
