
#!/usr/bin/env python3
"""
UnblockR - main.py
GUI client for the UnblockR proxy network.
Runs via launcher.vbs (hidden console).
"""

import sys
import os
import json
import winreg
import ctypes
import threading
import subprocess
import urllib.request
from pathlib import Path

# ── Ensure pywebview is available ──────────────────────────────────────────────
try:
    import webview
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pywebview", "-q"])
    import webview

# ── Config ─────────────────────────────────────────────────────────────────────
PROXY_IP   = "192.168.0.193"
PROXY_PORT = 8080
PROXY_ADDR = f"{PROXY_IP}:{PROXY_PORT}"
VERSION    = "1.0.0"
SETTINGS_FILE = Path(os.path.dirname(os.path.abspath(__file__))) / "settings.json"

REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
PROXY_BYPASS = "localhost;127.*;192.168.*;<local>"

TEST_URL  = f"http://{PROXY_IP}:{PROXY_PORT}"   # hit the proxy itself
DASH_URL  = f"http://{PROXY_IP}:8081/api/stats"

# ── Settings ───────────────────────────────────────────────────────────────────
def load_settings():
    defaults = {"window": {"x": 120, "y": 120, "w": 940, "h": 620}}
    try:
        if SETTINGS_FILE.exists():
            d = json.loads(SETTINGS_FILE.read_text())
            defaults.update(d)
    except Exception:
        pass
    return defaults

def save_settings(d):
    try:
        SETTINGS_FILE.write_text(json.dumps(d, indent=2))
    except Exception:
        pass

# ── Registry proxy helpers ─────────────────────────────────────────────────────
def _reg_open(write=False):
    access = winreg.KEY_WRITE if write else winreg.KEY_READ
    return winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, access)

def _reg_get(name):
    try:
        k = _reg_open()
        v, _ = winreg.QueryValueEx(k, name)
        winreg.CloseKey(k)
        return v
    except Exception:
        return None

def _reg_set(name, value, kind=winreg.REG_SZ):
    k = _reg_open(write=True)
    winreg.SetValueEx(k, name, 0, kind, value)
    winreg.CloseKey(k)

def _notify_windows():
    try:
        wininet = ctypes.windll.wininet
        wininet.InternetSetOptionW(0, 39, 0, 0)
        wininet.InternetSetOptionW(0, 37, 0, 0)
    except Exception:
        pass

def proxy_is_active():
    return _reg_get("ProxyEnable") == 1 and _reg_get("ProxyServer") == PROXY_ADDR

def enable_proxy():
    _reg_set("ProxyEnable", 1, winreg.REG_DWORD)
    _reg_set("ProxyServer", PROXY_ADDR)
    _reg_set("ProxyOverride", PROXY_BYPASS)
    _notify_windows()

def disable_proxy():
    _reg_set("ProxyEnable", 0, winreg.REG_DWORD)
    _notify_windows()

# ── Connectivity check ─────────────────────────────────────────────────────────
def check_server(timeout=4):
    try:
        req = urllib.request.urlopen(DASH_URL, timeout=timeout)
        data = json.loads(req.read())
        return True, data
    except Exception:
        return False, {}

# ── Python API exposed to JS ───────────────────────────────────────────────────
class API:
    def __init__(self):
        self.settings = load_settings()

    # Called on startup — checks server reachability
    def ping_server(self):
        ok, data = check_server()
        return {
            "online": ok,
            "proxy_active": proxy_is_active(),
            "stats": data,
            "proxy_addr": PROXY_ADDR,
            "version": VERSION,
        }

    # Toggle proxy on/off
    def toggle_proxy(self):
        if proxy_is_active():
            disable_proxy()
            active = False
        else:
            enable_proxy()
            active = True
        return {"proxy_active": active}

    # Get current state without changing anything
    def get_state(self):
        ok, data = check_server(timeout=3)
        return {
            "online": ok,
            "proxy_active": proxy_is_active(),
            "stats": data,
        }

    # Retry server connection
    def retry_connection(self):
        ok, data = check_server(timeout=5)
        return {
            "online": ok,
            "proxy_active": proxy_is_active(),
            "stats": data,
        }

    def close(self):
        s = self.settings
        try:
            pos  = window.get_position()
            size = window.get_size()
            s["window"] = {"x": pos[0], "y": pos[1], "w": size[0], "h": size[1]}
        except Exception:
            pass
        save_settings(s)
        os._exit(0)

