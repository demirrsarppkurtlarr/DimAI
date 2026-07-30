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

function addTyping() {
  hideWelcome();
  const msg = document.createElement("div");
  msg.className = "msg ai";
  msg.id = "typing-msg";
  msg.innerHTML = `
    <div class="avatar ai">D</div>
    <div class="bubble"><span class="typing"><i></i><i></i><i></i></span></div>`;
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
    .replace(/`([^`]+)`/g, "<code style=\"font-family:var(--mono);font-size:13px;background:rgba(255,255,255,0.08);padding:2px 6px;border-radius:5px\">$1</code>");
}

function addAiMsg({ reply, code, lang, source }) {
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

  const srcNames = { kb: "bilgi tabanı", chat: "sohbet", math: "hesap", fallback: "öneri", neural: "nöral (deneysel)" };
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
  addTyping();

  const started = Date.now();
  try {
    const data = await api("/api/chat", { message: text });
    // insanımsı minik gecikme
    const wait = Math.max(0, 500 - (Date.now() - started));
    await new Promise((r) => setTimeout(r, wait));
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
    setLive(true);
  } catch {
    setLive(false);
  }
}

els.btnAuto.addEventListener("click", async () => {
  try {
    const data = autoOn
      ? await api("/api/autolearn/stop", {})
      : await api("/api/autolearn/start", { interval: 3 });
    autoOn = !!data.state?.running;
    els.btnAuto.classList.toggle("on", autoOn);
  } catch {}
});

refresh();
setInterval(refresh, 3000);
els.input.focus();
