"""Tiny character-level language model in NumPy — our own weights, no external AI APIs."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np


def softmax(x: np.ndarray) -> np.ndarray:
    x = x - np.max(x, axis=-1, keepdims=True)
    e = np.exp(x)
    return e / np.sum(e, axis=-1, keepdims=True)


@dataclass
class Vocab:
    chars: List[str]
    stoi: Dict[str, int]
    itos: Dict[int, str]

    @classmethod
    def from_text(cls, text: str) -> "Vocab":
        chars = sorted(set(text))
        stoi = {c: i for i, c in enumerate(chars)}
        itos = {i: c for c, i in stoi.items()}
        return cls(chars=chars, stoi=stoi, itos=itos)

    @property
    def size(self) -> int:
        return len(self.chars)

    def encode(self, text: str) -> List[int]:
        return [self.stoi[c] for c in text if c in self.stoi]

    def decode(self, ids: List[int]) -> str:
        return "".join(self.itos[i] for i in ids)

    def to_dict(self) -> dict:
        return {"chars": self.chars}

    @classmethod
    def from_dict(cls, data: dict) -> "Vocab":
        chars = list(data["chars"])
        stoi = {c: i for i, c in enumerate(chars)}
        itos = {i: c for c, i in stoi.items()}
        return cls(chars=chars, stoi=stoi, itos=itos)


class CharRNN:
    """Single-layer GRU character language model."""

    def __init__(self, vocab_size: int, hidden_size: int = 128, seed: int = 42):
        rng = np.random.default_rng(seed)
        scale = 0.08
        self.vocab_size = vocab_size
        self.hidden_size = hidden_size

        # GRU gates: update z, reset r, candidate h
        self.Wz = rng.normal(0, scale, (vocab_size, hidden_size))
        self.Uz = rng.normal(0, scale, (hidden_size, hidden_size))
        self.bz = np.zeros((hidden_size,))

        self.Wr = rng.normal(0, scale, (vocab_size, hidden_size))
        self.Ur = rng.normal(0, scale, (hidden_size, hidden_size))
        self.br = np.zeros((hidden_size,))

        self.Wh = rng.normal(0, scale, (vocab_size, hidden_size))
        self.Uh = rng.normal(0, scale, (hidden_size, hidden_size))
        self.bh = np.zeros((hidden_size,))

        self.Wy = rng.normal(0, scale, (hidden_size, vocab_size))
        self.by = np.zeros((vocab_size,))

    def params(self) -> List[np.ndarray]:
        return [
            self.Wz, self.Uz, self.bz,
            self.Wr, self.Ur, self.br,
            self.Wh, self.Uh, self.bh,
            self.Wy, self.by,
        ]

    def zero_grads(self) -> List[np.ndarray]:
        return [np.zeros_like(p) for p in self.params()]

    def forward(self, inputs: List[int], h_prev: Optional[np.ndarray] = None):
        if h_prev is None:
            h_prev = np.zeros((self.hidden_size,))

        xs, zs, rs, h_tildes, hs, ys, ps = {}, {}, {}, {}, {}, {}, {}
        hs[-1] = np.array(h_prev, dtype=np.float64)

        loss = 0.0
        for t, idx in enumerate(inputs[:-1]):
            target = inputs[t + 1]
            x = np.zeros((self.vocab_size,))
            x[idx] = 1.0
            xs[t] = x

            z = 1.0 / (1.0 + np.exp(-(x @ self.Wz + hs[t - 1] @ self.Uz + self.bz)))
            r = 1.0 / (1.0 + np.exp(-(x @ self.Wr + hs[t - 1] @ self.Ur + self.br)))
            h_tilde = np.tanh(x @ self.Wh + (r * hs[t - 1]) @ self.Uh + self.bh)
            h = (1.0 - z) * hs[t - 1] + z * h_tilde
            y = h @ self.Wy + self.by
            p = softmax(y)

            zs[t], rs[t], h_tildes[t], hs[t], ys[t], ps[t] = z, r, h_tilde, h, y, p
            loss += -np.log(max(p[target], 1e-12))

        cache = (xs, zs, rs, h_tildes, hs, inputs)
        return loss, hs[len(inputs) - 2], cache, ps

    def backward(self, cache, ps) -> Tuple[List[np.ndarray], float]:
        xs, zs, rs, h_tildes, hs, inputs = cache
        grads = self.zero_grads()
        dWz, dUz, dbz, dWr, dUr, dbr, dWh, dUh, dbh, dWy, dby = grads

        dh_next = np.zeros((self.hidden_size,))
        n = max(len(inputs) - 1, 1)

        for t in reversed(range(len(inputs) - 1)):
            target = inputs[t + 1]
            dy = ps[t].copy()
            dy[target] -= 1.0

            dWy += np.outer(hs[t], dy)
            dby += dy
            dh = dy @ self.Wy.T + dh_next

            z = zs[t]
            r = rs[t]
            h_prev = hs[t - 1]
            h_tilde = h_tildes[t]
            x = xs[t]

            dz = dh * (h_tilde - h_prev)
            dh_tilde = dh * z
            dh_prev = dh * (1.0 - z)

            dt = dh_tilde * (1.0 - h_tilde ** 2)
            dWh += np.outer(x, dt)
            dUh += np.outer(r * h_prev, dt)
            dbh += dt
            dr_h = (dt @ self.Uh.T)
            dh_prev += r * dr_h
            dr = h_prev * dr_h

            # sigmoid grads
            dz_raw = dz * z * (1.0 - z)
            dr_raw = dr * r * (1.0 - r)

            dWz += np.outer(x, dz_raw)
            dUz += np.outer(h_prev, dz_raw)
            dbz += dz_raw
            dh_prev += dz_raw @ self.Uz.T

            dWr += np.outer(x, dr_raw)
            dUr += np.outer(h_prev, dr_raw)
            dbr += dr_raw
            dh_prev += dr_raw @ self.Ur.T

            dh_next = dh_prev

        # clip
        clipped = []
        total_norm = 0.0
        for g in grads:
            total_norm += float(np.sum(g * g))
        total_norm = np.sqrt(total_norm) + 1e-8
        clip = 5.0
        scale = clip / total_norm if total_norm > clip else 1.0
        for g in grads:
            clipped.append(g * scale)
        return clipped, total_norm

    def apply_grads(self, grads: List[np.ndarray], lr: float) -> None:
        for p, g in zip(self.params(), grads):
            p -= lr * g

    def train_sequence(self, inputs: List[int], lr: float = 0.05) -> float:
        if len(inputs) < 2:
            return 0.0
        loss, _, cache, ps = self.forward(inputs)
        grads, _ = self.backward(cache, ps)
        self.apply_grads(grads, lr)
        return float(loss / max(len(inputs) - 1, 1))

    def sample(
        self,
        seed_ids: List[int],
        n_chars: int,
        temperature: float = 0.8,
        rng: Optional[np.random.Generator] = None,
    ) -> List[int]:
        if rng is None:
            rng = np.random.default_rng()
        h = np.zeros((self.hidden_size,))
        # warm up
        for idx in seed_ids[:-1]:
            x = np.zeros((self.vocab_size,))
            x[idx] = 1.0
            z = 1.0 / (1.0 + np.exp(-(x @ self.Wz + h @ self.Uz + self.bz)))
            r = 1.0 / (1.0 + np.exp(-(x @ self.Wr + h @ self.Ur + self.br)))
            h_tilde = np.tanh(x @ self.Wh + (r * h) @ self.Uh + self.bh)
            h = (1.0 - z) * h + z * h_tilde

        idx = seed_ids[-1] if seed_ids else 0
        out = list(seed_ids)
        for _ in range(n_chars):
            x = np.zeros((self.vocab_size,))
            x[idx] = 1.0
            z = 1.0 / (1.0 + np.exp(-(x @ self.Wz + h @ self.Uz + self.bz)))
            r = 1.0 / (1.0 + np.exp(-(x @ self.Wr + h @ self.Ur + self.br)))
            h_tilde = np.tanh(x @ self.Wh + (r * h) @ self.Uh + self.bh)
            h = (1.0 - z) * h + z * h_tilde
            logits = (h @ self.Wy + self.by) / max(temperature, 1e-3)
            probs = softmax(logits)
            idx = int(rng.choice(self.vocab_size, p=probs))
            out.append(idx)
        return out

    def save(self, path: Path, vocab: Vocab, meta: Optional[dict] = None) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path,
            Wz=self.Wz, Uz=self.Uz, bz=self.bz,
            Wr=self.Wr, Ur=self.Ur, br=self.br,
            Wh=self.Wh, Uh=self.Uh, bh=self.bh,
            Wy=self.Wy, by=self.by,
            vocab_size=self.vocab_size,
            hidden_size=self.hidden_size,
        )
        meta_path = path.with_suffix(".json")
        payload = {"vocab": vocab.to_dict(), "meta": meta or {}}
        meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Tuple["CharRNN", Vocab, dict]:
        path = Path(path)
        data = np.load(path)
        model = cls(int(data["vocab_size"]), int(data["hidden_size"]))
        model.Wz, model.Uz, model.bz = data["Wz"], data["Uz"], data["bz"]
        model.Wr, model.Ur, model.br = data["Wr"], data["Ur"], data["br"]
        model.Wh, model.Uh, model.bh = data["Wh"], data["Uh"], data["bh"]
        model.Wy, model.by = data["Wy"], data["by"]
        meta_path = path.with_suffix(".json")
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
        vocab = Vocab.from_dict(payload["vocab"])
        return model, vocab, payload.get("meta", {})
