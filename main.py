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
import subprocess
import urllib.request
from pathlib import Path
import base64

try:
    import webview
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pywebview", "-q"])
    import webview

# ── Config ─────────────────────────────────────────────────────────────────────
PROXY_IP    = "192.168.0.193"
PROXY_PORT  = 8080
PROXY_ADDR  = f"{PROXY_IP}:{PROXY_PORT}"
VERSION     = "1.0.0"
APP_DIR     = Path(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_FILE = APP_DIR / "settings.json"
ICON_PATH   = APP_DIR / "UnblockR.ico"
LOGO_PATH   = APP_DIR / "UnblockR.png"
ICON_URL    = "https://github.com/396abc/UnblockR/raw/refs/heads/main/UnblockR.ico"
LOGO_URL    = "https://raw.githubusercontent.com/396abc/UnblockR/main/UnblockR.png"

REG_PATH     = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
PROXY_BYPASS = "localhost;127.*;192.168.*;<local>"
DASH_URL     = f"http://{PROXY_IP}:8081/api/stats"

# ── Download assets if missing ─────────────────────────────────────────────────
def ensure_assets():
    for url, path in [(ICON_URL, ICON_PATH), (LOGO_URL, LOGO_PATH)]:
        if not path.exists():
            try:
                urllib.request.urlretrieve(url, path)
            except Exception:
                pass

ensure_assets()

def logo_b64():
    if LOGO_PATH.exists():
        with open(LOGO_PATH, "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode()
    return ""

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

# ── Connectivity check (only used when toggling ON) ───────────────────────────
def check_server(timeout=4):
    try:
        req = urllib.request.urlopen(DASH_URL, timeout=timeout)
        data = json.loads(req.read())
        return True, data
    except Exception:
        return False, {}

# ── API ────────────────────────────────────────────────────────────────────────
class API:
    def __init__(self):
        self.settings = load_settings()

    def startup(self):
        """Called on app open — does NOT check server, just returns local state."""
        return {
            "proxy_active": proxy_is_active(),
            "version":      VERSION,
            "logo":         logo_b64(),
        }

    def toggle_proxy(self):
        """Toggle proxy. If turning ON, check server first."""
        if proxy_is_active():
            disable_proxy()
            return {"proxy_active": False, "online": None, "stats": {}, "error": None}
        else:
            ok, data = check_server(timeout=5)
            if not ok:
                return {"proxy_active": False, "online": False, "stats": {}, "error": "server_unreachable"}
            enable_proxy()
            return {"proxy_active": True, "online": True, "stats": data, "error": None}

    def get_stats(self):
        """Refresh stats from server — only called when proxy is already active."""
        ok, data = check_server(timeout=3)
        return {"online": ok, "stats": data}

    def close(self):
        try:
            pos  = window.get_position()
            size = window.get_size()
            s = self.settings
            s["window"] = {"x": pos[0], "y": pos[1], "w": size[0], "h": size[1]}
            save_settings(s)
        except Exception:
            pass
        os._exit(0)

# ── HTML ───────────────────────────────────────────────────────────────────────
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

  body::after {
    content: '';
    position: fixed; inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");
    pointer-events: none; z-index: 999; opacity: 0.35;
  }

  /* ── Loader ── */
  #loader {
    position: fixed; inset: 0; background: var(--bg);
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    z-index: 998;
    transition: opacity 0.5s ease, transform 0.5s ease;
  }
  #loader.fade-out { opacity:0; transform:scale(1.02); pointer-events:none; }

  .loader-logo {
    width: 72px; height: 72px; object-fit: contain;
    margin-bottom: 20px;
    animation: float 3s ease-in-out infinite;
  }
  @keyframes float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-6px)} }

  .loader-wordmark {
    font-family: var(--display);
    font-size: 28px; font-weight: 800;
    color: var(--text); margin-bottom: 4px; letter-spacing: -0.5px;
  }
  .loader-wordmark .r { color: var(--accent); }

  .loader-sub {
    font-size: 11px; color: var(--muted);
    letter-spacing: 0.12em; text-transform: uppercase;
    margin-bottom: 40px;
  }

  .progress-track {
    width: 240px; height: 2px;
    background: var(--border); border-radius: 2px;
    overflow: hidden; margin-bottom: 16px;
  }
  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--accent), var(--on));
    border-radius: 2px; width: 0%;
    transition: width 0.4s cubic-bezier(0.4,0,0.2,1);
  }
  .loader-status { font-size: 11px; color: var(--muted); letter-spacing: 0.06em; min-height: 16px; }

  /* ── Error overlay (shown over app, not full screen) ── */
  #error-overlay {
    position: fixed; inset: 0; background: rgba(7,10,15,0.92);
    display: none; flex-direction: column;
    align-items: center; justify-content: center; z-index: 500;
    backdrop-filter: blur(4px);
  }
  #error-overlay.visible { display: flex; }

  .error-icon { font-size: 36px; margin-bottom: 16px; color: var(--off); }
  .error-title { font-family: var(--display); font-size: 20px; font-weight: 700; color: var(--off); margin-bottom: 10px; }
  .error-sub { font-size: 12px; color: var(--muted); text-align: center; line-height: 1.7; max-width: 300px; margin-bottom: 28px; }
  .error-actions { display: flex; gap: 12px; }
  .retry-btn {
    padding: 11px 28px;
    background: var(--off-dim); border: 1px solid var(--off);
    border-radius: 8px; color: var(--off);
    font-family: var(--mono); font-size: 12px;
    cursor: pointer; transition: all 0.2s;
  }
  .retry-btn:hover { background: var(--off); color: #fff; }
  .dismiss-btn {
    padding: 11px 20px;
    background: transparent; border: 1px solid var(--border2);
    border-radius: 8px; color: var(--muted);
    font-family: var(--mono); font-size: 12px;
    cursor: pointer; transition: all 0.2s;
  }
  .dismiss-btn:hover { color: var(--text); border-color: var(--text); }

  /* ── App ── */
  #app { display: flex; flex-direction: column; height: 100vh; opacity: 0; transition: opacity 0.4s ease; }
  #app.visible { opacity: 1; }

  /* titlebar */
  .titlebar {
    height: 50px; background: var(--surface);
    border-bottom: 1px solid var(--border);
    display: flex; align-items: center;
    justify-content: space-between;
    padding: 0 18px 0 16px;
    -webkit-app-region: drag; flex-shrink: 0;
  }

  .titlebar-left {
    display: flex; align-items: center; gap: 10px;
    -webkit-app-region: no-drag;
  }
  .titlebar-left img { width: 26px; height: 26px; object-fit: contain; }
  .titlebar-wordmark {
    font-family: var(--display); font-size: 17px; font-weight: 800;
    color: var(--text); letter-spacing: -0.3px;
  }
  .titlebar-wordmark .r { color: var(--accent); }

  .titlebar-right {
    display: flex; align-items: center; gap: 14px;
    -webkit-app-region: no-drag;
  }

  .server-pill {
    display: flex; align-items: center; gap: 6px;
    padding: 4px 10px;
    background: var(--raised); border: 1px solid var(--border);
    border-radius: 100px; font-size: 11px; color: var(--muted);
  }
  .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--muted); }
  .dot.on  { background: var(--on); animation: blink 2.5s infinite; }
  .dot.off { background: var(--off); }
  @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }

  .close-btn {
    width: 26px; height: 26px; background: transparent;
    border: 1px solid var(--border); border-radius: 6px;
    color: var(--muted); font-size: 14px; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: all 0.15s;
  }
  .close-btn:hover { background: var(--off-dim); border-color: var(--off); color: var(--off); }

  /* layout */
  .body { flex: 1; display: flex; overflow: hidden; }

  .sidebar {
    width: 190px; background: var(--surface);
    border-right: 1px solid var(--border);
    padding: 20px 0; flex-shrink: 0;
    display: flex; flex-direction: column; gap: 2px;
  }
  .nav-item {
    display: flex; align-items: center; gap: 10px;
    padding: 10px 18px; font-size: 12px; color: var(--muted);
    cursor: pointer; border-left: 2px solid transparent;
    transition: all 0.15s; letter-spacing: 0.04em;
  }
  .nav-item:hover { color: var(--text); background: var(--raised); }
  .nav-item.active { color: var(--accent); border-left-color: var(--accent); background: var(--accent-d); }
  .nav-icon { font-size: 13px; width: 16px; text-align: center; }

  .sidebar-bottom { margin-top: auto; padding: 14px 18px; border-top: 1px solid var(--border); }
  .version-tag { font-size: 10px; color: var(--muted); letter-spacing: 0.08em; }

  .content { flex: 1; overflow-y: auto; padding: 32px 36px; }
  .content::-webkit-scrollbar { width: 4px; }
  .content::-webkit-scrollbar-track { background: transparent; }
  .content::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }

  .page { display: none; animation: fadeUp 0.3s ease; }
  .page.active { display: block; }
  @keyframes fadeUp { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }

  /* ── Dashboard ── */
  .main-grid {
    display: grid;
    grid-template-columns: 1fr 240px;
    gap: 18px; align-items: start;
  }

  .toggle-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 14px; padding: 32px 32px 28px;
    position: relative; overflow: hidden; transition: border-color 0.3s;
  }
  .toggle-card::before {
    content: ''; position: absolute; top:0; left:0; right:0; height: 2px;
    background: linear-gradient(90deg, var(--accent), transparent);
    transition: background 0.4s;
  }
  .toggle-card.on::before { background: linear-gradient(90deg, var(--on), transparent); }
  .toggle-card.on { border-color: rgba(0,229,160,0.2); }

  .status-label { font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); margin-bottom: 10px; }

  .status-value {
    font-family: var(--display);
    font-size: 28px; font-weight: 800;
    line-height: 1; margin-bottom: 6px; transition: color 0.3s;
  }
  .status-value.on  { color: var(--on); }
  .status-value.off { color: var(--text); }

  .status-desc { font-size: 12px; color: var(--muted); margin-bottom: 28px; line-height: 1.6; }

  .toggle-btn {
    display: flex; align-items: center; gap: 12px;
    padding: 13px 24px; border-radius: 10px;
    border: 1px solid var(--border2); background: var(--raised);
    color: var(--text); font-family: var(--mono);
    font-size: 13px; font-weight: 500; cursor: pointer;
    transition: all 0.2s cubic-bezier(0.4,0,0.2,1);
    width: fit-content;
  }
  .toggle-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.3); }
  .toggle-btn.activate { border-color: rgba(0,229,160,0.4); background: var(--on-dim); color: var(--on); }
  .toggle-btn.activate:hover { box-shadow: 0 8px 24px rgba(0,229,160,0.15); }
  .toggle-btn.deactivate { border-color: rgba(229,80,80,0.4); background: var(--off-dim); color: var(--off); }
  .toggle-btn.deactivate:hover { box-shadow: 0 8px 24px rgba(229,80,80,0.15); }
  .toggle-btn.loading { opacity:0.6; pointer-events:none; }
  .btn-dot { width:8px; height:8px; border-radius:50%; background:currentColor; flex-shrink:0; }

  .stats-col { display: flex; flex-direction: column; gap: 10px; }
  .stat-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 10px; padding: 18px 20px;
    position: relative; overflow: hidden;
  }
  .stat-card::after { content:''; position:absolute; top:0; left:0; width:3px; height:100%; }
  .stat-card.green::after { background: var(--on); }
  .stat-card.red::after   { background: var(--off); }
  .stat-card.blue::after  { background: var(--accent); }
  .stat-label { font-size:10px; letter-spacing:0.1em; text-transform:uppercase; color:var(--muted); margin-bottom:6px; }
  .stat-val { font-family:var(--display); font-size:24px; font-weight:700; line-height:1; }
  .stat-card.green .stat-val { color: var(--on); }
  .stat-card.red   .stat-val { color: var(--off); }
  .stat-card.blue  .stat-val { color: var(--accent); }

  .info-strip {
    margin-top: 16px;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 10px; padding: 14px 18px;
    display: flex; align-items: center; gap: 8px;
    font-size: 11px; color: var(--muted); grid-column: 1 / -1;
  }
  .info-strip code {
    background: var(--raised); border: 1px solid var(--border);
    border-radius: 4px; padding: 1px 7px;
    color: var(--accent); font-family: var(--mono); font-size: 11px;
  }

  /* ── About ── */
  .about-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 14px; padding: 32px; max-width: 520px;
  }
  .about-header { display:flex; align-items:center; gap:16px; margin-bottom:6px; }
  .about-logo { width:48px; height:48px; object-fit:contain; }
  .about-name { font-family:var(--display); font-size:28px; font-weight:800; color:var(--text); }
  .about-name .r { color: var(--accent); }
  .about-ver { font-size:11px; color:var(--muted); letter-spacing:0.1em; text-transform:uppercase; margin-bottom:20px; }
  .about-body { font-size:13px; color:var(--muted); line-height:1.8; }
  .divider { height:1px; background:var(--border); margin:20px 0; }
  .kv-row { display:flex; justify-content:space-between; align-items:center; padding:9px 0; border-bottom:1px solid var(--border); font-size:12px; }
  .kv-row:last-child { border-bottom:none; }
  .kv-key { color:var(--muted); }
  .kv-val { color:var(--text); font-family:var(--mono); }
