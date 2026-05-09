#!/usr/bin/env python3
"""
UnblockR - updater.py
Checks for and applies updates to the UnblockR client.
Launched via updater_launcher.vbs from the main app.
"""

import os
import sys
import json
import time
import base64
import logging
import threading
import subprocess
import urllib.request
from pathlib import Path

try:
    import webview
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pywebview", "-q"])
    import webview

# ── Config ─────────────────────────────────────────────────────────────────────
APP_DIR   = Path(os.path.dirname(os.path.abspath(__file__)))
ICON_PATH = APP_DIR / "UnblockR.ico"
LOGO_PATH = APP_DIR / "UnblockR.png"

REPO_BASE = "https://github.com/396abc/UnblockR/raw/refs/heads/main"
LOGO_URL  = "https://raw.githubusercontent.com/396abc/UnblockR/main/UnblockR.png"

FILES = {
    "main.py":              f"{REPO_BASE}/main.py",
    "updater.py":           f"{REPO_BASE}/updater.py",
    "launcher.vbs":         f"{REPO_BASE}/launcher.vbs",
    "updater_launcher.vbs": f"{REPO_BASE}/updater_launcher.vbs",
    "UnblockR.ico":         f"{REPO_BASE}/UnblockR.ico",
    "UnblockR.png":         LOGO_URL,
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("UnblockR.Updater")

# ── Helpers ────────────────────────────────────────────────────────────────────
def logo_b64():
    if LOGO_PATH.exists():
        with open(LOGO_PATH, "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode()
    return ""

def get_local_version():
    main = APP_DIR / "main.py"
    if not main.exists():
        return "unknown"
    for line in main.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.strip().startswith("VERSION"):
            try:
                return line.split("=")[1].strip().strip("\"'")
            except Exception:
                pass
    return "unknown"

def fetch_remote_version():
    try:
        ts  = int(time.time())
        req = urllib.request.urlopen(f"{REPO_BASE}/main.py?t={ts}", timeout=15)
        for line in req.read().decode("utf-8", errors="ignore").splitlines():
            if line.strip().startswith("VERSION"):
                return line.split("=")[1].strip().strip("\"'")
    except Exception as e:
        log.warning(f"fetch_remote_version: {e}")
    return None

def download_file(url, dest: Path, progress_cb=None):
    try:
        req = urllib.request.urlopen(url, timeout=20)
        total = int(req.headers.get("Content-Length", 0))
        done  = 0
        data  = b""
        while True:
            chunk = req.read(8192)
            if not chunk:
                break
            data += chunk
            done += len(chunk)
            if progress_cb and total:
                progress_cb(done / total)
        dest.write_bytes(data)
        return True
    except Exception as e:
        log.error(f"download_file {url}: {e}")
        return False

# ── API ────────────────────────────────────────────────────────────────────────
class UpdaterAPI:
    def __init__(self):
        self._window = None

    def startup(self):
        local   = get_local_version()
        remote  = fetch_remote_version()
        update  = remote is not None and remote != local
        return {
            "logo":           logo_b64(),
            "local_version":  local,
            "remote_version": remote or "unavailable",
            "update_available": update,
        }

    def perform_update(self):
        """Download all files, report progress to JS."""
        def run():
            names  = list(FILES.keys())
            total  = len(names)
            errors = []

            for i, name in enumerate(names):
                url  = FILES[name]
                dest = APP_DIR / name
                msg  = f"Downloading {name}..."
                self._js(f'setProgress({int((i/total)*90)}, "{msg}")')
                log.info(msg)

                ok = download_file(url, dest)
                if not ok:
                    errors.append(name)
                    self._js(f'setProgress({int((i/total)*90)}, "Warning: {name} failed, skipping...")')
                    time.sleep(0.4)
                    continue

                time.sleep(0.15)

            if errors:
                self._js(f'setProgress(90, "Some files failed: {", ".join(errors)}")')
                time.sleep(0.8)

            new_ver = get_local_version()
            self._js(f'setProgress(100, "Done — UnblockR {new_ver}")')
            time.sleep(1.2)
            self._js('updateComplete()')

        t = threading.Thread(target=run, daemon=True)
        t.start()
        return {"started": True}

    def launch_main(self):
        vbs = APP_DIR / "launcher.vbs"
        if vbs.exists():
            subprocess.Popen(["wscript.exe", str(vbs)], shell=False)
        else:
            subprocess.Popen([sys.executable, str(APP_DIR / "main.py")], shell=False)
        time.sleep(0.5)
        os._exit(0)

    def close(self):
        os._exit(0)

    def _js(self, code):
        try:
            if self._window:
                self._window.evaluate_js(code)
        except Exception:
            pass

# ── HTML ───────────────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>UnblockR Updater</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@600;700;800&display=swap" rel="stylesheet">
<style>
  :root {
    --bg:      #070a0f;
    --surface: #0d1219;
    --raised:  #121820;
    --border:  #1e2a38;
    --text:    #c8d8e8;
    --muted:   #4a6070;
    --on:      #00e5a0;
    --off:     #e55050;
    --accent:  #3d9eff;
    --mono:    'DM Mono', monospace;
    --display: 'Syne', sans-serif;
  }
  *, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }
  body {
    font-family: var(--mono);
    background: var(--bg); color: var(--text);
    height: 100vh; overflow: hidden;
    display: flex; flex-direction: column;
    user-select: none;
  }
  body::after {
    content: ''; position: fixed; inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");
    pointer-events: none; z-index: 999; opacity: 0.35;
  }

  /* titlebar */
  .titlebar {
    height: 46px; background: var(--surface);
    border-bottom: 1px solid var(--border);
    display: flex; align-items: center;
    justify-content: space-between;
    padding: 0 16px; flex-shrink: 0;
    -webkit-app-region: drag;
  }
  .titlebar-left { display:flex; align-items:center; gap:8px; -webkit-app-region:no-drag; }
  .titlebar-left img { width:22px; height:22px; object-fit:contain; }
  .titlebar-word { font-family:var(--display); font-size:15px; font-weight:800; }
  .titlebar-word .r { color:var(--accent); }
  .titlebar-sub { font-size:11px; color:var(--muted); margin-left:6px; }
  .close-btn {
    -webkit-app-region: no-drag;
    width:26px; height:26px; background:transparent;
    border:1px solid var(--border); border-radius:6px;
    color:var(--muted); font-size:14px; cursor:pointer;
    display:flex; align-items:center; justify-content:center;
    transition:all 0.15s;
  }
  .close-btn:hover { background:rgba(229,80,80,0.15); border-color:var(--off); color:var(--off); }

  /* main content */
  .body {
    flex:1; display:flex; align-items:center;
    justify-content:center; padding:32px;
  }

  .card {
    background: var(--surface); border:1px solid var(--border);
    border-radius:16px; padding:36px 40px;
    width:100%; max-width:420px; text-align:center;
    opacity:0; transform:translateY(12px);
    transition: opacity 0.4s ease, transform 0.4s ease;
  }
  .card.visible { opacity:1; transform:translateY(0); }

  .card-logo {
    width:64px; height:64px; object-fit:contain;
    margin:0 auto 20px;
    animation: float 3s ease-in-out infinite;
  }
  @keyframes float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-6px)} }

  .card-title {
    font-family:var(--display); font-size:22px; font-weight:800;
    color:var(--text); margin-bottom:4px;
  }
  .card-title .r { color:var(--accent); }

  .card-sub { font-size:11px; color:var(--muted); letter-spacing:0.08em; text-transform:uppercase; margin-bottom:28px; }

  /* version row */
  .ver-row {
    display:flex; gap:12px; margin-bottom:24px;
  }
  .ver-box {
    flex:1; background:var(--raised); border:1px solid var(--border);
    border-radius:10px; padding:14px;
  }
  .ver-label { font-size:10px; color:var(--muted); letter-spacing:0.1em; text-transform:uppercase; margin-bottom:6px; }
  .ver-val { font-family:var(--display); font-size:18px; font-weight:700; color:var(--text); }

  /* status badge */
  .badge {
    display:inline-flex; align-items:center; gap:6px;
    padding:6px 14px; border-radius:100px;
    font-size:12px; font-weight:500; margin-bottom:24px;
  }
  .badge.up-to-date { background:rgba(0,229,160,0.1); border:1px solid rgba(0,229,160,0.25); color:var(--on); }
  .badge.update-avail { background:rgba(61,158,255,0.1); border:1px solid rgba(61,158,255,0.3); color:var(--accent); animation:pulse 2s infinite; }
  .badge.updating { background:rgba(61,158,255,0.08); border:1px solid rgba(61,158,255,0.2); color:var(--muted); }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.6} }
  .badge-dot { width:6px; height:6px; border-radius:50%; background:currentColor; }

  /* progress */
  .progress-wrap { margin-bottom:24px; text-align:left; }
  .progress-track {
    height:4px; background:var(--border); border-radius:2px;
    overflow:hidden; margin-bottom:10px;
  }
  .progress-fill {
    height:100%;
    background:linear-gradient(90deg, var(--accent), var(--on));
    border-radius:2px; width:0%;
    transition:width 0.4s cubic-bezier(0.4,0,0.2,1);
  }
  .progress-msg { font-size:11px; color:var(--muted); }
  .progress-pct { font-size:11px; color:var(--accent); float:right; }

  /* buttons */
  .btns { display:flex; gap:10px; justify-content:center; }
  .btn {
    padding:12px 24px; border-radius:9px;
    font-family:var(--mono); font-size:12px; font-weight:500;
    cursor:pointer; transition:all 0.2s;
    border:1px solid var(--border);
  }
  .btn-primary {
    background:rgba(61,158,255,0.12); border-color:rgba(61,158,255,0.35);
    color:var(--accent);
  }
  .btn-primary:hover { background:rgba(61,158,255,0.2); transform:translateY(-1px); }
  .btn-secondary { background:var(--raised); color:var(--muted); }
  .btn-secondary:hover { color:var(--text); transform:translateY(-1px); }
  .btn:disabled { opacity:0.4; pointer-events:none; }

  .spinner {
    width:18px; height:18px;
    border:2px solid var(--border);
    border-top-color:var(--accent);
    border-radius:50%;
    animation:spin 0.8s linear infinite;
    display:inline-block; vertical-align:middle; margin-right:6px;
  }
  @keyframes spin { to { transform:rotate(360deg); } }
