const $ = (id) => document.getElementById(id);

const els = {
  messages: $("messages"),
  welcome: $("welcome"),
  input: $("input"),
  composer: $("composer"),
  send: $("btn-send"),
  chips: $("chips"),
  welcomeChips: $("welcome-chips"),
  btnNew: $("btn-new"),
  btnAuto: $("btn-auto"),
  steps: $("s-steps"),
  ok: $("s-ok"),
  loss: $("s-loss"),
  liveDot: $("live-dot"),
  liveLabel: $("live-label"),
};

/* Mobil klavye: görünen viewport yüksekliğini sabitle — zoom/kayma azaltır */
function syncAppHeight() {
  const vv = window.visualViewport;
  const h = Math.round(vv && vv.height ? vv.height : window.innerHeight);
  document.documentElement.style.setProperty("--app-height", `${h}px`);
  // iOS klavye açılınca sayfa offset'ini sıfırla
  if (vv && Math.abs(vv.offsetTop) > 0) {
    window.scrollTo(0, 0);
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
  }
}
syncAppHeight();
window.addEventListener("resize", syncAppHeight);
window.visualViewport?.addEventListener("resize", syncAppHeight);
window.visualViewport?.addEventListener("scroll", syncAppHeight);
window.addEventListener("orientationchange", () => setTimeout(syncAppHeight, 150));

const SUGGESTIONS = [
  "print komutu nasıl kullanılır?",
  "sayı tahmin oyunu yaz",
  "fibonacci kodu yaz",
  "dosya nasıl okunur?",
  "listeyi nasıl sıralarım?",
  "class örneği göster",
  "flask web uygulaması yaz",
  "şifre üretici yaz",
  "ne yapabilirsin?",
];

let autoOn = false;
let busy = false;
let chatHistory = [];  // {role: "user"|"ai", content}

