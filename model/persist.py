"""Persist model checkpoints to Supabase Storage.

Render's free tier has an ephemeral filesystem: anything trained at runtime
is lost on restart/deploy. After a training job finishes, the checkpoint is
uploaded to a Supabase Storage bucket; on boot, if the remote checkpoint has
more steps than the local one, it is restored.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import requests

SUPABASE_URL = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY") or ""
BUCKET = os.environ.get("DIMAI_BUCKET", "dimai-model")
TIMEOUT = 30

FILES = ("model.npz", "model.json", "trainer_state.json")


def configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY)


def _headers(extra: Optional[dict] = None) -> dict:
    h = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    if extra:
        h.update(extra)
    return h


def _ensure_bucket() -> None:
    r = requests.post(
        f"{SUPABASE_URL}/storage/v1/bucket",
        headers=_headers({"Content-Type": "application/json"}),
        json={"id": BUCKET, "name": BUCKET, "public": False},
        timeout=TIMEOUT,
    )
    # 200 = created, 400/409 = already exists
    if r.status_code not in (200, 400, 409):
        r.raise_for_status()


def upload_checkpoint(checkpoint_dir: Path) -> bool:
    """Upload all checkpoint files; returns True on success."""
    if not configured():
        return False
    try:
        _ensure_bucket()
        for name in FILES:
            path = checkpoint_dir / name
            if not path.exists():
                continue
            r = requests.post(
                f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{name}",
                headers=_headers({
                    "Content-Type": "application/octet-stream",
                    "x-upsert": "true",
                }),
                data=path.read_bytes(),
                timeout=120,
            )
            r.raise_for_status()
        return True
    except Exception as exc:
        print(f"[persist] upload failed: {exc}", flush=True)
        return False


def _remote_steps() -> int:
    r = requests.get(
        f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/trainer_state.json",
        headers=_headers(),
        timeout=TIMEOUT,
    )
    if r.status_code != 200:
        return -1
    return int(json.loads(r.text).get("steps", 0))


def restore_if_newer(checkpoint_dir: Path) -> bool:
    """Download the remote checkpoint when it has more steps than local."""
    if not configured():
        return False
    try:
        remote = _remote_steps()
        if remote < 0:
            return False
        local = 0
        state_path = checkpoint_dir / "trainer_state.json"
        if state_path.exists():
            local = int(json.loads(state_path.read_text()).get("steps", 0))
        if remote <= local:
            return False
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        for name in FILES:
            r = requests.get(
                f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{name}",
                headers=_headers(),
                timeout=120,
            )
            r.raise_for_status()
            (checkpoint_dir / name).write_bytes(r.content)
        print(f"[persist] restored remote checkpoint ({remote} steps > {local})", flush=True)
        return True
    except Exception as exc:
        print(f"[persist] restore failed: {exc}", flush=True)
        return False
