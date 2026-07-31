"""DimAI — web server for the self-training code AI. No external AI APIs."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flask import Flask, jsonify, request, send_from_directory

from model import web_research
from model.improve import init_improve
from model.trainer import trainer
from model.web_research import learned

app = Flask(__name__, static_folder="static", static_url_path="/static")

# Self-improvement engine (retrieve → evaluate → reflect → queue → promote)
improve = init_improve(learned)

# Knowledge index: hybrid top-k over all curated seeds (+ Supabase cold tier)
from model.kb_index import knowledge_index

try:
    _kb_stats = knowledge_index.bootstrap(
        push_supabase=os.environ.get("DIMAI_KB_PUSH", "").lower() in {"1", "true", "yes"},
    )
    print(
        f"[DimAI] kb_index ready: {_kb_stats.get('chunks', 0)} chunks "
        f"backend={knowledge_index.backend} boot={_kb_stats.get('boot_sec')}s",
        flush=True,
    )
except Exception as _exc:
    print(f"[DimAI] kb_index bootstrap skipped: {_exc}", flush=True)

# Legacy learned store seeds (smaller caps — primary retrieval is kb_index)
_TULU_SEED = ROOT / "data" / "tulu_learned_seed.json"
try:
    _seeded = learned.seed_from_file(_TULU_SEED, limit=800)
    if _seeded:
        print(f"[DimAI] seeded {_seeded} Tulu Q&A into learned store", flush=True)
except Exception as _exc:
    print(f"[DimAI] tulu seed skipped: {_exc}", flush=True)

# Hugging Face coding instruction seed (data/ingest_code_instruct.py)
_CODE_SEED = ROOT / "data" / "code_learned_seed.json"
try:
    _code_seeded = learned.seed_from_file(_CODE_SEED, limit=1200)
    if _code_seeded:
        print(f"[DimAI] seeded {_code_seeded} HF code-instruct pairs into learned store", flush=True)
except Exception as _exc:
    print(f"[DimAI] code seed skipped: {_exc}", flush=True)

# Turkish-heavy chat + code seeds — backup path for learned.lookup
_TR_CHAT_SEED = ROOT / "data" / "tr_chat_learned_seed.json"
_TR_CODE_SEED = ROOT / "data" / "tr_code_learned_seed.json"
try:
    _tr_chat = learned.seed_from_file(_TR_CHAT_SEED, limit=2000)
    if _tr_chat:
        print(f"[DimAI] seeded {_tr_chat} Turkish chat/instruct pairs into learned store", flush=True)
except Exception as _exc:
    print(f"[DimAI] TR chat seed skipped: {_exc}", flush=True)
try:
    _tr_code = learned.seed_from_file(_TR_CODE_SEED, limit=1200)
    if _tr_code:
        print(f"[DimAI] seeded {_tr_code} Turkish code-instruct pairs into learned store", flush=True)
except Exception as _exc:
    print(f"[DimAI] TR code seed skipped: {_exc}", flush=True)

# Mega code seed (data/ingest_mega_code.py) — 7 fresh HF coding datasets
_MEGA_SEED = ROOT / "data" / "mega_code_seed.json"
try:
    _mega = learned.seed_from_file(_MEGA_SEED, limit=1500)
    if _mega:
        print(f"[DimAI] seeded {_mega} mega-code pairs into learned store", flush=True)
except Exception as _exc:
    print(f"[DimAI] mega code seed skipped: {_exc}", flush=True)

# Huge-scale HF slices — backup only; full set lives in kb_index
_HUGE_SEED = ROOT / "data" / "huge_learned_seed.json"
try:
    _huge = learned.seed_from_file(_HUGE_SEED, limit=2000)
    if _huge:
        print(f"[DimAI] seeded {_huge} huge-HF pairs into learned store", flush=True)
except Exception as _exc:
    print(f"[DimAI] huge seed skipped: {_exc}", flush=True)


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "app": "DimAI"})


@app.get("/api/status")
def status():
    payload = trainer.state.to_dict()
    payload["learned_count"] = learned.count()
    payload["learned_backend"] = learned.backend
    payload["kb_index_count"] = knowledge_index.count()
    payload["kb_index_backend"] = knowledge_index.backend
    payload["kb_index_vectors"] = knowledge_index.stats.get("vectors")
    payload["train_job"] = trainer.job_status()
    payload["nlu"] = {
        "pipeline": "stages-1-10",
        "provider": "local-template",
        "phase": "coding-params-v15",
        "codegen": "first-principles+40-domains",
        "rag": "kb+topk-hybrid+learned+supabase-cold",
        "tool_policy": "auto",
        "hf_code_seed": True,
        "mega_code_seed": True,
        "tr_chat_seed": True,
        "tr_code_seed": True,
        "huge_seed": True,
        "kb_index": True,
        "response_quality": True,
        "perf": "tool-shortcircuit+cache+index",
        "self_improve": "codegen-promote+backlog-drain",
    }
    try:
        payload["improve"] = improve.status()
    except Exception:
        payload["improve"] = {}
    # Huge HF integration summary (if present)
    try:
        import json as _json
        man = ROOT / "data" / "huge_manifest.json"
        if man.exists():
            m = _json.loads(man.read_text(encoding="utf-8"))
            payload["huge_datasets"] = {
                "integrated": m.get("datasets_integrated"),
                "registered": m.get("datasets_registered"),
                "estimated_source_tokens_sum": m.get("estimated_source_tokens_sum"),
                "slice_chars_sum": m.get("slice_chars_sum"),
                "combined_seed": m.get("combined_seed"),
            }
        elif (ROOT / "data" / "huge_learned_seed.json").exists():
            payload["huge_datasets"] = {"combined_seed_file": True}
    except Exception:
        pass
    return jsonify(payload)


@app.post("/api/bootstrap")
def bootstrap():
    data = request.get_json(silent=True) or {}
    steps = int(data.get("steps", 400))
    loss = trainer.bootstrap_train(steps=steps)
    return jsonify({"ok": True, "loss": loss, "state": trainer.state.to_dict()})


@app.post("/api/train_sync")
def train():
    data = request.get_json(silent=True) or {}
    n = int(data.get("steps", 50))
    loss = trainer.train_steps(n=n)
    trainer.save()
    return jsonify({"ok": True, "loss": loss, "state": trainer.state.to_dict()})


@app.post("/api/generate")
def generate():
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "def ")
    n_chars = int(data.get("n_chars", 180))
    temperature = float(data.get("temperature", 0.7))
    text = trainer.generate(prompt=prompt, n_chars=n_chars, temperature=temperature)
    valid = trainer.longest_valid_prefix(text)
    return jsonify({
        "ok": True,
        "text": text,
        "valid_python": valid is not None,
        "valid_prefix": valid,
    })


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", ""))[:2000]
    history = data.get("history") or []
    if not isinstance(history, list):
        history = []

    # Easter eggs before any NLU/agent path
    try:
        from model import skills as _skills

        if _skills.looks_like_special_code(message):
            ans = _skills.answer_special_code(message)
            if ans:
                return jsonify({
                    "ok": True,
                    "reply": ans,
                    "source": "chat",
                    "intent": "conversation",
                    "thinking": "easter-egg",
                    "learned_count": learned.count(),
                })
    except Exception:
        pass

    # ---- Modern NLU reasoning pipeline (stages 1→10) ----
    result = None
    try:
        from model.nlu import nlu_pipeline

        result = nlu_pipeline.run(message, history[-24:])
    except Exception as nlu_err:
        result = {
            "reply": "Anlamlandırma sırasında bir sorun oldu; farklı şekilde dener misin?",
            "source": "chat",
            "allow_web": False,
            "thinking": f"nlu-error: {type(nlu_err).__name__}",
        }

    # Legacy agent only when NLU fell back / needs web-policy help
    decision = None
    if result is None or result.get("source") in {"fallback", None} or result.get("allow_web"):
        try:
            from model.agent import agent as _agent
            decision = _agent.decide(message, history[-16:])
        except Exception:
            decision = None
    else:
        decision = None

    # Markdown ``` kodunu ayrı alana çıkar — UI kod bloğu göstersin
    if result and not result.get("code"):
        reply = result.get("reply") or ""
        fence = re.search(r"```(\w+)?\s*\n(.*?)```", reply, re.S)
        if fence:
            lang = fence.group(1) or "python"
            code = fence.group(2).strip()
            clean = re.sub(r"```\w*\s*\n.*?```", "", reply, count=1, flags=re.S).strip()
            result["reply"] = clean or "İşte kod:"
            result["code"] = code
            result["lang"] = result.get("lang") or lang

    # Web: NLU planledi veya legacy fallback
    allow_web = bool(result.get("allow_web"))
    if result.get("source") == "fallback":
        allow_web = True
    if decision is not None and result.get("source") == "fallback":
        allow_web = bool(decision.allow_web) or allow_web

    if result.get("source") == "fallback" and allow_web:
        query = result.pop("research_query", message)
        context_query = result.pop("context_query", None)
        queries = [query]
        if context_query and context_query.strip() and context_query.strip() != query.strip():
            queries.append(context_query)

        for q in queries:
            try:
                prior = improve.retrieve(q)
            except Exception:
                prior = None
            if prior and float(prior.get("overall") or 0) >= 0.65:
                result = {
                    "reply": prior["reply"],
                    "source": prior.get("source") or "memory",
                    "url": prior.get("url", ""),
                    "thinking": result.get("thinking", "") or "geçmiş çözüm",
                    "intent": result.get("intent"),
                    "nlu": result.get("nlu"),
                }
                break

            hit = learned.lookup(q)
            if hit:
                result = {
                    "reply": f"{hit['a']}",
                    "source": "learned",
                    "url": hit.get("url", ""),
                    "thinking": result.get("thinking", ""),
                    "intent": result.get("intent"),
                    "nlu": result.get("nlu"),
                }
                break

            found = web_research.research_deep(q)
            if found:
                result = {
                    "reply": found["answer"],
                    "source": "web",
                    "url": found.get("url", ""),
                    "provider": found.get("provider", ""),
                    "thinking": result.get("thinking", ""),
                    "intent": result.get("intent"),
                    "nlu": result.get("nlu"),
                }
                break
        else:
            result["source"] = "chat"
            if not result.get("reply") or "araştırayım" in (result.get("reply") or "").lower():
                result["reply"] = (
                    "Bunu netleştiremedim. Soruyu bir cümleyle açar mısın, "
                    "ya da doğrudan `todo yaz` / `React nedir` gibi dene."
                )
    elif result.get("source") == "fallback" and not allow_web:
        result["source"] = "chat"
        if not result.get("reply") or "araştırayım" in (result.get("reply") or "").lower():
            result["reply"] = (
                "Bunu web'e çıkmadan yanıtlayamadım. "
                "Daha somut sor veya \"karadelik nedir\" / \"todo yaz\" dene."
            )

    # Neural sadece açıkça istenirse
    if data.get("neural"):
        try:
            sample = trainer.generate(prompt="def ", n_chars=160, temperature=0.5)
            valid = trainer.longest_valid_prefix(sample)
            result["neural_sample"] = valid or sample[:200]
            result["neural_valid"] = valid is not None
        except Exception:
            pass

    try:
        enrichment = improve.after_chat(message, result)
        result.update(enrichment)
    except Exception as exc:
        result["improve_error"] = str(exc)[:200]

    result["learned_count"] = learned.count()
    return jsonify({"ok": True, **result})


@app.get("/api/improve/status")
def improve_status():
    return jsonify({"ok": True, **improve.status()})


@app.post("/api/improve/process")
def improve_process():
    """Manually drain the learning queue (also runs automatically after chat)."""
    data = request.get_json(silent=True) or {}
    n = int(data.get("limit", 20))
    return jsonify({"ok": True, **improve.process_queue(limit=n)})


@app.post("/api/self_train")
def self_train():
    result = trainer.self_train_once()
    return jsonify({"ok": True, "result": result, "state": trainer.state.to_dict()})


def _keepalive_while_training() -> None:
    """Render free tier 15 dk isteksiz kalınca uyur; eğitim boyunca uyandık kal."""
    import threading
    import time as _t

    import requests as _rq

    url = os.environ.get("RENDER_EXTERNAL_URL", "")
    if not url:
        return

    def ping() -> None:
        while trainer.job.get("active"):
            _t.sleep(240)
            try:
                _rq.get(f"{url}/api/health", timeout=10)
            except Exception:
                pass

    threading.Thread(target=ping, daemon=True, name="keepalive").start()


@app.get("/api/debug/threads")
def debug_threads():
    import sys
    import threading as th
    import traceback

    names = {t.ident: t.name for t in th.enumerate()}
    out = {}
    for tid, frame in sys._current_frames().items():
        out[names.get(tid, str(tid))] = traceback.format_stack(frame)[-5:]
    return jsonify(out)


@app.post("/api/train")
def train_start():
    data = request.get_json(silent=True) or {}
    steps = int(data.get("steps", 1000))
    job = trainer.start_training_job(steps)
    _keepalive_while_training()
    return jsonify({"ok": True, "job": job})


@app.post("/api/train/stop")
def train_stop():
    return jsonify({"ok": True, "job": trainer.stop_training_job()})


@app.post("/api/autolearn/start")
def autolearn_start():
    data = request.get_json(silent=True) or {}
    interval = float(data.get("interval", 1.5))
    trainer.start_autolearn(interval_sec=interval)
    return jsonify({"ok": True, "state": trainer.state.to_dict()})


@app.post("/api/autolearn/stop")
def autolearn_stop():
    trainer.stop_autolearn()
    return jsonify({"ok": True, "state": trainer.state.to_dict()})


@app.post("/api/save")
def save():
    trainer.save()
    return jsonify({"ok": True})


def _startup() -> None:
    """Warm model for gunicorn / Render cold starts.

    ÖNEMLİ: Burada thread BAŞLATILMAZ. gunicorn fork ettiğinde master'da
    başlayan thread'ler worker'a geçmez ama kilit kilitli kopyalanabilir
    (kalıcı deadlock). Thread'ler ilk istekte, worker içinde başlar.
    """
    if trainer.state.steps == 0:
        print("DimAI: bootstrap training (first run)...")
        trainer.bootstrap_train(steps=int(os.environ.get("DIMAI_BOOTSTRAP_STEPS", "1200")))
    else:
        print(f"DimAI: checkpoint loaded at step {trainer.state.steps}")
    trainer.state.running = False


_startup()

_worker_ready = False


@app.before_request
def _ensure_worker_threads() -> None:
    """İlk istekte (worker sürecinde) kilidi tazele ve autolearn'ü başlat."""
    global _worker_ready
    if _worker_ready:
        return
    _worker_ready = True
    trainer.reset_lock()
    print("[worker] fresh lock; starting autolearn in worker process", flush=True)
    if os.environ.get("DIMAI_AUTOLEARN", "1") == "1":
        interval = float(os.environ.get("DIMAI_AUTOLEARN_INTERVAL", "3"))
        if interval > 0:
            trainer.start_autolearn(interval_sec=interval)
    # Deep training: automatically continue toward a step target in the
    # background (keepalive pings prevent Render free-tier sleep).
    try:
        auto_target = int(os.environ.get("DIMAI_AUTO_TRAIN_TARGET", "60000"))
        if auto_target > 0 and trainer.state.steps < auto_target and not trainer.job.get("active"):
            remaining = auto_target - trainer.state.steps
            job = trainer.start_training_job(remaining)
            _keepalive_while_training()
            print(f"[worker] auto training job → target {auto_target} ({remaining} steps): {job}", flush=True)
    except Exception as exc:
        print(f"[worker] auto train skipped: {exc}", flush=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5055"))
    print(f"DimAI listening on http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