</style>
</head>
<body>

<div class="titlebar">
  <div class="titlebar-left">
    <img id="title-logo" src="" alt="">
    <div class="titlebar-word">Unblock<span class="r">R</span></div>
    <span class="titlebar-sub">Updater</span>
  </div>
  <button class="close-btn" onclick="doClose()">&#x2715;</button>
</div>

<div class="body">
  <div class="card" id="card">
    <img class="card-logo" id="card-logo" src="" alt="UnblockR">
    <div class="card-title">Unblock<span class="r">R</span></div>
    <div class="card-sub">Software Update</div>

    <div class="ver-row">
      <div class="ver-box">
        <div class="ver-label">Installed</div>
        <div class="ver-val" id="local-ver">—</div>
      </div>
      <div class="ver-box">
        <div class="ver-label">Latest</div>
        <div class="ver-val" id="remote-ver">—</div>
      </div>
    </div>

    <div class="badge updating" id="badge">
      <div class="badge-dot"></div>
      <span id="badge-text">Checking...</span>
    </div>

    <div class="progress-wrap" id="prog-wrap" style="display:none">
      <div>
        <span class="progress-msg" id="prog-msg">Starting...</span>
        <span class="progress-pct" id="prog-pct">0%</span>
      </div>
      <div style="clear:both;margin-top:6px;">
        <div class="progress-track"><div class="progress-fill" id="prog-fill"></div></div>
      </div>
    </div>

    <div class="btns" id="btns">
      <button class="btn btn-secondary" onclick="doClose()">Close</button>
    </div>
  </div>