async function api(path, body) {
  const res = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

/* ---------- message rendering ---------- */

function scrollBottom() {
  els.messages.scrollTo({ top: els.messages.scrollHeight, behavior: "smooth" });
}

function hideWelcome() {
  if (els.welcome) {
    els.welcome.remove();
    els.welcome = null;
  }
}

function addUserMsg(text) {
  hideWelcome();
  const msg = document.createElement("div");
  msg.className = "msg user";
  msg.innerHTML = `<div class="avatar me">S</div>`;
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  msg.appendChild(bubble);
  els.messages.appendChild(msg);
  scrollBottom();
}

function addTyping(label) {
  hideWelcome();
  const msg = document.createElement("div");
  msg.className = "msg ai";
  msg.id = "typing-msg";
  msg.innerHTML = `
    <div class="avatar ai">D</div>
    <div class="bubble">
      <span class="typing-label">${label || "düşünüyor"}</span>
      <span class="typing"><i></i><i></i><i></i></span>
    </div>`;
  els.messages.appendChild(msg);
  scrollBottom();
  return msg;
}

function renderMarkdownish(text) {
  // minimal: **bold**, `inline`, satır sonları korunur (pre-wrap)
  const esc = text
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return esc
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(
      /(https?:\/\/[^\s<]+)/g,
      '<a class="src-link" href="$1" target="_blank" rel="noopener">$1</a>'
    )
    .replace(/`([^`]+)`/g, "<code style=\"font-family:var(--mono);font-size:13px;background:rgba(255,255,255,0.08);padding:2px 6px;border-radius:5px;word-break:break-all\">$1</code>");
}

function addAiMsg({ reply, code, lang, source, url, neural_sample }) {
  const typing = document.getElementById("typing-msg");
  if (typing) typing.remove();

  const msg = document.createElement("div");
  msg.className = "msg ai";
  msg.innerHTML = `<div class="avatar ai">D</div>`;

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  const textEl = document.createElement("div");
  textEl.innerHTML = renderMarkdownish(reply || "");
  bubble.appendChild(textEl);

  if (code) {
    const block = document.createElement("div");
    block.className = "codeblock";

    const head = document.createElement("div");
    head.className = "codeblock-head";
    head.innerHTML = `<span class="codeblock-lang">${lang || "code"}</span>`;

    const copyBtn = document.createElement("button");
    copyBtn.className = "copy-btn";
    copyBtn.textContent = "Kopyala";
    copyBtn.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(code);
        copyBtn.textContent = "Kopyalandı ✓";
        copyBtn.classList.add("copied");
        setTimeout(() => {
          copyBtn.textContent = "Kopyala";
          copyBtn.classList.remove("copied");
        }, 1800);
      } catch {}
    });
    head.appendChild(copyBtn);

    const pre = document.createElement("pre");
    pre.textContent = code;

    block.append(head, pre);
    bubble.appendChild(block);
  }

  if (url) {
    const link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.rel = "noopener";
    link.className = "src-link";
    link.textContent = "Kaynağı aç ↗";
    link.style.cssText = "display:inline-block;margin-top:10px;font-size:12.5px;color:var(--blue);text-decoration:none;max-width:100%;overflow-wrap:anywhere";
    bubble.appendChild(document.createElement("br"));
    bubble.appendChild(link);
  }

  if (neural_sample) {
    const nb = document.createElement("div");
    nb.className = "codeblock";
    nb.innerHTML = `<div class="codeblock-head"><span class="codeblock-lang">nöral · deneysel</span></div>`;
    const pre = document.createElement("pre");
    pre.textContent = neural_sample;
    nb.appendChild(pre);
    bubble.appendChild(nb);
  }

  const srcNames = { kb: "bilgi tabanı", chat: "sohbet", math: "hesap", fallback: "öneri", web: "web", learned: "öğrenilmiş", memory: "geçmiş başarı", neural: "nöral (deneysel)" };
  if (source) {
    const tag = document.createElement("span");
    tag.className = "src-tag";
    tag.textContent = `· ${srcNames[source] || source}`;
    bubble.appendChild(tag);
  }

  msg.appendChild(bubble);
  els.messages.appendChild(msg);
  scrollBottom();
}

/* ---------- chat flow ---------- */

async function sendMessage(text) {
  text = (text || "").trim();
  if (!text || busy) return;
  busy = true;
  els.send.disabled = true;

  addUserMsg(text);
  els.input.value = "";
  autoResize();
  addTyping("düşünüyor");

  const started = Date.now();
  try {
    const data = await api("/api/chat", {
      message: text,
      history: chatHistory.slice(-16),
    });
    chatHistory.push({ role: "user", content: text });
    // AI cevabının daha fazlasını tut — takip soruları için konu lazım
    chatHistory.push({ role: "ai", content: (data.reply || "").slice(0, 1200) });
    if (chatHistory.length > 48) chatHistory = chatHistory.slice(-48);

    // düşünme hissi: en az ~700ms, düşünce varsa biraz daha
    const thinkMs = data.thinking ? 900 : 650;
    const wait = Math.max(0, thinkMs - (Date.now() - started));
    if (wait > 0) {
      const t = document.getElementById("typing-msg");
      const lab = t?.querySelector(".typing-label");
      if (lab && data.thinking) lab.textContent = "bağlamı okuyor";
      await new Promise((r) => setTimeout(r, wait));
    }
    addAiMsg(data);
  } catch (err) {
    addAiMsg({ reply: "Bir hata oluştu, tekrar dener misin? 🙏", source: "chat" });
  } finally {
    busy = false;
    els.send.disabled = false;
    els.input.focus();
  }
}

/* ---------- composer ---------- */

function autoResize() {
  els.input.style.height = "auto";
  els.input.style.height = Math.min(els.input.scrollHeight, 160) + "px";
}

els.input.addEventListener("input", autoResize);

els.input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage(els.input.value);
  }
});

els.composer.addEventListener("submit", (e) => {
  e.preventDefault();
  sendMessage(els.input.value);
});

els.btnNew.addEventListener("click", () => {
  chatHistory = [];
  els.messages.innerHTML = "";
  const welcome = document.createElement("div");
  welcome.className = "welcome";
  welcome.innerHTML = `
    <div class="welcome-mark"></div>
    <h1>Nasıl yardımcı olabilirim?</h1>
    <p>Kod odaklı sorular sor — Python, JavaScript, SQL, Git…</p>`;
  const chipBox = document.createElement("div");
  chipBox.className = "chips center";
  fillChips(chipBox, 4);
  welcome.appendChild(chipBox);
  els.messages.appendChild(welcome);
  els.welcome = welcome;
  els.input.focus();
});

/* ---------- chips ---------- */

function fillChips(container, count) {
  const picks = [...SUGGESTIONS].sort(() => Math.random() - 0.5).slice(0, count);
  container.innerHTML = "";
  for (const s of picks) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "chip";
    chip.textContent = s;
    chip.addEventListener("click", () => sendMessage(s));
    container.appendChild(chip);
  }
}

fillChips(els.chips, 6);
fillChips(els.welcomeChips, 4);

/* ---------- status polling ---------- */

function setLive(on) {
  els.liveDot.className = `dot ${on ? "on" : "off"}`;
  els.liveLabel.textContent = on ? (autoOn ? "öğreniyor" : "çevrimiçi") : "çevrimdışı";
}

async function refresh() {
  try {
    const s = await api("/api/status");
    els.steps.textContent = s.steps ?? "—";
    els.ok.textContent = s.accepted ?? "—";
    els.loss.textContent = s.last_loss ? Number(s.last_loss).toFixed(2) : "—";
    autoOn = !!s.running;
    els.btnAuto.classList.toggle("on", autoOn);
    els.btnAuto.setAttribute("aria-checked", String(autoOn));
    updateTrainPanel(s.train_job || {});
    setLive(true);
  } catch {
    setLive(false);
  }
}

/* ---------- targeted training ---------- */

const trainSteps = $("train-steps");
const btnTrain = $("btn-train");
const trainProgress = $("train-progress");
const trainBar = $("train-bar");
const trainPct = $("train-pct");
const trainMsg = $("train-msg");

function updateTrainPanel(job) {
  const active = !!job.active;
  btnTrain.disabled = active;
  btnTrain.textContent = active ? "Eğitiliyor…" : "Eğit";
  trainProgress.hidden = !active && !job.message;
  if (active) {
    const pct = Math.round((job.progress || 0) * 100);
    trainBar.style.width = `${pct}%`;
    trainPct.textContent = `${pct}%`;
    let msg = job.message || "eğitiliyor…";
    if (job.eta_sec != null) {
      const m = Math.ceil(job.eta_sec / 60);
      msg += ` · ~${m} dk kaldı`;
    }
    trainMsg.textContent = msg;
  } else if (job.message) {
    trainBar.style.width = "100%";
    trainPct.textContent = "";
    trainMsg.textContent = job.message;
  }
}

btnTrain?.addEventListener("click", async () => {
  const n = Math.max(100, Math.min(1000000, Number(trainSteps.value) || 1000));
  btnTrain.disabled = true;
  trainMsg.textContent = "eğitim başlatılıyor…";
  try {
    const data = await api("/api/train", { steps: n });
    updateTrainPanel(data.job || {});
  } catch {
    trainMsg.textContent = "eğitim başlatılamadı";
    btnTrain.disabled = false;
  }
});

els.btnAuto.addEventListener("click", async () => {
  try {
    const data = autoOn
      ? await api("/api/autolearn/stop", {})
      : await api("/api/autolearn/start", { interval: 3 });
    autoOn = !!data.state?.running;
    els.btnAuto.classList.toggle("on", autoOn);
  } catch {}
});

/* ---------- mobile drawer ---------- */

const sidebar = document.getElementById("sidebar");
const overlay = document.getElementById("overlay");
const btnMenu = document.getElementById("btn-menu");
const liveDotM = document.getElementById("live-dot-m");

function closeDrawer() {
  sidebar.classList.remove("open");
  overlay.classList.remove("show");
}

btnMenu?.addEventListener("click", () => {
  sidebar.classList.toggle("open");
  overlay.classList.toggle("show", sidebar.classList.contains("open"));
});
overlay?.addEventListener("click", closeDrawer);

// chip tıklanınca mobilde menüyü kapat
document.addEventListener("click", (e) => {
  if (e.target.closest(".chip") && window.innerWidth <= 800) closeDrawer();
});

const origSetLive = setLive;
setLive = (on) => {
  origSetLive(on);
  if (liveDotM) liveDotM.className = `dot ${on ? "on" : "off"}`;
};

refresh();
setInterval(refresh, 3000);
if (window.innerWidth > 800) els.input.focus();
