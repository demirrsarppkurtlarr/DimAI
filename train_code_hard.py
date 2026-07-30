"""Aggressive code-focused training for DimAI.

Resumes the existing checkpoint, trains on the full HF Python corpus
(plus a curated high-quality pack), pushes toward TARGET_STEPS with
frequent self-training reinforcement, then restores the deploy corpus
and uploads the checkpoint to Supabase when configured.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

TARGET_STEPS = int(os.environ.get("DIMAI_CODE_TARGET", "500000"))
LR_START = 0.015
LR_END = 0.003
LOG_EVERY = 2_000
SAVE_EVERY = 5_000
SELF_EVERY = 1_000  # self-train burst every N steps


QUALITY_PACK = r'''
def fibonacci(n: int) -> list[int]:
    """Return the first n Fibonacci numbers."""
    if n <= 0:
        return []
    if n == 1:
        return [0]
    seq = [0, 1]
    while len(seq) < n:
        seq.append(seq[-1] + seq[-2])
    return seq


def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True


def bubble_sort(arr: list) -> list:
    a = list(arr)
    n = len(a)
    for i in range(n):
        for j in range(0, n - i - 1):
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
    return a


def binary_search(arr: list, target) -> int:
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        if arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


def merge_sort(arr: list) -> list:
    if len(arr) <= 1:
        return list(arr)
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return _merge(left, right)


def _merge(left: list, right: list) -> list:
    out = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            out.append(left[i]); i += 1
        else:
            out.append(right[j]); j += 1
    out.extend(left[i:]); out.extend(right[j:])
    return out


def quick_sort(arr: list) -> list:
    if len(arr) <= 1:
        return list(arr)
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    mid = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + mid + quick_sort(right)


class Stack:
    def __init__(self):
        self._data = []
    def push(self, item):
        self._data.append(item)
    def pop(self):
        return self._data.pop()
    def peek(self):
        return self._data[-1]
    def empty(self) -> bool:
        return not self._data


class Queue:
    def __init__(self):
        self._data = []
    def enqueue(self, item):
        self._data.append(item)
    def dequeue(self):
        return self._data.pop(0)
    def empty(self) -> bool:
        return not self._data


def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def count_words(text: str) -> dict:
    counts = {}
    for w in text.lower().split():
        counts[w] = counts.get(w, 0) + 1
    return counts


def flatten(nested: list) -> list:
    out = []
    for item in nested:
        if isinstance(item, list):
            out.extend(flatten(item))
        else:
            out.append(item)
    return out


def unique(items: list) -> list:
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def group_by(items: list, key_fn):
    groups = {}
    for item in items:
        k = key_fn(item)
        groups.setdefault(k, []).append(item)
    return groups


def retry(fn, times: int = 3, delay: float = 0.5):
    import time
    last = None
    for _ in range(times):
        try:
            return fn()
        except Exception as exc:
            last = exc
            time.sleep(delay)
    raise last


def http_get_json(url: str) -> dict:
    import json
    from urllib.request import urlopen
    with urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


class BankAccount:
    def __init__(self, owner: str, balance: float = 0.0):
        self.owner = owner
        self.balance = balance
    def deposit(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("amount must be positive")
        self.balance += amount
    def withdraw(self, amount: float) -> None:
        if amount > self.balance:
            raise ValueError("insufficient funds")
        self.balance -= amount


def guess_number_game() -> None:
    import random
    secret = random.randint(1, 100)
    while True:
        guess = int(input("Tahmin (1-100): "))
        if guess < secret:
            print("Daha büyük")
        elif guess > secret:
            print("Daha küçük")
        else:
            print("Bildin!")
            break


def password_generator(length: int = 12) -> str:
    import random
    import string
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "".join(random.choice(alphabet) for _ in range(length))


def factorial(n: int) -> int:
    if n < 0:
        raise ValueError("n must be >= 0")
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return abs(a)


def lcm(a: int, b: int) -> int:
    return abs(a * b) // gcd(a, b) if a and b else 0


def flatten_dict(d: dict, parent: str = "", sep: str = ".") -> dict:
    items = {}
    for k, v in d.items():
        key = f"{parent}{sep}{k}" if parent else str(k)
        if isinstance(v, dict):
            items.update(flatten_dict(v, key, sep=sep))
        else:
            items[key] = v
    return items


def chunked(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def deep_copy(obj):
    import copy
    return copy.deepcopy(obj)


def timer(fn):
    import time
    def wrapper(*args, **kwargs):
        t0 = time.time()
        result = fn(*args, **kwargs)
        print(f"{fn.__name__} took {time.time() - t0:.4f}s")
        return result
    return wrapper


@timer
def demo_sum(n: int = 100000):
    return sum(range(n))


def parse_csv_line(line: str) -> list[str]:
    return [part.strip() for part in line.split(",")]


def invert_dict(d: dict) -> dict:
    return {v: k for k, v in d.items()}


def most_common(items: list):
    from collections import Counter
    return Counter(items).most_common(1)[0]


def safe_divide(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        return None


def matrix_transpose(matrix: list[list]) -> list[list]:
    return [list(row) for row in zip(*matrix)]


def is_palindrome(s: str) -> bool:
    cleaned = "".join(ch.lower() for ch in s if ch.isalnum())
    return cleaned == cleaned[::-1]


def two_sum(nums: list[int], target: int) -> list[int]:
    seen = {}
    for i, n in enumerate(nums):
        need = target - n
        if need in seen:
            return [seen[need], i]
        seen[n] = i
    return []


def sliding_window_max(nums: list[int], k: int) -> list[int]:
    if k <= 0 or k > len(nums):
        return []
    return [max(nums[i:i + k]) for i in range(len(nums) - k + 1)]


def dfs(graph: dict, start):
    visited = set()
    stack = [start]
    order = []
    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        order.append(node)
        stack.extend(reversed(graph.get(node, [])))
    return order


def bfs(graph: dict, start):
    from collections import deque
    visited = {start}
    q = deque([start])
    order = []
    while q:
        node = q.popleft()
        order.append(node)
        for nb in graph.get(node, []):
            if nb not in visited:
                visited.add(nb)
                q.append(nb)
    return order


if __name__ == "__main__":
    print(fibonacci(10))
    print(is_prime(97))
    print(bubble_sort([3, 1, 4, 1, 5, 9]))
    print(binary_search([1, 2, 3, 4, 5], 4))
    print(password_generator(16))
    print(two_sum([2, 7, 11, 15], 9))
'''


def main() -> None:
    root = Path(__file__).resolve().parent
    big = (root / "data" / "train_corpus.txt").read_text(encoding="utf-8")
    # curated pack first so anchors hit clean functions often
    # Repeat quality pack to dominate early windows and wash bad habits
    pack_boost = (QUALITY_PACK + "\n\n") * 8
    boosted = (pack_boost + big)[:12_000_000]
    (root / "data" / "corpus.txt").write_text(boosted, encoding="utf-8")
    print(f"train corpus: {len(boosted):,} chars (quality pack x8 + HF)", flush=True)

    from model.trainer import CodeTrainer

    tr = CodeTrainer(hidden_size=160, seq_len=140)
    # longer sequences for better code structure
    tr.seq_len = 140
    # Seed replay with curated quality snippets so rejects still reinforce good code
    for block in QUALITY_PACK.split("\n\n"):
        block = block.strip()
        if block.startswith(("def ", "class ")) and CodeTrainer.is_valid_python(block):
            if block not in tr.replay:
                tr.replay.append(block)
    print(f"quality replay seeded: {len(tr.replay)} snippets", flush=True)

    # --- wash phase: overfit clean code to erase degenerate patterns ---
    wash_steps = int(os.environ.get("DIMAI_WASH_STEPS", "25000"))
    print(f"wash phase: {wash_steps:,} steps on quality-heavy corpus", flush=True)
    wash_start = tr.state.steps
    wash_target = wash_start + wash_steps
    t_wash = time.time()
    while tr.state.steps < wash_target:
        loss = tr.train_steps(n=100, lr=0.012)
        # reinforce replay snippets directly
        if tr.replay and tr.state.steps % 200 < 100:
            import random
            sample = random.choice(tr.replay)
            ids = tr.vocab.encode(sample) if tr.vocab else []
            if tr.model and len(ids) >= 2:
                for _ in range(3):
                    tr.model.train_sequence(ids[: min(len(ids), tr.seq_len + 1)], lr=0.01)
                    tr.state.steps += 1
        if tr.state.steps % 2000 < 100:
            rate = (tr.state.steps - wash_start) / max(time.time() - t_wash, 1e-9)
            print(
                f"[wash] steps={tr.state.steps:,} loss={loss:.3f} {rate:.0f} st/s",
                flush=True,
            )
            tr.save()
    tr.save()
    print("wash phase done — sample check:", flush=True)
    for prompt in ("def fibonacci", "def binary_", "class Stack", "def "):
        s = tr.generate(prompt, 160, 0.35)
        v = tr.longest_valid_prefix(s)
        print(f"  {prompt!r} valid={v is not None}")
        print("  ", (v or s)[:160].replace("\n", "\\n"), flush=True)

    start = tr.state.steps
    target = max(TARGET_STEPS, start + 50_000)
    print(f"resuming hard train {start:,} -> target {target:,}", flush=True)

    t0 = time.time()
    next_log = tr.state.steps + LOG_EVERY
    next_save = tr.state.steps + SAVE_EVERY
    next_self = tr.state.steps + SELF_EVERY
    loss = 0.0
    accepted_burst = 0

    while tr.state.steps < target:
        p = (tr.state.steps - start) / max(1, target - start)
        lr = LR_START * (LR_END / LR_START) ** p
        loss = tr.train_steps(n=100, lr=lr)

        if tr.state.steps >= next_self:
            ok = 0
            for _ in range(40):
                ok += int(tr.self_train_once()["ok"])
            accepted_burst = ok
            print(f"[self] accepted {ok}/40 at step {tr.state.steps:,}", flush=True)
            next_self += SELF_EVERY

        if tr.state.steps >= next_log:
            el = time.time() - t0
            rate = (tr.state.steps - start) / max(el, 1e-9)
            eta = (target - tr.state.steps) / max(rate, 1e-9)
            print(
                f"steps={tr.state.steps:7,d} lr={lr:.4f} loss={loss:.3f} "
                f"{rate:.0f} st/s eta={eta/60:.0f}min self_ok={accepted_burst}/40",
                flush=True,
            )
            next_log += LOG_EVERY

        if tr.state.steps >= next_save:
            tr.save()
            next_save += SAVE_EVERY

    # final reinforcement sweep
    ok = 0
    for _ in range(80):
        ok += int(tr.self_train_once()["ok"])
    print(f"final self-train {ok}/80", flush=True)
    tr.save()

    print(f"reached {tr.state.steps:,} steps in {(time.time()-t0)/60:.1f} min", flush=True)
    for prompt in ("def ", "def fibonacci", "def sort_", "class ", "def binary_"):
        for temp in (0.35, 0.5):
            s = tr.generate(prompt, 180, temp)
            v = tr.longest_valid_prefix(s)
            print(f"--- {prompt!r} temp={temp} valid={v is not None}")
            print((v or s)[:220], flush=True)

    # restore deploy corpus
    deploy = (root / "data" / "deploy_corpus.txt").read_text(encoding="utf-8")
    # keep quality pack in deploy corpus too for better online autolearn
    deploy_boosted = ((QUALITY_PACK + "\n\n") * 3 + deploy)[:2_000_000]
    (root / "data" / "corpus.txt").write_text(deploy_boosted, encoding="utf-8")
    (root / "data" / "deploy_corpus.txt").write_text(deploy_boosted, encoding="utf-8")
    print("deploy corpus restored (+ quality pack)", flush=True)

    try:
        from model import persist
        if persist.upload_checkpoint(root / "checkpoints"):
            print("checkpoint uploaded to Supabase", flush=True)
    except Exception as exc:
        print(f"upload skipped: {exc}", flush=True)

    print("DONE", flush=True)


if __name__ == "__main__":
    main()
