#!/usr/bin/env python3
"""
TokenSpire2 Live Conversation Viewer

Watches the LLM history JSON file and serves a live-updating web UI.

Usage:
    python viewer.py                          # auto-find latest JSON in default mod folder
    python viewer.py path/to/llm_history.json # watch a specific file
    python viewer.py --port 8080              # custom port
"""

import argparse
import glob
import json
import os
import sys
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

DEFAULT_MOD_PATHS = [
    os.path.expandvars(r"%ProgramFiles(x86)%\..\SteamLibrary\steamapps\common\Slay the Spire 2\mods\TokenSpire2"),
    os.path.expandvars(r"D:\SteamLibrary\steamapps\common\Slay the Spire 2\mods\TokenSpire2"),
    os.path.expandvars(r"C:\Program Files (x86)\Steam\steamapps\common\Slay the Spire 2\mods\TokenSpire2"),
    os.path.expanduser("~/Library/Application Support/Steam/steamapps/common/Slay the Spire 2/mods/TokenSpire2"),
]


def find_latest_history(base_dir: str) -> str | None:
    pattern = os.path.join(base_dir, "llm_history_*.json")
    files = glob.glob(pattern)
    return max(files, key=os.path.getmtime) if files else None


def find_json_file(explicit_path: str | None) -> tuple[str | None, str | None]:
    """Returns (json_path, watch_dir). If json_path is None, watch_dir is polled for new files."""
    if explicit_path and os.path.isfile(explicit_path):
        return explicit_path, None
    if explicit_path and os.path.isdir(explicit_path):
        f = find_latest_history(explicit_path)
        if f:
            return f, explicit_path
        return None, explicit_path
    for mod_path in DEFAULT_MOD_PATHS:
        if os.path.isdir(mod_path):
            f = find_latest_history(mod_path)
            if f:
                return f, mod_path
            return None, mod_path
    print("Error: Could not find mod folder or JSON file.")
    print("Usage: python viewer.py [path/to/llm_history.json | path/to/mod/folder]")
    sys.exit(1)


