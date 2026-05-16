#!/usr/bin/env python3
"""
UnblockR - uninstall.py
Removes UnblockR from the system.
Refuses to uninstall if the proxy is active or disabler is on.
"""

import os
import sys
import json
import shutil
import ctypes
import winreg
import subprocess
import threading
from pathlib import Path

try:
    import webview
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pywebview", "-q"])
    import webview

APP_DIR = Path(os.environ["LOCALAPPDATA"]) / "UnblockR"
SETTINGS = APP_DIR / "settings.json"
START_MENU = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "UnblockR"

# HTML for the uninstaller GUI with custom titlebar
HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>UnblockR - Uninstaller</title>
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
    --accent:   #3d9eff;
    --accent-d: rgba(61,158,255,0.1);
    --error:    #e55050;
    --error-dim: rgba(229,80,80,0.12);
    --on:       #00e5a0;
    --mono:     'DM Mono', monospace;
    --display:  'Syne', sans-serif;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    font-family: var(--mono);
    background: var(--bg);
    color: var(--text);
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    user-select: none;
  }
  
  /* Custom Titlebar */
  .titlebar {
    height: 50px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 18px 0 16px;
    -webkit-app-region: drag;
    flex-shrink: 0;
  }
  .titlebar-left {
    display: flex;
    align-items: center;
    gap: 10px;
    -webkit-app-region: no-drag;
  }
  .titlebar-word {
    font-family: var(--display);
    font-size: 17px;
    font-weight: 800;
    color: var(--text);
    letter-spacing: -0.3px;
  }
  .titlebar-word .r {
    color: var(--accent);
  }
  .titlebar-right {
    display: flex;
    align-items: center;
    gap: 10px;
    -webkit-app-region: no-drag;
  }
  .close-btn {
    width: 26px;
    height: 26px;
    background: transparent;
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--muted);
    font-size: 14px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s;
  }
  .close-btn:hover {
    background: var(--error-dim);
    border-color: var(--error);
    color: var(--error);
  }
  
  /* Main Content */
  .main-content {
    flex: 1;
    overflow-y: auto;
    padding: 32px 36px;
  }
  .main-content::-webkit-scrollbar {
    width: 4px;
  }
  .main-content::-webkit-scrollbar-track {
    background: transparent;
  }
  .main-content::-webkit-scrollbar-thumb {
    background: var(--border2);
    border-radius: 2px;
  }
  
  .uninstall-card {
    max-width: 480px;
    margin: 0 auto;
    position: relative;
    animation: fadeIn 0.4s ease;
  }
  
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }
  
  .header {
    text-align: center;
    margin-bottom: 32px;
  }
  .title {
    font-family: var(--display);
    font-size: 28px;
    font-weight: 800;
    color: var(--text);
  }
  .title .r {
    color: var(--accent);
  }
  .subtitle {
    font-size: 11px;
    color: var(--muted);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-top: 6px;
  }
  
  .warning-box {
    background: var(--error-dim);
    border: 1px solid rgba(229,80,80,0.3);
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 24px;
  }
  .warning-title {
    font-size: 12px;
    font-weight: 600;
    color: var(--error);
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .warning-text {
    font-size: 11px;
    color: var(--muted);
    line-height: 1.6;
  }
  
  .info-box {
    background: var(--raised);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 24px;
  }
  .info-row {
    font-size: 11px;
    color: var(--muted);
    padding: 6px 0;
    display: flex;
    gap: 12px;
    font-family: var(--mono);
  }
  .info-label {
    font-weight: 600;
    color: var(--text);
    min-width: 80px;
  }
  .info-value {
    color: var(--accent);
    word-break: break-all;
  }
  
  .progress-section {
    margin-bottom: 24px;
    display: none;
  }
  .progress-section.visible {
    display: block;
  }
  .progress-header {
    display: flex;
    justify-content: space-between;
    font-size: 10px;
    color: var(--muted);
    margin-bottom: 8px;
  }
  .progress-bar {
    height: 4px;
    background: var(--border);
    border-radius: 4px;
    overflow: hidden;
  }
  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--accent), var(--on));
    border-radius: 4px;
    width: 0%;
    transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }
  .progress-status {
    font-size: 11px;
    color: var(--muted);
    margin-top: 10px;
    text-align: center;
  }
  
  .buttons {
    display: flex;
    gap: 12px;
    justify-content: center;
  }
  .btn {
    padding: 12px 28px;
    border-radius: 10px;
    font-family: var(--mono);
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    border: 1px solid var(--border2);
    background: var(--raised);
    color: var(--text);
  }
  .btn-cancel {
    background: transparent;
    border-color: var(--border2);
  }
  .btn-cancel:hover {
    border-color: var(--text);
    color: var(--text);
  }
  .btn-uninstall {
    background: var(--error-dim);
    border-color: rgba(229,80,80,0.4);
    color: var(--error);
  }
  .btn-uninstall:hover {
    background: rgba(229,80,80,0.2);
    transform: translateY(-1px);
  }
  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none;
  }
  
  .error-message {
    background: var(--error-dim);
    border: 1px solid rgba(229,80,80,0.3);
    border-radius: 10px;
    padding: 12px;
    margin-top: 16px;
    font-size: 11px;
    color: var(--error);
    text-align: center;
    display: none;
  }
  .error-message.visible {
    display: block;
  }
  
  .success-message {
    text-align: center;
    animation: fadeIn 0.3s ease;
  }
  .success-icon {
    font-size: 54px;
    margin-bottom: 16px;
  }
  .success-text {
    font-size: 13px;
    color: var(--on);
    margin-bottom: 20px;
  }