</style>
</head>
<body>

<!-- Loader -->
<div id="loader">
  <img class="loader-logo" id="loader-img" src="" alt="UnblockR">
  <div class="loader-wordmark">Unblock<span class="r">R</span></div>
  <div class="loader-sub">Starting up</div>
  <div class="progress-track"><div class="progress-fill" id="prog"></div></div>
  <div class="loader-status" id="loader-status">Initialising...</div>
</div>

<!-- Error overlay (shown when connect attempt fails) -->
<div id="error-overlay">
  <div class="error-icon">&#x26A0;</div>
  <div class="error-title">Server Unreachable</div>
  <div class="error-sub">
    Could not connect to the UnblockR server.<br><br>
    The server may be offline or you may not be on the correct network.
    The proxy has not been activated.
  </div>
  <div class="error-actions">
    <button class="retry-btn" onclick="retryToggle()">&#x21BA;&nbsp; Retry</button>
    <button class="dismiss-btn" onclick="dismissError()">Dismiss</button>
  </div>
</div>

<!-- App -->
<div id="app">
  <div class="titlebar">
    <div class="titlebar-left">
      <img id="title-img" src="" alt="">
      <div class="titlebar-wordmark">Unblock<span class="r">R</span></div>
    </div>
    <div class="titlebar-right">
      <div class="server-pill">
        <div class="dot" id="server-dot"></div>
        <span id="server-label">UnblockR Server</span>
      </div>
      <button class="close-btn" onclick="closeApp()">&#x2715;</button>
    </div>
  </div>

  <div class="body">
    <div class="sidebar">
      <div class="nav-item active" data-page="main">
        <span class="nav-icon">&#x2B21;</span> Dashboard
      </div>
      <div class="nav-item" data-page="about">
        <span class="nav-icon">&#x25C8;</span> About
      </div>
      <div class="sidebar-bottom">
        <div class="version-tag">v<span id="ver-tag">—</span></div>
      </div>
    </div>

    <div class="content">

      <!-- Dashboard -->
      <div class="page active" id="page-main">
        <div class="main-grid">
          <div class="toggle-card" id="toggle-card">
            <div class="status-label">Proxy Status</div>
            <div class="status-value off" id="status-val">INACTIVE</div>
            <div class="status-desc" id="status-desc">Traffic is routing directly. Click to activate UnblockR.</div>
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
            <span>&#x2B21;</span>
            <span>Connected to <code>UnblockR Server</code></span>
            &nbsp;·&nbsp;
            <span>Covers all WinINet apps (Chrome, Edge, Discord, Steam)</span>
          </div>
        </div>
      </div>

      <!-- About -->
      <div class="page" id="page-about">
        <div class="about-card">
          <div class="about-header">
            <img class="about-logo" id="about-img" src="" alt="UnblockR">
            <div class="about-name">Unblock<span class="r">R</span></div>
          </div>
          <div class="about-ver">Version <span id="about-ver">—</span></div>
          <div class="about-body">
            UnblockR routes your traffic through a filtering proxy server,
            blocking adult content, gambling, malware, and other inappropriate
            sites across all apps on your device.
          </div>
          <div class="divider"></div>
          <div class="kv-row"><span class="kv-key">Server</span><span class="kv-val">UnblockR Server</span></div>
          <div class="kv-row"><span class="kv-key">Filter</span><span class="kv-val">StevenBlack + custom blacklist</span></div>
          <div class="kv-row"><span class="kv-key">Coverage</span><span class="kv-val">HTTP + HTTPS (domain level)</span></div>
          <div class="kv-row"><span class="kv-key">Safe search</span><span class="kv-val">Google · Bing · YouTube · DDG · Yahoo</span></div>
          <div class="kv-row"><span class="kv-key">Built by</span><span class="kv-val">396abc</span></div>
        </div>
      </div>

    </div>
  </div>
