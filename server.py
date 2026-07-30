"""DimAI — web server for the self-training code AI. No external AI APIs."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flask import Flask, jsonify, request, send_from_directory

from model import web_research
from model.brain import brain
from model.improve import init_improve
from model.trainer import trainer
from model.web_research import learned

app = Flask(__name__, static_folder="static", static_url_path="/static")

# Self-improvement engine (retrieve → evaluate → reflect → queue → promote)
improve = init_improve(learned)

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
    payload["train_job"] = trainer.job_status()
    try:
        payload["improve"] = improve.status()
    except Exception:
        payload["improve"] = {}
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

    result = None

    # --- Knowledge Retrieval: güçlü geçmiş başarıyı önce dene ---
    try:
        prior = improve.retrieve(message)
        if prior and float(prior.get("overall") or 0) >= 0.72 and prior.get("from") == "episode":
            # episode match requires high overlap (see retrieve); reuse as answer
            if float(prior.get("match") or 0) >= 0.78:
                result = {
                    "reply": prior["reply"],
                    "source": "memory",
                    "url": prior.get("url", ""),
                    "thinking": "geçmiş başarılı çözümden",
                }
    except Exception:
        result = None

    if result is None:
        result = brain.reply(message, history=history[-10:])

    if result.get("source") == "fallback":
        query = result.pop("research_query", message)
        context_query = result.pop("context_query", None)
        queries = [query]
        if context_query and context_query.strip() and context_query.strip() != query.strip():
            queries.append(context_query)

        for q in queries:
            # 1) geçmiş başarı / learned (retrieval)
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
                }
                break

            hit = learned.lookup(q)
            if hit:
                result = {
                    "reply": f"{hit['a']}",
                    "source": "learned",
                    "url": hit.get("url", ""),
                    "thinking": result.get("thinking", ""),
                }
                break

            found = web_research.research_deep(q)
            if found:
                # Learning Queue: doğrudan memory'e yazma — after_chat doğrulayıp ekler
                result = {
                    "reply": found["answer"],
                    "source": "web",
                    "url": found.get("url", ""),
                    "provider": found.get("provider", ""),
                    "thinking": result.get("thinking", ""),
                }
                break
        else:
            if (result.get("thinking") or "").startswith("önceki konuya"):
                tip = (result.get("thinking") or "")
                konu = tip.split("«")[-1].split("»")[0] if "«" in tip else "bu konu"
                result["source"] = "chat"
                result["reply"] = (
                    f"**{konu}** hakkında sorduğunu anladım ama net bir sonuç "
                    f"çekemedim. Soruyu biraz açar mısın — ör. \"{konu} nasıl oluşur\" "
                    f"veya \"{konu} ne işe yarar\"?"
                )

    # Attach experimental neural output when requested or still unanswered
    if data.get("neural") or result.get("source") == "fallback":
        try:
            sample = trainer.generate(prompt="def ", n_chars=160, temperature=0.5)
            valid = trainer.longest_valid_prefix(sample)
            result["neural_sample"] = valid or sample[:200]
            result["neural_valid"] = valid is not None
        except Exception:
            pass

    # --- Self-improvement: evaluate → reflect → log → queue → promote ---
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
        trainer.bootstrap_train(steps=int(os.environ.get("DIMAI_BOOTSTRAP_STEPS", "200")))
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5055"))
    print(f"DimAI listening on http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