</style>
</head>
<body>
<div class="titlebar">
  <div class="titlebar-left">
    <div class="titlebar-word">Unblock<span class="r">R</span></div>
  </div>
  <div class="titlebar-right">
    <button class="close-btn" onclick="window.pywebview.api.close_window()">✕</button>
  </div>
</div>

<div class="main-content">
  <div class="uninstall-card">
    <div id="confirm-view">
      <div class="header">
        <div class="title">Unblock<span class="r">R</span></div>
        <div class="subtitle">Uninstaller</div>
      </div>
      
      <div class="warning-box">
        <div class="warning-title">⚠️ Warning</div>
        <div class="warning-text">This will permanently remove UnblockR from your system. All settings and data will be deleted.</div>
      </div>
      
      <div class="info-box">
        <div class="info-row"><span class="info-label">📍 Location:</span><span class="info-value" id="app-path">—</span></div>
        <div class="info-row"><span class="info-label">📁 Shortcuts:</span><span class="info-value" id="shortcut-path">—</span></div>
      </div>
      
      <div class="buttons">
        <button class="btn btn-cancel" id="cancel-btn">Cancel</button>
        <button class="btn btn-uninstall" id="uninstall-btn">Uninstall</button>
      </div>
    </div>
    
    <div id="progress-view" style="display:none">
      <div class="header">
        <div class="title">Unblock<span class="r">R</span></div>
        <div class="subtitle">Uninstalling...</div>
      </div>
      <div class="progress-section visible">
        <div class="progress-header">
          <span id="progress-action">Preparing...</span>
          <span id="progress-percent">0%</span>
        </div>
        <div class="progress-bar"><div class="progress-fill" id="progress-fill"></div></div>
        <div class="progress-status" id="progress-status">Initializing...</div>
      </div>
    </div>
    
    <div id="success-view" style="display:none">
      <div class="success-message">
        <div class="success-icon">✓</div>
        <div class="success-text">UnblockR has been removed successfully!</div>
        <div class="buttons">
          <button class="btn btn-cancel" id="close-btn">Close</button>
        </div>
      </div>
    </div>
    
    <div class="error-message" id="error-message"></div>
  </div>
</div>

<script>
  let windowRef = null;
  
  function updateProgress(percent, action, status) {
    const fill = document.getElementById('progress-fill');
    const percentEl = document.getElementById('progress-percent');
    const actionEl = document.getElementById('progress-action');
    const statusEl = document.getElementById('progress-status');
    if (fill) fill.style.width = percent + '%';
    if (percentEl) percentEl.textContent = percent + '%';
    if (actionEl) actionEl.textContent = action;
    if (statusEl) statusEl.textContent = status;
  }
  
  function showProgress() {
    document.getElementById('confirm-view').style.display = 'none';
    document.getElementById('progress-view').style.display = 'block';
    document.getElementById('success-view').style.display = 'none';
  }
  
  function showSuccess() {
    document.getElementById('confirm-view').style.display = 'none';
    document.getElementById('progress-view').style.display = 'none';
    document.getElementById('success-view').style.display = 'block';
  }
  
  function showError(msg) {
    const errEl = document.getElementById('error-message');
    errEl.textContent = msg;
    errEl.classList.add('visible');
    document.getElementById('uninstall-btn').disabled = false;
    document.getElementById('cancel-btn').disabled = false;
    document.getElementById('progress-view').style.display = 'none';
    document.getElementById('confirm-view').style.display = 'block';
  }
  
  async function startUninstall() {
    document.getElementById('uninstall-btn').disabled = true;
    document.getElementById('cancel-btn').disabled = true;
    showProgress();
    updateProgress(0, 'Checking conditions', 'Verifying...');
    
    try {
      const result = await pywebview.api.check_conditions();
      if (!result.can_uninstall) {
        showError(result.reason);
        return;
      }
      
      updateProgress(10, 'Stopping processes', 'Killing UnblockR processes...');
      await pywebview.api.kill_processes();
      
      updateProgress(30, 'Removing application', 'Deleting application files...');
      await pywebview.api.remove_app_dir();
      
      updateProgress(60, 'Removing shortcuts', 'Deleting Start Menu shortcuts...');
      await pywebview.api.remove_shortcuts();
      
      updateProgress(90, 'Cleaning up', 'Finalizing...');
      await pywebview.api.cleanup();
      
      updateProgress(100, 'Complete!', 'Uninstall finished successfully');
      await new Promise(r => setTimeout(r, 500));
      showSuccess();
    } catch(e) {
      showError('Uninstall failed: ' + e);
    }
  }
  
  function closeWindow() {
    pywebview.api.close_window();
  }
  
  window.addEventListener('pywebviewready', function() {
    document.getElementById('app-path').textContent = '{{APP_DIR}}';
    document.getElementById('shortcut-path').textContent = '{{START_MENU}}';
    
    document.getElementById('uninstall-btn').onclick = startUninstall;
    document.getElementById('cancel-btn').onclick = closeWindow;
    const closeBtn = document.getElementById('close-btn');
    if (closeBtn) {
      closeBtn.onclick = closeWindow;
    }
  });