VIEWER_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>TokenSpire2 — Live Viewer</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #1a1a2e; color: #e0e0e0; display: flex; height: 100vh; overflow: hidden; }

  /* Sidebar */
  #sidebar { width: 280px; min-width: 280px; background: #16213e; display: flex; flex-direction: column; border-right: 1px solid #0f3460; }
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
  #status { padding: 8px; font-size: 11px; color: #666; border-top: 1px solid #0f3460; }

  /* Main */
  #main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
  #main-header { padding: 12px 16px; background: #16213e; border-bottom: 1px solid #0f3460; font-size: 13px; }
  #main-header .time { color: #666; margin-left: 8px; }
  #content { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 16px; }

  .message-block { background: #16213e; border-radius: 8px; padding: 16px; }
  .message-block h3 { font-size: 12px; text-transform: uppercase; margin-bottom: 8px; letter-spacing: 1px; }
  .message-block.user h3 { color: #4ecdc4; }
  .message-block.assistant h3 { color: #e94560; }
  .message-block.thinking h3 { color: #f7b731; }
  .message-block pre { white-space: pre-wrap; word-wrap: break-word; font-size: 13px; line-height: 1.6; font-family: 'Cascadia Code', 'Fira Code', monospace; }
  .message-block.thinking { background: #1a1a0e; border: 1px solid #333300; }
  .message-block.thinking pre { color: #bba; font-size: 12px; }
  .thinking-toggle { cursor: pointer; color: #f7b731; font-size: 12px; margin-bottom: 4px; user-select: none; }
  .thinking-toggle:hover { text-decoration: underline; }

  /* Auto-scroll toggle */
  #auto-scroll-bar { padding: 6px 16px; background: #0f3460; font-size: 12px; display: flex; align-items: center; gap: 8px; }
  #auto-scroll-bar label { cursor: pointer; }
</style>
</head>
<body>

<div id="sidebar">
  <h2>TokenSpire2 Viewer</h2>
  <div id="run-tabs"></div>
  <div id="msg-list"></div>
  <div id="status">Connecting...</div>
</div>

<div id="main">
  <div id="main-header">Select a message from the sidebar</div>
  <div id="content"></div>
  <div id="auto-scroll-bar">
    <label><input type="checkbox" id="auto-scroll" checked> Auto-follow latest</label>
    <span id="last-update"></span>
  </div>
</div>

<script>
const POLL_INTERVAL = 2000;
let data = [];
let selectedRun = -1;
let selectedMsg = -1;
let lastJson = "";

function contextLabel(ctx) {
  if (!ctx) return "unknown";
  if (ctx.startsWith("overlay:")) return ctx.split(":")[1];
  return ctx;
}

function contextClass(ctx) {
  if (!ctx) return "ctx-unknown";
  if (ctx.startsWith("overlay")) return "ctx-overlay";
  return "ctx-" + ctx;
}

function renderRunTabs() {
  const el = document.getElementById("run-tabs");
  el.innerHTML = data.map((run, i) =>
    `<button class="run-tab ${i === selectedRun ? 'active' : ''}" onclick="selectRun(${i})">Run ${i + 1} (${run.messages ? Math.floor(run.messages.length / 2) : 0} turns)</button>`
  ).join("");
}

function renderMsgList() {
  const el = document.getElementById("msg-list");
  if (selectedRun < 0 || selectedRun >= data.length) { el.innerHTML = ""; return; }
  const msgs = data[selectedRun].messages || [];
  // Show user messages as items (pairs)
  let html = "";
  for (let i = 0; i < msgs.length; i++) {
    const m = msgs[i];
    if (m.role !== "user") continue;
    const ctx = m.context || "unknown";
    const preview = m.content.split("\n")[0].substring(0, 40);
    const pairIdx = i;
    html += `<div class="msg-item ${contextClass(ctx)} ${pairIdx === selectedMsg ? 'active' : ''}" onclick="selectMsg(${pairIdx})">
      <span class="label">${contextLabel(ctx)}</span>${preview}
    </div>`;
  }
  el.innerHTML = html;
}

function renderContent() {
  const el = document.getElementById("content");
  const header = document.getElementById("main-header");
  if (selectedRun < 0 || selectedMsg < 0) { el.innerHTML = ""; return; }
  const msgs = data[selectedRun].messages || [];
  const userMsg = msgs[selectedMsg];
  if (!userMsg) { el.innerHTML = ""; return; }
  // Find the assistant response (next message)
  const assistantMsg = (selectedMsg + 1 < msgs.length && msgs[selectedMsg + 1].role === "assistant") ? msgs[selectedMsg + 1] : null;

  const ctx = userMsg.context || "unknown";
  const time = userMsg.timestamp ? new Date(userMsg.timestamp).toLocaleTimeString() : "";
  header.innerHTML = `<strong>${contextLabel(ctx).toUpperCase()}</strong><span class="time">${time}</span>`;

  let html = `<div class="message-block user"><h3>Game State</h3><pre>${escHtml(userMsg.content)}</pre></div>`;
  if (assistantMsg) {
    if (assistantMsg.thinking) {
      html += `<div class="message-block thinking">
        <div class="thinking-toggle" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='none'?'block':'none'">▶ Thinking (click to expand)</div>
        <pre style="display:none">${escHtml(assistantMsg.thinking)}</pre>
      </div>`;
    }
    html += `<div class="message-block assistant"><h3>LLM Response</h3><pre>${escHtml(assistantMsg.content)}</pre></div>`;
  } else {
    html += `<div class="message-block assistant"><h3>LLM Response</h3><pre style="color:#666">⏳ Waiting for response...</pre></div>`;
  }
  el.innerHTML = html;
}

function escHtml(s) {
  return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

function selectRun(i) {
  selectedRun = i;
  selectedMsg = -1;
  renderRunTabs();
  renderMsgList();
  renderContent();
}

function selectMsg(i) {
  selectedMsg = i;
  renderMsgList();
  renderContent();
}

async function poll() {
  try {
    const resp = await fetch("/api/state?" + Date.now());
    const text = await resp.text();
    if (text === lastJson) { return; }
    lastJson = text;
    data = JSON.parse(text);

    const autoFollow = document.getElementById("auto-scroll").checked;
    // Auto-select latest run if following
    if (autoFollow || selectedRun < 0) {
      const newRun = data.length - 1;
      const msgs = data[newRun]?.messages || [];
      // Find last user message index
      let lastUserIdx = -1;
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i].role === "user") { lastUserIdx = i; break; }
      }
      selectedRun = newRun;
      if (autoFollow && lastUserIdx >= 0) selectedMsg = lastUserIdx;
    }
    renderRunTabs();
    renderMsgList();
    renderContent();
    document.getElementById("status").textContent = `${data.length} run(s) loaded`;
    document.getElementById("last-update").textContent = `Updated: ${new Date().toLocaleTimeString()}`;

    // Scroll sidebar to bottom if auto-follow
    if (autoFollow) {
      const list = document.getElementById("msg-list");
      list.scrollTop = list.scrollHeight;
    }
  } catch (e) {
    document.getElementById("status").textContent = "Error: " + e.message;
  }
}

setInterval(poll, POLL_INTERVAL);
poll();
</script>
</body>
</html>"""


class ViewerHandler(SimpleHTTPRequestHandler):
    json_path = None
    watch_dir = None

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(VIEWER_HTML.encode("utf-8"))
        elif parsed.path == "/api/state":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            # Auto-discover latest file if watching a directory
            path = self.json_path
            if self.watch_dir:
                latest = find_latest_history(self.watch_dir)
                if latest:
                    if path != latest:
                        ViewerHandler.json_path = latest
                        print(f"Now watching: {latest}")
                    path = latest
            try:
                if path:
                    with open(path, "r", encoding="utf-8") as f:
                        self.wfile.write(f.read().encode("utf-8"))
                else:
                    self.wfile.write(b"[]")
            except (FileNotFoundError, PermissionError):
                self.wfile.write(b"[]")
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        pass  # suppress access logs


def main():
    parser = argparse.ArgumentParser(description="TokenSpire2 Live Conversation Viewer")
    parser.add_argument("path", nargs="?", help="Path to llm_history JSON file or mod folder")
    parser.add_argument("--port", type=int, default=5555, help="HTTP port (default: 5555)")
    args = parser.parse_args()

    json_path, watch_dir = find_json_file(args.path)
    if json_path:
        print(f"Watching: {json_path}")
    elif watch_dir:
        print(f"Watching folder: {watch_dir} (waiting for game to start...)")
    print(f"Open http://localhost:{args.port} in your browser")
    print()

    ViewerHandler.json_path = json_path
    ViewerHandler.watch_dir = watch_dir
    server = HTTPServer(("127.0.0.1", args.port), ViewerHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
