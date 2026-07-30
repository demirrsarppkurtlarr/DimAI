const $ = (id) => document.getElementById(id);

const els = {
  prompt: $("prompt"),
  temp: $("temp"),
  tempVal: $("temp-val"),
  output: $("output"),
  badge: $("valid-badge"),
  steps: $("s-steps"),
  rounds: $("s-rounds"),
  ok: $("s-ok"),
  bad: $("s-bad"),
  loss: $("s-loss"),
  lossFill: $("loss-fill"),
  msg: $("s-msg"),
  history: $("history"),
  btnGen: $("btn-generate"),
  btnTrain: $("btn-train"),
  btnSelf: $("btn-self"),
  btnAuto: $("btn-auto"),
  liveDot: $("live-dot"),
  liveLabel: $("live-label"),
};

let autoOn = false;
let lastValues = {};

async function api(path, body) {
  const res = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

/* ---- helpers ---- */

function setNum(el, key, value) {
  const text = String(value);
  if (lastValues[key] !== text) {
    lastValues[key] = text;
    el.textContent = text;
    el.classList.remove("bump");
    void el.offsetWidth;
    el.classList.add("bump");
  }
}

function setBadge(state, text) {
  els.badge.className = `pill ${state}`;
  els.badge.textContent = text;
}

function typeCode(text) {
  els.output.classList.add("swapping");
  setTimeout(() => {
    els.output.textContent = "";
    els.output.classList.remove("swapping");
    let i = 0;
    const step = Math.max(2, Math.floor(text.length / 90));
    const tick = () => {
      i = Math.min(text.length, i + step);
      els.output.textContent = text.slice(0, i);
      if (i < text.length) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, 180);
}

function withLoading(btn, fn) {
  return async (...args) => {
    btn.disabled = true;
    btn.classList.add("loading");
    try {
      await fn(...args);
    } catch (err) {
      console.error(err);
    } finally {
      btn.disabled = false;
      btn.classList.remove("loading");
    }
  };
}

/* ---- state rendering ---- */

function renderState(state) {
  if (!state) return;
  setNum(els.steps, "steps", state.steps);
  setNum(els.rounds, "rounds", state.self_train_rounds);
  setNum(els.ok, "ok", state.accepted);
  setNum(els.bad, "bad", state.rejected);

  const loss = Number(state.last_loss) || 0;
  setNum(els.loss, "loss", loss ? loss.toFixed(3) : "—");
  els.lossFill.style.width = `${Math.min(100, (loss / 3) * 100)}%`;

  els.msg.textContent = state.message || "—";

  autoOn = !!state.running;
  els.btnAuto.classList.toggle("on", autoOn);
  els.btnAuto.textContent = autoOn ? "Sürekli öğrenme · açık" : "Sürekli öğrenme";

  renderHistory(state.history || []);
}

let lastHistoryKey = "";

function renderHistory(items) {
  const recent = items.slice(-14).reverse();
  const key = JSON.stringify(recent.map((h) => [h.t, h.ok]));
  if (key === lastHistoryKey) return;
  lastHistoryKey = key;

  els.history.innerHTML = "";
  if (!recent.length) {
    const li = document.createElement("li");
    li.className = "h-empty";
    li.textContent = "Henüz öğrenme kaydı yok";
    els.history.appendChild(li);
    return;
  }
  for (const h of recent) {
    const li = document.createElement("li");
    const icon = document.createElement("span");
    icon.className = `h-icon ${h.ok ? "ok" : "bad"}`;
    icon.textContent = h.ok ? "✓" : "✕";
    const text = document.createElement("span");
    text.className = "h-text";
    text.textContent = `${h.prompt || ""}  ${h.preview || ""}`.trim();
    li.append(icon, text);
    els.history.appendChild(li);
  }
}

function setLive(on) {
  els.liveDot.className = `dot ${on ? "on" : "off"}`;
  els.liveLabel.textContent = on ? (autoOn ? "öğreniyor" : "çevrimiçi") : "çevrimdışı";
}

async function refresh() {
  try {
    const state = await api("/api/status");
    renderState(state);
    setLive(true);
  } catch {
    setLive(false);
  }
}

/* ---- events ---- */

els.temp.addEventListener("input", () => {
  els.tempVal.textContent = Number(els.temp.value).toFixed(2);
  const pct = ((els.temp.value - 0.2) / 1.2) * 100;
  els.temp.style.setProperty("--fill", `${pct}%`);
});
els.temp.dispatchEvent(new Event("input"));

els.btnGen.addEventListener(
  "click",
  withLoading(els.btnGen, async () => {
    setBadge("neutral", "üretiliyor…");
    const data = await api("/api/generate", {
      prompt: els.prompt.value || "def ",
      temperature: Number(els.temp.value),
      n_chars: 220,
    });
    typeCode(data.valid_prefix || data.text);
    if (data.valid_python) setBadge("ok", "geçerli Python");
    else setBadge("bad", "geçersiz — model hâlâ öğreniyor");
    refresh();
  })
);

els.btnSelf.addEventListener(
  "click",
  withLoading(els.btnSelf, async () => {
    const data = await api("/api/self_train", {});
    if (data.result?.snippet) {
      typeCode(data.result.snippet);
      if (data.result.ok) setBadge("ok", "kabul edildi · corpus'a eklendi");
      else setBadge("bad", "reddedildi · tekrar deneniyor");
    }
    renderState(data.state);
  })
);

els.btnTrain.addEventListener(
  "click",
  withLoading(els.btnTrain, async () => {
    const data = await api("/api/train", { steps: 50 });
    renderState(data.state);
  })
);

els.btnAuto.addEventListener(
  "click",
  withLoading(els.btnAuto, async () => {
    const data = autoOn
      ? await api("/api/autolearn/stop", {})
      : await api("/api/autolearn/start", { interval: 3 });
    renderState(data.state);
  })
);

els.prompt.addEventListener("keydown", (e) => {
  if (e.key === "Enter") els.btnGen.click();
});

refresh();
setInterval(refresh, 2500);