</script>
</body>
</html>
"""

class UninstallAPI:
    def __init__(self):
        self.app_dir = APP_DIR
        self.start_menu = START_MENU
        self.settings = SETTINGS
        self.window = None
    
    def set_window(self, window):
        self.window = window
    
    def close_window(self):
        """Close the uninstaller window"""
        if self.window:
            self.window.destroy()
        os._exit(0)
    
    def check_conditions(self):
        """Check if uninstall can proceed"""
        # Check if installed
        if not self.app_dir.exists():
            return {"can_uninstall": False, "reason": "UnblockR is not installed."}
        
        # Check proxy
        if self.is_proxy_active():
            return {"can_uninstall": False, "reason": "Cannot uninstall: a proxy is currently active.\nPlease disable the proxy in UnblockR before uninstalling."}
        
        # Check disabler
        if self.is_disabler_active():
            return {"can_uninstall": False, "reason": "Cannot uninstall: the disabler is currently active.\nPlease restore extensions in UnblockR before uninstalling."}
        
        return {"can_uninstall": True, "reason": ""}
    
    def is_proxy_active(self):
        """Check if a proxy is currently set in Windows"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
            )
            enabled, _ = winreg.QueryValueEx(key, "ProxyEnable")
            winreg.CloseKey(key)
            return enabled == 1
        except Exception:
            return False
    
    def is_disabler_active(self):
        """Check if disabler_active is true in settings.json"""
        try:
            if self.settings.exists():
                data = json.loads(self.settings.read_text(encoding="utf-8"))
                return data.get("disabler_active", False) is True
            return False
        except Exception:
            return False
    
    def kill_processes(self):
        """Kill any running UnblockR python processes"""
        try:
            result = subprocess.run(
                ["wmic", "process", "where",
                 f"commandline like '%{self.app_dir}%' and name='pythonw.exe'",
                 "get", "processid"],
                capture_output=True, text=True, timeout=10
            )
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.isdigit():
                    subprocess.run(["taskkill", "/F", "/PID", line],
                                 capture_output=True, timeout=5)
        except Exception:
            pass
        
        try:
            result = subprocess.run(
                ["wmic", "process", "where",
                 f"commandline like '%{self.app_dir}%' and name='python.exe'",
                 "get", "processid"],
                capture_output=True, text=True, timeout=10
            )
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.isdigit():
                    subprocess.run(["taskkill", "/F", "/PID", line],
                                 capture_output=True, timeout=5)
        except Exception:
            pass
        
        return {"success": True}
    
    def remove_app_dir(self):
        """Remove the application directory"""
        try:
            if self.app_dir.exists():
                shutil.rmtree(self.app_dir, ignore_errors=True)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def remove_shortcuts(self):
        """Remove Start Menu shortcuts"""
        try:
            if self.start_menu.exists():
                shutil.rmtree(self.start_menu, ignore_errors=True)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def cleanup(self):
        """Final cleanup"""
        return {"success": True}

def main():
    # Check if installed
    if not APP_DIR.exists():
        ctypes.windll.user32.MessageBoxW(0, "UnblockR is not installed on this system.", "UnblockR Uninstaller", 0x10)
        return
    
    # Create and show the GUI window
    api = UninstallAPI()
    
    # Replace placeholders in HTML
    html_final = HTML.replace("{{APP_DIR}}", str(APP_DIR)).replace("{{START_MENU}}", str(START_MENU))
    
    window = webview.create_window(
        "UnblockR - Uninstaller",
        html=html_final,
        js_api=api,
        width=520,
        height=560,
        resizable=False,
        frameless=True,
        easy_drag=True,
        background_color="#070a0f"
    )
    
    api.set_window(window)
    webview.start(debug=False)

if __name__ == "__main__":
    main()