# ── HTML/CSS/JS ────────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>UnblockR</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@600;700;800&display=swap" rel="stylesheet">
<style>
  :root {
    --bg:       #070a0f;
    --surface:  #0d1219;
    --raised:   #121820;
    --border:   #1e2a38;
    --border2:  #2a3a4e;
    --text:     #c8d8e8;
    --muted:    #4a6070;
    --on:       #00e5a0;
    --on-dim:   rgba(0,229,160,0.12);
    --off:      #e55050;
    --off-dim:  rgba(229,80,80,0.12);
    --accent:   #3d9eff;
    --accent-d: rgba(61,158,255,0.1);
    --mono:     'DM Mono', monospace;
    --display:  'Syne', sans-serif;
  }

  *, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }

  body {
    font-family: var(--mono);
    background: var(--bg);
    color: var(--text);
    height: 100vh;
    overflow: hidden;
    user-select: none;
  }

  /* Noise overlay */
  body::after {
    content: '';
    position: fixed;
    inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");
    pointer-events: none;
    z-index: 999;
    opacity: 0.35;
  }

  /* ── Loading screen ──────────────────────────────────────────────── */
  #loader {
    position: fixed;
    inset: 0;
    background: var(--bg);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    z-index: 998;
    transition: opacity 0.5s ease, transform 0.5s ease;
  }

  #loader.fade-out {
    opacity: 0;
    transform: scale(1.02);
    pointer-events: none;
  }

  .loader-wordmark {
    font-family: var(--display);
    font-size: 38px;
    font-weight: 800;
    letter-spacing: -1px;
    color: var(--text);
    margin-bottom: 8px;
  }

  .loader-wordmark span { color: var(--accent); }

  .loader-sub {
    font-size: 11px;
    color: var(--muted);
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 48px;
  }

  .progress-track {
    width: 280px;
    height: 3px;
    background: var(--border);
    border-radius: 2px;
    overflow: hidden;
    margin-bottom: 20px;
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--accent), var(--on));
    border-radius: 2px;
    width: 0%;
    transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  }

  .loader-status {
    font-size: 11px;
    color: var(--muted);
    letter-spacing: 0.06em;
    min-height: 16px;
  }

  /* ── Error screen ────────────────────────────────────────────────── */
  #error-screen {
    position: fixed;
    inset: 0;
    background: var(--bg);
    display: none;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    z-index: 997;
  }

  #error-screen.visible { display: flex; }

  .error-icon {
    font-size: 40px;
    margin-bottom: 20px;
    animation: pulse-err 2s infinite;
  }

  @keyframes pulse-err {
    0%,100% { opacity:1; }
    50% { opacity: 0.5; }
  }

  .error-title {
    font-family: var(--display);
    font-size: 22px;
    font-weight: 700;
    color: var(--off);
    margin-bottom: 10px;
  }

  .error-sub {
    font-size: 12px;
    color: var(--muted);
    text-align: center;
    line-height: 1.7;
    max-width: 320px;
    margin-bottom: 32px;
  }

  .retry-btn {
    padding: 12px 32px;
    background: var(--off-dim);
    border: 1px solid var(--off);
    border-radius: 8px;
    color: var(--off);
    font-family: var(--mono);
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .retry-btn:hover {
    background: var(--off);
    color: #fff;
  }

  /* ── App shell ───────────────────────────────────────────────────── */
  #app {
    display: flex;
    flex-direction: column;
    height: 100vh;
    opacity: 0;
    transition: opacity 0.5s ease;
  }

  #app.visible { opacity: 1; }

  /* titlebar */
  .titlebar {
    height: 52px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 20px 0 24px;
    -webkit-app-region: drag;
    flex-shrink: 0;
  }

  .wordmark {
    font-family: var(--display);
    font-size: 20px;
    font-weight: 800;
    letter-spacing: -0.5px;
    color: var(--text);
  }

  .wordmark span { color: var(--accent); }

  .titlebar-right {
    display: flex;
    align-items: center;
    gap: 16px;
    -webkit-app-region: no-drag;
  }

  .server-pill {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    background: var(--raised);
    border: 1px solid var(--border);
    border-radius: 100px;
    font-size: 11px;
    color: var(--muted);
  }

  .server-pill .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--on);
    animation: blink 2.5s infinite;
  }

  .server-pill .dot.off { background: var(--off); animation: none; }

  @keyframes blink {
    0%,100% { opacity:1; }
    50% { opacity: 0.3; }
  }

  .close-btn {
    width: 28px;
    height: 28px;
    background: transparent;
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--muted);
    font-size: 16px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s;
  }

  .close-btn:hover { background: var(--off-dim); border-color: var(--off); color: var(--off); }

  /* body layout */
  .body {
    flex: 1;
    display: flex;
    overflow: hidden;
  }

  /* sidebar */
  .sidebar {
    width: 200px;
    background: var(--surface);
    border-right: 1px solid var(--border);
    padding: 24px 0;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 20px;
    font-size: 12px;
    color: var(--muted);
    cursor: pointer;
    border-left: 2px solid transparent;
    transition: all 0.15s;
    letter-spacing: 0.04em;
  }

  .nav-item:hover { color: var(--text); background: var(--raised); }

  .nav-item.active {
    color: var(--accent);
    border-left-color: var(--accent);
    background: var(--accent-d);
  }

  .nav-icon { font-size: 14px; width: 18px; text-align: center; }

  .sidebar-bottom {
    margin-top: auto;
    padding: 16px 20px;
    border-top: 1px solid var(--border);
  }

  .version-tag {
    font-size: 10px;
    color: var(--muted);
    letter-spacing: 0.08em;
  }

  /* content */
  .content {
    flex: 1;
    overflow-y: auto;
    padding: 36px 40px;
  }

  .content::-webkit-scrollbar { width: 4px; }
  .content::-webkit-scrollbar-track { background: transparent; }
  .content::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }

  .page { display: none; animation: fadeUp 0.3s ease; }
  .page.active { display: block; }

  @keyframes fadeUp {
    from { opacity:0; transform: translateY(10px); }
    to   { opacity:1; transform: translateY(0); }
  }

  /* ── Main page ───────────────────────────────────────────────────── */
  .main-grid {
    display: grid;
    grid-template-columns: 1fr 260px;
    gap: 20px;
    align-items: start;
  }

  /* toggle card */
  .toggle-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 40px 40px 36px;
    position: relative;
    overflow: hidden;
    transition: border-color 0.3s;
  }

  .toggle-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--accent), transparent);
    transition: background 0.4s;
  }

  .toggle-card.on::before {
    background: linear-gradient(90deg, var(--on), transparent);
  }

  .toggle-card.on { border-color: rgba(0,229,160,0.2); }

  .status-label {
    font-size: 11px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 12px;
  }

  .status-value {
    font-family: var(--display);
    font-size: 42px;
    font-weight: 800;
    line-height: 1;
    margin-bottom: 6px;
    transition: color 0.3s;
  }

  .status-value.on  { color: var(--on); }
  .status-value.off { color: var(--text); }

  .status-desc {
    font-size: 12px;
    color: var(--muted);
    margin-bottom: 36px;
    line-height: 1.6;
  }

  /* big toggle button */
  .toggle-btn {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 16px 28px;
    border-radius: 12px;
    border: 1px solid var(--border2);
    background: var(--raised);
    color: var(--text);
    font-family: var(--mono);
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    width: fit-content;
  }

  .toggle-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.3);
  }

  .toggle-btn.activate {
    border-color: rgba(0,229,160,0.4);
    background: var(--on-dim);
    color: var(--on);
  }

  .toggle-btn.activate:hover { box-shadow: 0 8px 24px rgba(0,229,160,0.15); }

  .toggle-btn.deactivate {
    border-color: rgba(229,80,80,0.4);
    background: var(--off-dim);
    color: var(--off);
  }

  .toggle-btn.deactivate:hover { box-shadow: 0 8px 24px rgba(229,80,80,0.15); }

  .toggle-btn.loading { opacity: 0.6; pointer-events: none; }

  .btn-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: currentColor;
    flex-shrink: 0;
  }

  /* side stats */
  .stats-col {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .stat-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px 22px;
    position: relative;
    overflow: hidden;
  }

  .stat-card::after {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 3px; height: 100%;
  }

  .stat-card.green::after { background: var(--on); }
  .stat-card.red::after   { background: var(--off); }
  .stat-card.blue::after  { background: var(--accent); }

  .stat-label {
    font-size: 10px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 8px;
  }

  .stat-val {
    font-family: var(--display);
    font-size: 28px;
    font-weight: 700;
    line-height: 1;
  }

  .stat-card.green .stat-val { color: var(--on); }
  .stat-card.red   .stat-val { color: var(--off); }
  .stat-card.blue  .stat-val { color: var(--accent); }

  /* info strip */
  .info-strip {
    margin-top: 20px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 18px 22px;
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 12px;
    color: var(--muted);
    grid-column: 1 / -1;
  }

  .info-strip code {
    background: var(--raised);
    border: 1px solid var(--border);
    border-radius: 5px;
    padding: 2px 8px;
    color: var(--accent);
    font-family: var(--mono);
    font-size: 11px;
  }

  /* ── About page ──────────────────────────────────────────────────── */
  .about-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 36px;
    max-width: 560px;
  }

  .about-name {
    font-family: var(--display);
    font-size: 32px;
    font-weight: 800;
    color: var(--text);
    margin-bottom: 4px;
  }

  .about-name span { color: var(--accent); }

  .about-ver {
    font-size: 11px;
    color: var(--muted);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 24px;
  }

  .about-body {
    font-size: 13px;
    color: var(--muted);
    line-height: 1.8;
  }

  .about-body a { color: var(--accent); text-decoration: none; }

  .divider {
    height: 1px;
    background: var(--border);
    margin: 24px 0;
  }

  .kv-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 0;
    border-bottom: 1px solid var(--border);
    font-size: 12px;
  }

  .kv-row:last-child { border-bottom: none; }
  .kv-key { color: var(--muted); }
  .kv-val { color: var(--text); font-family: var(--mono); }
