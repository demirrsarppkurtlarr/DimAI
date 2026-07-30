"""Local web server for the self-training code AI. No external AI APIs."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flask import Flask, jsonify, request, send_from_directory

from model.trainer import trainer

app = Flask(__name__, static_folder="static", static_url_path="/static")


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/status")
def status():
    return jsonify(trainer.state.to_dict())


@app.post("/api/bootstrap")
def bootstrap():
    data = request.get_json(silent=True) or {}
    steps = int(data.get("steps", 400))
    loss = trainer.bootstrap_train(steps=steps)
    return jsonify({"ok": True, "loss": loss, "state": trainer.state.to_dict()})


@app.post("/api/train")
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


@app.post("/api/self_train")
def self_train():
    result = trainer.self_train_once()
    return jsonify({"ok": True, "result": result, "state": trainer.state.to_dict()})


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


if __name__ == "__main__":
    # Initial light training if brand new
    if trainer.state.steps == 0:
        print("Bootstrap training (first run)...")
        trainer.bootstrap_train(steps=500)
        print("Starting continuous self-learning...")
        trainer.start_autolearn(interval_sec=2.0)
    else:
        print(f"Resuming from checkpoint at step {trainer.state.steps}")
        trainer.start_autolearn(interval_sec=2.0)

    print("Open http://127.0.0.1:5055")
    app.run(host="0.0.0.0", port=5055, debug=False, threaded=True)