</div>

<script>
  function applyLogo(src) {
    if (!src) return;
    ['title-logo','card-logo'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.src = src;
    });
  }

  function setBadge(cls, txt) {
    const b = document.getElementById('badge');
    b.className = 'badge ' + cls;
    document.getElementById('badge-text').textContent = txt;
  }

  function setButtons(html) {
    document.getElementById('btns').innerHTML = html;
  }

  function setProgress(pct, msg) {
    document.getElementById('prog-wrap').style.display = 'block';
    document.getElementById('prog-fill').style.width = pct + '%';
    document.getElementById('prog-msg').textContent = msg;
    document.getElementById('prog-pct').textContent = pct + '%';
  }

  function updateComplete() {
    setBadge('up-to-date', 'Update complete');
    setButtons('<button class="btn btn-primary" onclick="launchMain()">Launch UnblockR</button>');
  }

  async function boot() {
    let result;
    try { result = await pywebview.api.startup(); }
    catch(e) { setBadge('updating','Error loading'); return; }

    applyLogo(result.logo);
    document.getElementById('local-ver').textContent  = result.local_version;
    document.getElementById('remote-ver').textContent = result.remote_version;
    document.getElementById('card').classList.add('visible');

    if (result.remote_version === 'unavailable') {
      setBadge('up-to-date', 'Could not reach server');
      setButtons('<button class="btn btn-secondary" onclick="launchMain()">Launch anyway</button><button class="btn btn-secondary" onclick="doClose()">Close</button>');
      return;
    }

    if (!result.update_available) {
      setBadge('up-to-date', 'You are up to date');
      setButtons('<button class="btn btn-primary" onclick="launchMain()">Launch UnblockR</button><button class="btn btn-secondary" onclick="doClose()">Close</button>');
      return;
    }

    setBadge('update-avail', 'Update available');
    setButtons(
      '<button class="btn btn-primary" onclick="startUpdate()">Update Now</button>' +
      '<button class="btn btn-secondary" onclick="launchMain()">Skip</button>'
    );
  }

  async function startUpdate() {
    setBadge('updating', 'Updating...');
    setButtons('<button class="btn btn-secondary" disabled><span class="spinner"></span>Updating...</button>');
    setProgress(0, 'Starting...');
    await pywebview.api.perform_update();
  }

  async function launchMain() {
    setBadge('updating', 'Launching...');
    setButtons('<button class="btn btn-secondary" disabled>Launching...</button>');
    await pywebview.api.launch_main();
  }

  function doClose() { if (window.pywebview) pywebview.api.close(); }

  window.addEventListener('pywebviewready', boot);
</script>
</body>
</html>"""

# ── Entry point ────────────────────────────────────────────────────────────────
api    = UpdaterAPI()
icon   = str(ICON_PATH) if ICON_PATH.exists() else None

window = webview.create_window(
    "UnblockR Updater",
    html=HTML,
    js_api=api,
    width=620,
    height=620,
    resizable=False,
    frameless=True,
    easy_drag=True,
    background_color="#070a0f",
)

api._window = window
webview.start(icon=icon, debug=False)
