"""Train and continuously self-improve the code model. No external AI APIs."""
from __future__ import annotations

import ast
import json
import os
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
    hf_offset: int = 0
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
            "hf_offset": self.hf_offset,
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
        self._ids: Optional[np.ndarray] = None
        self._ids_for_len = -1
        self._anchors: List[int] = []
        self._job_stop = threading.Event()
        self._job_thread: Optional[threading.Thread] = None
        self.job: dict = {"active": False}
        # Render'ın diski geçici: Supabase'de daha ileri bir model varsa onu al
        try:
            from model import persist
            persist.restore_if_newer(CHECKPOINT.parent)
        except Exception as exc:
            print(f"[trainer] restore skipped: {exc}", flush=True)
        self._load_or_init()

    def _rebuild_cache(self) -> None:
        """Pre-encode corpus once; makes training ~10x faster on big corpora."""
        assert self.vocab
        self._ids = np.array(self.vocab.encode(self.corpus), dtype=np.int32)
        self._ids_for_len = len(self.corpus)
        # anchor positions valid only if no character was skipped during encode
        if len(self._ids) == len(self.corpus):
            import re as _re
            self._anchors = [
                m.start() for m in _re.finditer(r"(?m)^(?:def |class |if __name__)", self.corpus)
            ]
        else:
            self._anchors = []

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
            self.state.hf_offset = int(meta.get("hf_offset", 0))
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
                "hf_offset": self.state.hf_offset,
            }
            self.model.save(CHECKPOINT, self.vocab, meta)
            STATE_PATH.write_text(json.dumps(self.state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def _random_slice_ids(self) -> List[int]:
        assert self.vocab
        if self._ids is None or self._ids_for_len != len(self.corpus):
            self._rebuild_cache()
        ids = self._ids
        n = len(ids)
        if n <= self.seq_len + 1:
            return ids.tolist()
        # Bias training windows toward real code starts for faster structure learning
        if self._anchors and self.rng.random() < 0.55:
            pos = self._anchors[int(self.rng.integers(0, len(self._anchors)))]
            if pos < n - self.seq_len - 1:
                return ids[pos : pos + self.seq_len + 1].tolist()
        start = int(self.rng.integers(0, n - self.seq_len - 1))
        return ids[start : start + self.seq_len + 1].tolist()

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

    # Smaller work units on tiny cloud instances (Render free = 0.1 CPU)
    LIGHT_MODE = os.environ.get("DIMAI_LIGHT", "0") == "1"

    def self_train_once(self) -> dict:
        prompt = random.choice(PROMPTS)
        temp = self._adaptive_temperature()
        n_chars = 120 if self.LIGHT_MODE else 220
        generated = self.generate(prompt=prompt, n_chars=n_chars, temperature=temp)
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
                    if self.LIGHT_MODE:
                        reps = min(reps, 2)
                    for _ in range(reps):
                        self.model.train_sequence(ids[: min(len(ids), self.seq_len + 1)], lr=lr * 0.8)
                        self.state.steps += 1
                loss = self.train_steps(n=2 if self.LIGHT_MODE else 8, lr=lr)
            else:
                self.state.rejected += 1
                self.state.message = "red — temel veriyle tekrar çalışılıyor"
                loss = self.train_steps(n=4 if self.LIGHT_MODE else 14, lr=lr)
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

    # -------------------- targeted training job --------------------

    def job_status(self) -> dict:
        job = dict(self.job)
        if job.get("active"):
            done = self.state.steps - job.get("start_steps", 0)
            total = job.get("requested", 1)
            job["done_steps"] = done
            job["progress"] = min(1.0, done / max(1, total))
            rate = done / max(1e-9, time.time() - job.get("started", time.time()))
            if rate > 0:
                job["eta_sec"] = int((total - done) / max(rate, 1e-9))
        return job

    def start_training_job(self, requested_steps: int) -> dict:
        """Train `requested_steps` more steps in the background.

        Collects fresh HF data along the way, saves periodically, and when
        the target is reached uploads the checkpoint to Supabase Storage so
        the learned weights survive restarts.
        """
        requested = max(100, min(int(requested_steps), 1_000_000))
        # NOT: burada self.lock ALINMAZ — autolearn turu kilidi uzun süre
        # tutabilir ve endpoint zaman aşımına uğrar. Kurulum kilitsiz güvenli.
        if self._job_thread and self._job_thread.is_alive():
            return self.job_status()
        was_autolearn = self.state.running
        self.stop_autolearn()
        self._job_stop.clear()
        self.job = {
            "active": True,
            "requested": requested,
            "start_steps": self.state.steps,
            "target": self.state.steps + requested,
            "collected_chars": 0,
            "started": time.time(),
            "message": "eğitim başladı",
        }

        def loop() -> None:
            from model import data_collector, persist

            target = self.job["target"]
            start = self.job["start_steps"]
            next_collect = start
            next_save = start + 1000
            try:
                while self.state.steps < target and not self._job_stop.is_set():
                    # her ~2000 adımda bir taze veri topla
                    if self.state.steps >= next_collect:
                        self.job["message"] = "veri toplanıyor (Hugging Face)…"
                        try:
                            text, next_off = data_collector.fetch_batch(self.state.hf_offset)
                            if text:
                                with self.lock:
                                    self.corpus = (self.corpus + "\n\n" + text)[-3_000_000:]
                                    self._rebuild_cache()
                                self.state.hf_offset = next_off
                                self.job["collected_chars"] += len(text)
                        except Exception:
                            pass
                        next_collect += 2000
                    p = (self.state.steps - start) / max(1, target - start)
                    lr = 0.02 * (0.2 ** p)
                    loss = self.train_steps(n=20, lr=lr)
                    self.job["message"] = f"eğitiliyor… loss={loss:.3f}"
                    # ara sıra kendi ürettiği kodla pekiştir
                    if self.state.steps % 500 < 20:
                        try:
                            self.self_train_once()
                        except Exception:
                            pass
                    if self.state.steps >= next_save:
                        self.save()
                        next_save += 1000
                self.save()
                uploaded = persist.upload_checkpoint(CHECKPOINT.parent)
                if self._job_stop.is_set():
                    self.job["message"] = "eğitim durduruldu"
                else:
                    self.job["message"] = (
                        "eğitim tamamlandı — model kalıcı olarak kaydedildi ✅"
                        if uploaded
                        else "eğitim tamamlandı (yerel kayıt)"
                    )
            except Exception as exc:
                self.job["message"] = f"eğitim hatası: {exc}"
            finally:
                self.job["active"] = False
                if was_autolearn or os.environ.get("DIMAI_AUTOLEARN", "1") == "1":
                    interval = float(os.environ.get("DIMAI_AUTOLEARN_INTERVAL", "3"))
                    if interval > 0:
                        self.start_autolearn(interval_sec=interval)

        self._job_thread = threading.Thread(target=loop, daemon=True, name="train-job")
        self._job_thread.start()
        return self.job_status()

    def stop_training_job(self) -> dict:
        self._job_stop.set()
        return self.job_status()


# singleton used by server
trainer = CodeTrainer()
