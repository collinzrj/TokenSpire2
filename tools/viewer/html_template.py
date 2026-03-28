"""HTML template for the viewer UI."""

VIEWER_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>TokenSpire2 — Live Viewer</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #1a1a2e; color: #e0e0e0; display: flex; height: 100vh; overflow: hidden; }

  #sidebar { width: 280px; min-width: 0; background: #16213e; display: flex; flex-direction: column; border-right: 1px solid #0f3460; transition: width 0.2s; overflow: hidden; }
  #sidebar.collapsed { width: 0; border-right: none; }
  #sidebar-toggle { position: absolute; left: 0; top: 50%; transform: translateY(-50%); z-index: 10; background: #0f3460; color: #e0e0e0; border: 1px solid #0f3460; border-left: none; padding: 8px 4px; cursor: pointer; font-size: 14px; border-radius: 0 4px 4px 0; transition: left 0.2s; }
  #sidebar-toggle.open { left: 280px; }
  #sidebar h2 { padding: 16px; font-size: 14px; color: #e94560; border-bottom: 1px solid #0f3460; }
  #run-tabs { display: flex; gap: 4px; padding: 8px; flex-wrap: wrap; }
  .run-tab { padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 12px; background: #0f3460; border: none; color: #e0e0e0; }
  .run-tab.active { background: #e94560; color: white; }
  .run-tab:hover { opacity: 0.8; }
  #msg-list { flex: 1; overflow-y: auto; padding: 4px; }
  .msg-item { padding: 6px 8px; margin: 2px 0; border-radius: 4px; cursor: pointer; font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; border-left: 3px solid transparent; }
  .msg-item:hover { background: #1a1a4e; }
  .msg-item.active { background: #1a1a4e; border-left-color: #e94560; }
  .msg-item .label { font-weight: 600; margin-right: 4px; }
  .ctx-combat .label { color: #e94560; }
  .ctx-map .label { color: #4ecdc4; }
  .ctx-event .label { color: #f7b731; }
  .ctx-shop .label { color: #a55eea; }
  .ctx-restsite .label { color: #26de81; }
  .ctx-overlay .label { color: #45aaf2; }
  .ctx-gameover_reflection .label { color: #888; }
  .ctx-unknown .label { color: #666; }
  .msg-item.streaming .label::after { content: " ●"; color: #26de81; animation: blink 1s infinite; }
  @keyframes blink { 50% { opacity: 0.3; } }
  #status { padding: 8px; font-size: 11px; color: #666; border-top: 1px solid #0f3460; }

  #main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
  #main-header { padding: 12px 16px; background: #16213e; border-bottom: 1px solid #0f3460; font-size: 13px; }
  #content { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 16px; }

  .message-block { background: #16213e; border-radius: 8px; padding: 16px; }
  .message-block h3 { font-size: 12px; text-transform: uppercase; margin-bottom: 8px; letter-spacing: 1px; }
  .message-block.user h3 { color: #4ecdc4; }
  .message-block.assistant h3 { color: #e94560; }
  .message-block pre { white-space: pre-wrap; word-wrap: break-word; font-size: 13px; line-height: 1.6; font-family: 'Cascadia Code', 'Fira Code', monospace; }

  .thinking-block { background: #1a1a0e; border: 1px solid #333300; border-radius: 8px; padding: 16px; }
  .thinking-block h3 { color: #f7b731; font-size: 12px; text-transform: uppercase; margin-bottom: 8px; letter-spacing: 1px; }
  .thinking-block pre { white-space: pre-wrap; word-wrap: break-word; font-size: 13px; line-height: 1.6; font-family: 'Cascadia Code', 'Fira Code', monospace; color: #bba; }

  .summary-block { background: #0e1a1a; border: 1px solid #003333; border-radius: 8px; padding: 16px; }
  .summary-block h3 { color: #26de81; font-size: 12px; text-transform: uppercase; margin-bottom: 8px; letter-spacing: 1px; }
  .summary-item { color: #8ed1c0; font-size: 13px; line-height: 1.6; padding: 4px 0; border-bottom: 1px solid #002222; }
  .summary-item:last-child { border-bottom: none; }
  .summary-idx { color: #26de81; font-weight: 600; margin-right: 6px; }

  #auto-scroll-bar { padding: 6px 16px; background: #0f3460; font-size: 12px; display: flex; align-items: center; gap: 8px; }
  #auto-scroll-bar label { cursor: pointer; }
  .tts-playing { animation: pulse 0.5s infinite alternate; }
  @keyframes pulse { from { opacity: 1; } to { opacity: 0.6; } }
</style>
</head>
<body>
<button id="sidebar-toggle" class="open" onclick="toggleSidebar()">◀</button>
<div id="sidebar">
  <div id="run-tabs"></div>
  <div id="msg-list"></div>
  <div id="status">Connecting...</div>
</div>
<div id="main">
  <div id="main-header">Select a message from the sidebar</div>
  <div id="content"></div>
  <div id="auto-scroll-bar">
    <label><input type="checkbox" id="auto-scroll" checked> Auto-follow latest</label>
    <label><input type="checkbox" id="tts-enabled"> TTS</label>
    <label>Vol <input type="range" id="tts-volume" min="0" max="100" value="50" style="width:80px;vertical-align:middle"></label>
    <span id="last-update"></span>
  </div>
</div>
<script>
const POLL_INTERVAL = 100;
let data = [];
let selectedRun = -1;
let selectedMsg = -1;
let lastJson = "";

function toggleSidebar() {
  const sb = document.getElementById("sidebar");
  const btn = document.getElementById("sidebar-toggle");
  sb.classList.toggle("collapsed");
  btn.classList.toggle("open");
  btn.textContent = sb.classList.contains("collapsed") ? "▶" : "◀";
}

function ctxLabel(c) { return !c ? "unknown" : c.startsWith("overlay:") ? c.split(":")[1] : c; }
function ctxClass(c) { return !c ? "ctx-unknown" : c.startsWith("overlay") ? "ctx-overlay" : "ctx-"+c; }
function esc(s) { return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }

function renderRunTabs() {
  document.getElementById("run-tabs").innerHTML = data.map((r, i) =>
    `<button class="run-tab ${i===selectedRun?'active':''}" onclick="selectRun(${i})">Run ${i+1} (${Math.floor((r.messages||[]).length/2)} turns)</button>`
  ).join("");
}

function renderMsgList() {
  const el = document.getElementById("msg-list");
  if (selectedRun < 0 || selectedRun >= data.length) { el.innerHTML = ""; return; }
  const msgs = data[selectedRun].messages || [];
  let html = "";
  for (let i = 0; i < msgs.length; i++) {
    const m = msgs[i];
    if (m.role !== "user") continue;
    const ctx = m.context || "unknown";
    const preview = m.content.split("\n")[0].substring(0, 40);
    const hasResp = i+1 < msgs.length && msgs[i+1].role === "assistant";
    const streaming = !hasResp || (!msgs[i+1].content && msgs[i+1].cot);
    html += `<div class="msg-item ${ctxClass(ctx)}${streaming?" streaming":""} ${i===selectedMsg?'active':''}" onclick="selectMsg(${i})">
      <span class="label">${ctxLabel(ctx)}</span>${preview}</div>`;
  }
  el.innerHTML = html;
}

function renderContent() {
  const el = document.getElementById("content");
  const hdr = document.getElementById("main-header");
  if (selectedRun < 0 || selectedMsg < 0) { el.innerHTML = ""; return; }
  const msgs = data[selectedRun].messages || [];
  const u = msgs[selectedMsg];
  if (!u) { el.innerHTML = ""; return; }
  const a = (selectedMsg+1 < msgs.length && msgs[selectedMsg+1].role === "assistant") ? msgs[selectedMsg+1] : null;

  const time = u.timestamp ? new Date(u.timestamp).toLocaleTimeString() : "";
  hdr.innerHTML = `<strong>${ctxLabel(u.context||"unknown").toUpperCase()}</strong><span style="color:#666;margin-left:8px">${time}</span>`;

  let html = `<div class="message-block user"><h3>Game State</h3><pre>${esc(u.content)}</pre></div>`;
  if (a) {
    // Scene description (phase 1)
    if (a.scene) {
      html += `<div class="summary-block"><h3>Scene</h3><div class="summary-item">${esc(a.scene)}</div></div>`;
    } else if (!a.content) {
      html += `<div class="summary-block"><h3>Scene</h3><div class="summary-item" style="color:#666">⏳ Describing...</div></div>`;
    }
    // Decision summary (phase 2)
    if (a.summary) {
      html += `<div class="summary-block"><h3>Decision Summary</h3><div class="summary-item">${esc(a.summary)}</div></div>`;
    } else if (a.content) {
      html += `<div class="summary-block"><h3>Decision Summary</h3><div class="summary-item" style="color:#666">⏳ Summarizing...</div></div>`;
    }
    const txt = a.content || (a.cot ? "⏳ Thinking..." : "⏳ Waiting...");
    html += `<div class="message-block assistant"><h3>LLM Response</h3><pre${!a.content?' style="color:#666"':''}>${esc(txt)}</pre></div>`;
  } else {
    html += `<div class="message-block assistant"><h3>LLM Response</h3><pre style="color:#666">⏳ Waiting for response...</pre></div>`;
  }
  el.innerHTML = html;
}

function selectRun(i) { selectedRun = i; selectedMsg = -1; renderRunTabs(); renderMsgList(); renderContent(); }
function selectMsg(i) { selectedMsg = i; renderMsgList(); renderContent(); }

async function poll() {
  try {
    const resp = await fetch("/api/state?" + Date.now());
    const text = await resp.text();
    if (text === lastJson) return;
    lastJson = text;
    data = JSON.parse(text);

    const af = document.getElementById("auto-scroll").checked;
    if (af || selectedRun < 0) {
      selectedRun = data.length - 1;
      const msgs = data[selectedRun]?.messages || [];
      let last = -1;
      for (let i = msgs.length-1; i >= 0; i--) { if (msgs[i].role==="user") { last=i; break; } }
      if (af && last >= 0) selectedMsg = last;
    }
    renderRunTabs(); renderMsgList(); renderContent();
    document.getElementById("status").textContent = `${data.length} run(s) loaded`;
    document.getElementById("last-update").textContent = `Updated: ${new Date().toLocaleTimeString()}`;
    if (af) {
      document.getElementById("msg-list").scrollTop = 999999;
      document.getElementById("content").scrollTop = 999999;
    }
  } catch (e) {
    document.getElementById("status").textContent = "Error: " + e.message;
  }
}
// ─── TTS (two-phase: scene then summary) ───
let lastSceneKey = "";
let lastSummaryKey = "";
let ttsInitialized = false;
let ttsPlaying = false;
let pendingTtsText = null;
let prefetchedBlob = null;
let prefetchingKey = null;

function prefetchAudio(text, key) {
  // No prefetch for WebSocket — playback is streamed live
  prefetchingKey = key;
  prefetchedBlob = null;
}

function getLatestAudio() {
  if (data.length === 0) return null;
  for (let ri = data.length - 1; ri >= 0; ri--) {
    const msgs = data[ri].messages || [];
    for (let mi = msgs.length - 1; mi >= 0; mi--) {
      const m = msgs[mi];
      if (m.role !== "assistant") continue;
      const sumKey = `sum:${ri}:${mi}`;
      if (m.summary && sumKey !== lastSummaryKey) {
        return { key: sumKey, text: m.summary, type: "summary", ri, mi };
      }
      const scnKey = `scn:${ri}:${mi}`;
      if (m.scene && scnKey !== lastSceneKey) {
        return { key: scnKey, text: m.scene, type: "scene", ri, mi, scene_t: m.scene_t };
      }
      return null;
    }
  }
  return null;
}

let pendingTtsType = null;

let pendingRi = -1, pendingMi = -1;
let pendingSceneT = null;

function checkNewAudio() {
  if (!document.getElementById("tts-enabled").checked) {
    const info = getLatestAudio();
    if (info) {
      if (info.type === "scene") lastSceneKey = info.key;
      if (info.type === "summary") { lastSummaryKey = info.key; sendProceed(info.ri, info.mi); }
    }
    return;
  }
  const info = getLatestAudio();
  if (!info) return;
  if (!ttsInitialized) {
    if (info.type === "scene") lastSceneKey = info.key;
    if (info.type === "summary") { lastSummaryKey = info.key; sendProceed(info.ri, info.mi); }
    ttsInitialized = true;
    return;
  }
  if (info.type === "scene") lastSceneKey = info.key;
  if (info.type === "summary") lastSummaryKey = info.key;
  // Prefetch audio immediately (even while current audio plays)
  prefetchAudio(info.text, info.key);
  pendingTtsText = info.text;
  pendingTtsType = info.type;
  pendingSceneT = info.scene_t || null;
  pendingRi = info.ri;
  pendingMi = info.mi;
  if (!ttsPlaying) playNext();
}

let lastProceedKey = "";

function sendProceed(ri, mi) {
  const key = `${ri}:${mi}`;
  if (key === lastProceedKey) return; // avoid duplicate
  lastProceedKey = key;
  fetch("/api/proceed", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({run: ri, msg: mi})
  }).catch(e => console.error("Proceed error:", e));
}

let sharedAudioCtx = null;
function getAudioCtx() {
  if (!sharedAudioCtx || sharedAudioCtx.state === "closed") {
    sharedAudioCtx = new AudioContext({ sampleRate: 24000 });
  }
  if (sharedAudioCtx.state === "suspended") sharedAudioCtx.resume();
  return sharedAudioCtx;
}

async function playNext() {
  if (!pendingTtsText || ttsPlaying) return;
  const text = pendingTtsText;
  const type = pendingTtsType;
  const ri = pendingRi;
  const mi = pendingMi;
  const scene_t = pendingSceneT;
  pendingTtsText = null;
  pendingTtsType = null;
  pendingSceneT = null;
  ttsPlaying = true;
  try {
    const ctx = getAudioCtx();
    const vol = ctx.createGain();
    vol.gain.value = document.getElementById("tts-volume").value / 100;
    vol.connect(ctx.destination);
    let nextTime = ctx.currentTime + 0.1;

    await new Promise((resolve, reject) => {
      const ws = new WebSocket("ws://localhost:5556");
      ws.binaryType = "arraybuffer";

      ws.onopen = () => {
        ws.send(JSON.stringify({ text, scene_t }));
      };

      ws.onmessage = (e) => {
        const buf = e.data;
        if (buf.byteLength === 0) { ws.close(); return; } // end signal
        const samples = buf.byteLength / 2;
        const view = new DataView(buf);
        const floats = new Float32Array(samples);
        for (let i = 0; i < samples; i++) floats[i] = view.getInt16(i * 2, true) / 32768.0;
        const audioBuf = ctx.createBuffer(1, samples, 24000);
        audioBuf.getChannelData(0).set(floats);
        const src = ctx.createBufferSource();
        src.buffer = audioBuf;
        src.connect(vol);
        if (nextTime < ctx.currentTime) nextTime = ctx.currentTime;
        src.start(nextTime);
        nextTime += audioBuf.duration;
      };

      ws.onclose = () => {
        // Wait for all scheduled audio to finish, then disconnect gain node
        const remaining = Math.max(0, nextTime - ctx.currentTime);
        setTimeout(() => {
          vol.disconnect();
          resolve();
        }, remaining * 1000 + 100);
      };

      ws.onerror = (e) => {
        console.error("WS-TTS error:", e);
        vol.disconnect();
        reject(e);
      };
    });
    // Success — audio finished
    ttsPlaying = false;
    if (type === "summary") sendProceed(ri, mi);
    if (pendingTtsText) setTimeout(playNext, 500);
  } catch (e) {
    console.error("TTS error:", e);
    ttsPlaying = false;
    if (type === "summary") sendProceed(ri, mi);
    if (pendingTtsText) setTimeout(playNext, 500);
  }
}

setInterval(poll, POLL_INTERVAL);
setInterval(checkNewAudio, POLL_INTERVAL);
poll();
</script>
</body>
</html>"""
