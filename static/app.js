async function api(path, body) {
  const res = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

const els = {
  prompt: document.getElementById("prompt"),
  temp: document.getElementById("temp"),
  output: document.getElementById("output"),
  badge: document.getElementById("valid-badge"),
  steps: document.getElementById("s-steps"),
  rounds: document.getElementById("s-rounds"),
  ok: document.getElementById("s-ok"),
  bad: document.getElementById("s-bad"),
  loss: document.getElementById("s-loss"),
  msg: document.getElementById("s-msg"),
  history: document.getElementById("history"),
  btnGen: document.getElementById("btn-generate"),
  btnTrain: document.getElementById("btn-train"),
  btnSelf: document.getElementById("btn-self"),
  btnAuto: document.getElementById("btn-auto"),
};

let autoOn = false;

function renderState(state) {
  if (!state) return;
  els.steps.textContent = state.steps;
  els.rounds.textContent = state.self_train_rounds;
  els.ok.textContent = state.accepted;
  els.bad.textContent = state.rejected;
  els.loss.textContent = Number.isFinite(state.last_loss) ? state.last_loss.toFixed(3) : "—";
  els.msg.textContent = state.message || "—";
  autoOn = !!state.running;
  els.btnAuto.textContent = autoOn ? "Sürekli öğren: KAPAT" : "Sürekli öğren: AÇ";
  els.btnAuto.classList.toggle("accent", !autoOn);

  els.history.innerHTML = "";
  (state.history || []).slice().reverse().forEach((h) => {
    const li = document.createElement("li");
    li.className = h.ok ? "ok" : "bad";
    li.textContent = `${h.ok ? "✓" : "✗"} [${h.prompt}] ${h.preview || ""}`;
    els.history.appendChild(li);
  });
}

async function refresh() {
  try {
    const state = await api("/api/status");
    renderState(state);
  } catch (_) {
    /* ignore transient errors while server trains */
  }
}

els.btnGen.addEventListener("click", async () => {
  els.btnGen.disabled = true;
  try {
    const data = await api("/api/generate", {
      prompt: els.prompt.value || "def ",
      temperature: Number(els.temp.value),
      n_chars: 200,
    });
    els.output.textContent = data.text;
    els.badge.textContent = data.valid_python ? "geçerli Python" : "geçersiz / yarım";
    els.badge.className = "badge " + (data.valid_python ? "ok" : "bad");
  } catch (err) {
    els.output.textContent = String(err);
  } finally {
    els.btnGen.disabled = false;
    refresh();
  }
});

els.btnTrain.addEventListener("click", async () => {
  els.btnTrain.disabled = true;
  try {
    const data = await api("/api/train", { steps: 50 });
    renderState(data.state);
  } finally {
    els.btnTrain.disabled = false;
  }
});

els.btnSelf.addEventListener("click", async () => {
  els.btnSelf.disabled = true;
  try {
    const data = await api("/api/self_train", {});
    if (data.result?.snippet) {
      els.output.textContent = data.result.snippet;
      els.badge.textContent = data.result.ok ? "kabul edildi" : "reddedildi";
      els.badge.className = "badge " + (data.result.ok ? "ok" : "bad");
    }
    renderState(data.state);
  } finally {
    els.btnSelf.disabled = false;
  }
});

els.btnAuto.addEventListener("click", async () => {
  els.btnAuto.disabled = true;
  try {
    if (autoOn) {
      const data = await api("/api/autolearn/stop", {});
      renderState(data.state);
    } else {
      const data = await api("/api/autolearn/start", { interval: 2 });
      renderState(data.state);
    }
  } finally {
    els.btnAuto.disabled = false;
  }
});

refresh();
setInterval(refresh, 2000);