</style>
</head>
<body>

<!-- ── Loading screen ─────────────────────────────────── -->
<div id="loader">
  <div class="loader-wordmark">Unblock<span>R</span></div>
  <div class="loader-sub">Connecting to server</div>
  <div class="progress-track">
    <div class="progress-fill" id="prog"></div>
  </div>
  <div class="loader-status" id="loader-status">Initialising...</div>
</div>

<!-- ── Error screen ───────────────────────────────────── -->
<div id="error-screen">
  <div class="error-icon">⚠</div>
  <div class="error-title">Server Unreachable</div>
  <div class="error-sub">
    Could not connect to the UnblockR server at<br>
    <code style="background:rgba(229,80,80,0.1);border-color:rgba(229,80,80,0.3);color:var(--off);padding:3px 10px;border-radius:5px;font-family:var(--mono);font-size:12px;" id="err-addr"></code><br><br>
    The server may be offline or you may not be on the correct network.
  </div>
  <button class="retry-btn" onclick="retryConnection()">↺ &nbsp;Retry Connection</button>
</div>

<!-- ── App ────────────────────────────────────────────── -->
<div id="app">
  <div class="titlebar">
    <div class="wordmark">Unblock<span>R</span></div>
    <div class="titlebar-right">
      <div class="server-pill">
        <div class="dot" id="server-dot"></div>
        <span id="server-addr">—</span>
      </div>
      <button class="close-btn" onclick="closeApp()">✕</button>
    </div>
  </div>

  <div class="body">
    <div class="sidebar">
      <div class="nav-item active" data-page="main">
        <span class="nav-icon">⬡</span> Dashboard
      </div>
      <div class="nav-item" data-page="about">
        <span class="nav-icon">◈</span> About
      </div>
      <div class="sidebar-bottom">
        <div class="version-tag">UnblockR v<span id="ver-tag">—</span></div>
      </div>
    </div>

    <div class="content">

      <!-- Dashboard -->
      <div class="page active" id="page-main">
        <div class="main-grid">

          <div class="toggle-card" id="toggle-card">
            <div class="status-label">Proxy Status</div>
            <div class="status-value off" id="status-val">INACTIVE</div>
            <div class="status-desc" id="status-desc">
              Traffic is routing directly. Click to activate UnblockR.
            </div>
            <button class="toggle-btn activate" id="toggle-btn" onclick="toggleProxy()">
              <span class="btn-dot"></span>
              <span id="toggle-label">Activate Proxy</span>
            </button>
          </div>

          <div class="stats-col">
            <div class="stat-card green">
              <div class="stat-label">Allowed</div>
              <div class="stat-val" id="stat-allowed">—</div>
            </div>
            <div class="stat-card red">
              <div class="stat-label">Blocked</div>
              <div class="stat-val" id="stat-blocked">—</div>
            </div>
            <div class="stat-card blue">
              <div class="stat-label">Filter size</div>
              <div class="stat-val" id="stat-domains">—</div>
            </div>
          </div>

          <div class="info-strip">
            <span>⬡</span>
            <span>Server: <code id="info-addr">—</code></span>
            &nbsp;·&nbsp;
            <span>Proxy covers all WinINet apps (Chrome, Edge, Discord, Steam)</span>
          </div>

        </div>
      </div>

      <!-- About -->
      <div class="page" id="page-about">
        <div class="about-card">
          <div class="about-name">Unblock<span>R</span></div>
          <div class="about-ver">Version <span id="about-ver">—</span></div>
          <div class="about-body">
            UnblockR routes your traffic through a filtering proxy server,
            blocking adult content, gambling, malware, and other inappropriate sites
            across all apps on your device — not just the browser.
          </div>
          <div class="divider"></div>
          <div class="kv-row">
            <span class="kv-key">Server</span>
            <span class="kv-val" id="about-server">—</span>
          </div>
          <div class="kv-row">
            <span class="kv-key">Filter</span>
            <span class="kv-val">StevenBlack hosts + custom blacklist</span>
          </div>
          <div class="kv-row">
            <span class="kv-key">Coverage</span>
            <span class="kv-val">HTTP + HTTPS (domain level)</span>
          </div>
          <div class="kv-row">
            <span class="kv-key">Safe search</span>
            <span class="kv-val">Google · Bing · YouTube · DDG · Yahoo</span>
          </div>
          <div class="kv-row">
            <span class="kv-key">Built by</span>
            <span class="kv-val">396abc</span>
          </div>
        </div>
      </div>

    </div>
  </div>