</div>

<script>
  let proxyActive = false;
  let appVersion  = '—';
  let pendingToggle = false;

  function setProgress(pct, msg) {
    document.getElementById('prog').style.width = pct + '%';
    document.getElementById('loader-status').textContent = msg;
  }

  function applyLogo(src) {
    if (!src) return;
    ['loader-img','title-img','about-img'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.src = src;
    });
  }

  function showApp() {
    document.getElementById('loader').classList.add('fade-out');
    setTimeout(() => {
      document.getElementById('loader').style.display = 'none';
      document.getElementById('app').classList.add('visible');
    }, 500);
  }

  async function boot() {
    setProgress(30, 'Loading...');
    await sleep(200);
    setProgress(70, 'Applying settings...');

    let result;
    try {
      result = await pywebview.api.startup();
    } catch(e) {
      setProgress(100, 'Ready.');
      await sleep(200);
      showApp();
      return;
    }

    if (result.logo) applyLogo(result.logo);
    appVersion  = result.version;
    proxyActive = result.proxy_active;

    setProgress(100, 'Ready.');
    await sleep(250);
    applyState({ proxy_active: proxyActive, online: proxyActive, stats: {} });
    showApp();
  }

  function applyState(result) {
    proxyActive = result.proxy_active;
    const stats = result.stats || {};
    const online = result.online;

    document.getElementById('ver-tag').textContent   = appVersion;
    document.getElementById('about-ver').textContent = appVersion;

    // server dot — only lit when proxy is active and server confirmed reachable
    const dot = document.getElementById('server-dot');
    if (proxyActive && online) dot.className = 'dot on';
    else if (!proxyActive)     dot.className = 'dot';
    else                       dot.className = 'dot off';

    const card  = document.getElementById('toggle-card');
    const val   = document.getElementById('status-val');
    const desc  = document.getElementById('status-desc');
    const btn   = document.getElementById('toggle-btn');
    const label = document.getElementById('toggle-label');

    if (proxyActive) {
      card.className  = 'toggle-card on';
      val.className   = 'status-value on';
      val.textContent = 'ACTIVE';
      desc.textContent = 'All system traffic is routed through UnblockR.';
      btn.className   = 'toggle-btn deactivate';
      label.textContent = 'Deactivate Proxy';
    } else {
      card.className  = 'toggle-card';
      val.className   = 'status-value off';
      val.textContent = 'INACTIVE';
      desc.textContent = 'Traffic is routing directly. Click to activate UnblockR.';
      btn.className   = 'toggle-btn activate';
      label.textContent = 'Activate Proxy';
    }

    function fmt(n) {
      if (!n && n !== 0) return '—';
      if (n >= 1000000) return (n/1000000).toFixed(1)+'M';
      if (n >= 1000)    return (n/1000).toFixed(1)+'K';
      return String(n);
    }
    document.getElementById('stat-allowed').textContent = fmt(stats.allowed);
    document.getElementById('stat-blocked').textContent = fmt(stats.blocked);
    document.getElementById('stat-domains').textContent = fmt(stats.domains_in_blocklist);
  }

  async function toggleProxy() {
    const btn   = document.getElementById('toggle-btn');
    const label = document.getElementById('toggle-label');
    btn.classList.add('loading');

    const turningOn = !proxyActive;
    label.textContent = turningOn ? 'Connecting...' : 'Deactivating...';

    try {
      const result = await pywebview.api.toggle_proxy();
      if (result.error === 'server_unreachable') {
        showError();
      } else {
        applyState(result);
        // if now active, start polling stats
        if (result.proxy_active) startStatsPoll();
        else stopStatsPoll();
      }
    } catch(e) {
      label.textContent = 'Error';
      setTimeout(() => applyState({proxy_active: proxyActive, online: false, stats:{}}), 1500);
    }
    btn.classList.remove('loading');
  }

  function showError() {
    document.getElementById('error-overlay').classList.add('visible');
    pendingToggle = true;
  }

  function dismissError() {
    document.getElementById('error-overlay').classList.remove('visible');
    pendingToggle = false;
  }

  async function retryToggle() {
    const btn = document.querySelector('.retry-btn');
    btn.textContent = 'Checking...';
    btn.style.pointerEvents = 'none';
    try {
      const result = await pywebview.api.toggle_proxy();
      if (result.error === 'server_unreachable') {
        btn.textContent = 'Still offline — Retry';
        btn.style.pointerEvents = '';
      } else {
        dismissError();
        applyState(result);
        if (result.proxy_active) startStatsPoll();
      }
    } catch(e) {
      btn.textContent = 'Failed — Retry';
      btn.style.pointerEvents = '';
    }
  }

  // Stats polling — only runs while proxy is active
  let statsInterval = null;

  function startStatsPoll() {
    stopStatsPoll();
    statsInterval = setInterval(async () => {
      try {
        const s = await pywebview.api.get_stats();
        applyState({ proxy_active: proxyActive, online: s.online, stats: s.stats });
      } catch(e) {}
    }, 10000);
  }

  function stopStatsPoll() {
    if (statsInterval) { clearInterval(statsInterval); statsInterval = null; }
  }

  // Nav
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
      document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
      document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
      item.classList.add('active');
      document.getElementById('page-' + item.dataset.page).classList.add('active');
    });
  });

  function closeApp() { if (window.pywebview) pywebview.api.close(); }
  function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

  window.addEventListener('pywebviewready', boot);
</script>
</body>
</html>"""

# ── Entry point ────────────────────────────────────────────────────────────────
settings = load_settings()
api      = API()
icon     = str(ICON_PATH) if ICON_PATH.exists() else None

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

webview.start(icon=icon, debug=False)
