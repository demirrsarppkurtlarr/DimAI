#!/usr/bin/env python3
"""Build a compact hot chunk pack from curated seeds.

Usage:
  python data/build_kb_hot.py
  DIMAI_KB_PUSH=1 python data/build_kb_hot.py   # also upsert to Supabase

Creates data/kb_hot_chunks.json for faster boots (optional — server can
bootstrap directly from seed files too).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from model.kb_index import HOT_PATH, KnowledgeIndex  # noqa: E402


def main() -> int:
    idx = KnowledgeIndex()
    # Force rebuild from seeds (ignore existing hot pack during build)
    if HOT_PATH.exists():
        HOT_PATH.unlink()
    stats = idx.bootstrap(
        push_supabase=os.environ.get("DIMAI_KB_PUSH", "").lower() in {"1", "true", "yes"},
    )
    # Persist compact pack (no embeddings — re-encoded on boot)
    rows = []
    for ch in idx.chunks:
        rows.append({
            "chunk_id": ch.chunk_id,
            "kind": ch.kind,
            "q": ch.title,
            "a": ch.body,
            "c": ch.code,
            "l": ch.lang,
            "tags": ch.tags,
            "quality": ch.quality,
            "source": ch.source,
            "url": ch.url,
        })
    HOT_PATH.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {HOT_PATH} ({len(rows)} chunks) stats={stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