</div>

<script>
  // ── State ───────────────────────────────────────────────────────────
  let serverOnline  = false;
  let proxyActive   = false;
  let appVersion    = '—';
  let proxyAddr     = '—';

  // ── Loader helpers ──────────────────────────────────────────────────
  function setProgress(pct, msg) {
    document.getElementById('prog').style.width = pct + '%';
    document.getElementById('loader-status').textContent = msg;
  }

  function showError() {
    document.getElementById('err-addr').textContent = proxyAddr || '—';
    document.getElementById('loader').classList.add('fade-out');
    setTimeout(() => {
      document.getElementById('loader').style.display = 'none';
      document.getElementById('error-screen').classList.add('visible');
    }, 500);
  }

  function showApp() {
    document.getElementById('loader').classList.add('fade-out');
    setTimeout(() => {
      document.getElementById('loader').style.display = 'none';
      document.getElementById('app').classList.add('visible');
    }, 500);
  }

  // ── Boot sequence ───────────────────────────────────────────────────
  async function boot() {
    setProgress(15, 'Connecting to Python bridge...');
    await sleep(300);

    setProgress(35, 'Reaching server...');
    let result;
    try {
      result = await pywebview.api.ping_server();
    } catch(e) {
      showError();
      return;
    }

    proxyAddr   = result.proxy_addr;
    appVersion  = result.version;
    serverOnline = result.online;
    proxyActive  = result.proxy_active;

    setProgress(70, 'Verifying connection...');
    await sleep(400);

    if (!serverOnline) {
      setProgress(100, 'Server unreachable.');
      await sleep(400);
      showError();
      return;
    }

    setProgress(100, 'Connected.');
    await sleep(350);

    applyState(result);
    showApp();
  }

  // ── Apply state to UI ───────────────────────────────────────────────
  function applyState(result) {
    serverOnline = result.online;
    proxyActive  = result.proxy_active;
    const stats  = result.stats || {};

    // server pill
    const dot = document.getElementById('server-dot');
    dot.className = 'dot' + (serverOnline ? '' : ' off');
    document.getElementById('server-addr').textContent = proxyAddr;

    // version
    document.getElementById('ver-tag').textContent    = appVersion;
    document.getElementById('about-ver').textContent  = appVersion;
    document.getElementById('about-server').textContent = proxyAddr;
    document.getElementById('info-addr').textContent  = proxyAddr;

    // toggle card
    const card  = document.getElementById('toggle-card');
    const val   = document.getElementById('status-val');
    const desc  = document.getElementById('status-desc');
    const btn   = document.getElementById('toggle-btn');
    const label = document.getElementById('toggle-label');

    if (proxyActive) {
      card.className = 'toggle-card on';
      val.className  = 'status-value on';
      val.textContent = 'ACTIVE';
      desc.textContent = 'All system traffic is routed through UnblockR.';
      btn.className  = 'toggle-btn deactivate';
      label.textContent = 'Deactivate Proxy';
    } else {
      card.className = 'toggle-card';
      val.className  = 'status-value off';
      val.textContent = 'INACTIVE';
      desc.textContent = 'Traffic is routing directly. Click to activate UnblockR.';
      btn.className  = 'toggle-btn activate';
      label.textContent = 'Activate Proxy';
    }

    // stats
    function fmt(n) {
      if (!n && n !== 0) return '—';
      if (n >= 1000000) return (n/1000000).toFixed(1)+'M';
      if (n >= 1000)    return (n/1000).toFixed(1)+'K';
      return String(n);
    }

    document.getElementById('stat-allowed').textContent  = fmt(stats.allowed);
    document.getElementById('stat-blocked').textContent  = fmt(stats.blocked);
    document.getElementById('stat-domains').textContent  = fmt(stats.domains_in_blocklist);
  }

  // ── Toggle proxy ────────────────────────────────────────────────────
  async function toggleProxy() {
    const btn = document.getElementById('toggle-btn');
    const lbl = document.getElementById('toggle-label');
    btn.classList.add('loading');
    lbl.textContent = 'Applying...';

    try {
      const result = await pywebview.api.toggle_proxy();
      proxyActive = result.proxy_active;
      // Refresh full state
      const state = await pywebview.api.get_state();
      applyState(state);
    } catch(e) {
      lbl.textContent = 'Error';
      setTimeout(() => applyState({ online: serverOnline, proxy_active: proxyActive, stats: {} }), 1500);
    }

    btn.classList.remove('loading');
  }

  // ── Retry ────────────────────────────────────────────────────────────
  async function retryConnection() {
    const btn = document.querySelector('.retry-btn');
    btn.textContent = 'Checking...';
    btn.style.pointerEvents = 'none';

    try {
      const result = await pywebview.api.retry_connection();
      if (result.online) {
        document.getElementById('error-screen').classList.remove('visible');
        proxyAddr   = result.proxy_addr || proxyAddr;
        serverOnline = true;
        proxyActive  = result.proxy_active;
        applyState(result);
        document.getElementById('app').classList.add('visible');
      } else {
        btn.textContent = '✕  Still offline — Retry';
        btn.style.pointerEvents = '';
      }
    } catch(e) {
      btn.textContent = '✕  Failed — Retry';
      btn.style.pointerEvents = '';
    }
  }

  // ── Navigation ───────────────────────────────────────────────────────
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
      document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
      document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
      item.classList.add('active');
      document.getElementById('page-' + item.dataset.page).classList.add('active');
    });
  });

  // ── Close ────────────────────────────────────────────────────────────
  function closeApp() {
    if (window.pywebview) pywebview.api.close();
  }

  // ── Helpers ──────────────────────────────────────────────────────────
  function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

  // ── Auto-refresh stats every 10s ────────────────────────────────────
  setInterval(async () => {
    if (!serverOnline) return;
    try {
      const s = await pywebview.api.get_state();
      applyState(s);
    } catch(e) {}
  }, 10000);

  // ── Start ────────────────────────────────────────────────────────────
  window.addEventListener('pywebviewready', boot);
</script>
</body>
</html>"""

# ── Entry point ────────────────────────────────────────────────────────────────
settings = load_settings()
api      = API()

window = webview.create_window(
    "UnblockR",
    html=HTML,
    js_api=api,
    x=settings["window"].get("x", 120),
    y=settings["window"].get("y", 120),
    width=settings["window"].get("w", 940),
    height=settings["window"].get("h", 620),
    resizable=True,
    frameless=True,
    easy_drag=True,
    background_color="#070a0f",
)

webview.start(debug=False)
