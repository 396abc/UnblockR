#!/usr/bin/env python3
"""
UnblockR - main.py
GUI client for UnblockR.
Runs via launcher.vbs (hidden console).
"""

VERSION = "1.3.1"

import sys
import os
import json
import winreg
import ctypes
import subprocess
import urllib.request
import urllib.error
import threading
import socket
import websocket
import time
import shutil
import zipfile
import logging
from pathlib import Path
import base64
import re
import random

try:
    import webview
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pywebview", "-q"])
    import webview

# ── Config ─────────────────────────────────────────────────────────────────────
APP_DIR     = Path(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_FILE = APP_DIR / "settings.json"

# These are set dynamically based on plan
PROXY_IP    = None
PROXY_PORT  = None
PROXY_ADDR  = None
TUNNEL_URL  = None
LOCAL_PROXY = None
USER_PLAN   = None
USER_TOKEN  = None

AUTH_URL     = "https://auth.unblockr.org"
DASH_URL     = "https://dash.unblockr.org/api/stats"
REMOTE_MAIN  = "https://raw.githubusercontent.com/396abc/UnblockR/main/main.py"

ICON_URL    = "https://github.com/396abc/UnblockR/raw/refs/heads/main/UnblockR.ico"
LOGO_URL    = "https://raw.githubusercontent.com/396abc/UnblockR/main/UnblockR.png"

REG_PATH     = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
PROXY_BYPASS = "localhost;127.*;192.168.*;<local>"

CHROME_DIR    = Path(os.environ.get("LOCALAPPDATA","")) / "Google/Chrome/User Data/Default"
BACKUP_DIR    = APP_DIR / "backups"
RESOURCES_DIR = APP_DIR / "resources"

# ── Logging ────────────────────────────────────────────────────────────────────
LOG_PATH = APP_DIR / "unblockr.log"
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("UnblockR")

ICON_PATH   = APP_DIR / "UnblockR.ico"
LOGO_PATH   = APP_DIR / "UnblockR.png"

EXTENSION_FOLDERS = [
    "Extension Scripts", "Extensions", "Managed Extension Settings",
    "Local Extension Settings", "Extension State", "Extension Rules",
]

RESOURCE_URLS = {
    "Extension Rules.zip":              "https://github.com/396abc/UnblockR/raw/refs/heads/main/resources/Extension%20Rules.zip",
    "Extension Scripts.zip":            "https://github.com/396abc/UnblockR/raw/refs/heads/main/resources/Extension%20Scripts.zip",
    "Extension State.zip":              "https://github.com/396abc/UnblockR/raw/refs/heads/main/resources/Extension%20State.zip",
    "Extensions.zip":                   "https://github.com/396abc/UnblockR/raw/refs/heads/main/resources/Extensions.zip",
    "Local Extension Settings.zip":     "https://github.com/396abc/UnblockR/raw/refs/heads/main/resources/Local%20Extension%20Settings.zip",
    "Managed Extension Settings.zip":   "https://github.com/396abc/UnblockR/raw/refs/heads/main/resources/Managed%20Extension%20Settings.zip",
}

# ── Assets ─────────────────────────────────────────────────────────────────────
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
    defaults = {"window": {"x": 120, "y": 120, "w": 960, "h": 620}, "disabler_active": False}
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

def set_disabler_state(active: bool):
    s = load_settings()
    s["disabler_active"] = active
    save_settings(s)
    log.info(f"disabler_active saved as {active}")

def get_disabler_state() -> bool:
    return load_settings().get("disabler_active", False)

def get_stored_token() -> str:
    return load_settings().get("token", "")

def save_token(token: str, username: str):
    global USER_TOKEN
    s = load_settings()
    s["token"]    = token
    s["username"] = username
    save_settings(s)
    USER_TOKEN = token
    log.info(f"Token saved for {username}")

def clear_token():
    global USER_TOKEN
    s = load_settings()
    s.pop("token", None)
    s.pop("username", None)
    save_settings(s)
    USER_TOKEN = None
    log.info("Token cleared")

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
    if USER_PLAN == "premium":
        start_tunnel()
    _reg_set("ProxyEnable", 1, winreg.REG_DWORD)
    _reg_set("ProxyServer", PROXY_ADDR)
    _reg_set("ProxyOverride", PROXY_BYPASS)
    _notify_windows()

def disable_proxy():
    if USER_PLAN == "premium":
        stop_tunnel()
    _reg_set("ProxyEnable", 0, winreg.REG_DWORD)
    _notify_windows()

# ── Auth helpers ───────────────────────────────────────────────────────────────
def auth_request(endpoint: str, payload: dict = None, timeout: int = 8):
    try:
        url  = f"{AUTH_URL}{endpoint}"
        data = json.dumps(payload).encode() if payload else None
        hdrs = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"} if data else {"User-Agent": "Mozilla/5.0"}
        if USER_TOKEN:
            hdrs["X-Token"] = USER_TOKEN
        req  = urllib.request.Request(url, data=data, headers=hdrs)
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read()), None
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read()), e.code
        except Exception:
            return {"error": str(e)}, e.code
    except Exception as e:
        return {"error": str(e)}, None

def verify_token_sync(token: str) -> tuple:
    global USER_PLAN, PROXY_IP, PROXY_PORT, PROXY_ADDR, TUNNEL_URL, LOCAL_PROXY
    data, code = auth_request(f"/auth/verify?token={token}")
    valid = data.get("valid", False)
    if valid:
        plan = data.get("plan")
        USER_PLAN = plan
        proxy_cfg = data.get("proxy", {})
        if plan == "home":
            PROXY_IP   = proxy_cfg.get("host", "static.unblockr.org")
            PROXY_PORT = proxy_cfg.get("port", 8888)
            PROXY_ADDR = f"{USER_TOKEN}:x@{PROXY_IP}:{PROXY_PORT}" if USER_TOKEN else None
            TUNNEL_URL = None
            LOCAL_PROXY = None
        elif plan == "premium":
            TUNNEL_URL  = proxy_cfg.get("tunnel_url", "wss://tunnel.unblockr.org")
            LOCAL_PROXY = proxy_cfg.get("local_proxy", "127.0.0.1:19999")
            PROXY_ADDR  = LOCAL_PROXY
            PROXY_IP    = "127.0.0.1"
            PROXY_PORT  = 19999
        else:
            USER_PLAN = None
            PROXY_ADDR = None
    return valid, data

# ── Chrome / disabler helpers ─────────────────────────────────────────────────
def kill_chrome():
    try:
        subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True, timeout=10)
        time.sleep(1.5)
    except Exception:
        pass

def _js(code):
    try:
        window.evaluate_js(code)
    except Exception as e:
        log.error(f"_js error: {e}")

def _prog(pct, msg):
    _js(f'window._disablerProgress({pct}, {json.dumps(msg)})')

def run_disabler():
    log.info("=== run_disabler started ===")
    try:
        _prog(2, "Closing Chrome...")
        kill_chrome()
        BACKUP_DIR.mkdir(exist_ok=True)
        RESOURCES_DIR.mkdir(exist_ok=True)
        total = len(EXTENSION_FOLDERS) + len(RESOURCE_URLS) * 2
        step = 0
        for folder in EXTENSION_FOLDERS:
            src = CHROME_DIR / folder
            dst = BACKUP_DIR / folder
            pct = int(5 + (step / total) * 40)
            if src.exists():
                _prog(pct, f"Backing up {folder}...")
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.move(str(src), str(dst))
            else:
                _prog(pct, f"Skipping {folder} (not found)...")
            step += 1
        for fname, url in RESOURCE_URLS.items():
            pct = int(45 + (step / total) * 30)
            _prog(pct, f"Downloading {fname}...")
            dest = RESOURCES_DIR / fname
            try:
                urllib.request.urlretrieve(url, dest)
            except Exception as e:
                log.error(f"Download failed: {fname}: {e}")
                _js(f'window._disablerError("Download failed: {fname}")')
                return
            step += 1
        for fname in RESOURCE_URLS:
            pct = int(75 + (step / total) * 20)
            folder_name = fname.replace(".zip", "")
            _prog(pct, f"Installing {folder_name}...")
            zip_path = RESOURCES_DIR / fname
            try:
                with zipfile.ZipFile(zip_path, 'r') as z:
                    z.extractall(CHROME_DIR)
            except Exception as e:
                log.error(f"Extract failed: {fname}: {e}")
                _js(f'window._disablerError("Extract failed: {folder_name}")')
                return
            step += 1
        log.info("=== run_disabler complete ===")
        set_disabler_state(True)
        _prog(100, "Done!")
        time.sleep(0.5)
        _js('window._disablerDone(true)')
    except Exception as e:
        log.exception(f"run_disabler exception: {e}")
        _js(f'window._disablerError({json.dumps(str(e))})')

def run_restorer():
    log.info("=== run_restorer started ===")
    try:
        _prog(2, "Closing Chrome...")
        kill_chrome()
        total = len(EXTENSION_FOLDERS) * 2
        step  = 0
        for folder in EXTENSION_FOLDERS:
            pct = int(5 + (step / total) * 45)
            target = CHROME_DIR / folder
            _prog(pct, f"Removing {folder}...")
            if target.exists():
                shutil.rmtree(target)
            step += 1
        time.sleep(1)
        for folder in EXTENSION_FOLDERS:
            pct = int(50 + (step / total) * 45)
            src = BACKUP_DIR / folder
            dst = CHROME_DIR / folder
            _prog(pct, f"Restoring {folder}...")
            if src.exists():
                shutil.move(str(src), str(dst))
            step += 1
        try:
            if BACKUP_DIR.exists() and not any(BACKUP_DIR.iterdir()):
                BACKUP_DIR.rmdir()
        except Exception:
            pass
        log.info("=== run_restorer complete ===")
        set_disabler_state(False)
        _prog(100, "Restored!")
        time.sleep(0.5)
        _js('window._disablerDone(false)')
    except Exception as e:
        log.exception(f"run_restorer exception: {e}")
        _js(f'window._disablerError({json.dumps(str(e))})')

# ── Server check ───────────────────────────────────────────────────────────────
def check_server(timeout=4):
    try:
        req  = urllib.request.Request(DASH_URL, headers={"User-Agent": "Mozilla/5.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
        return True, data
    except Exception:
        return False, {}

# ── Remote version check ───────────────────────────────────────────────────────
def fetch_remote_version():
    try:
        req = urllib.request.Request(REMOTE_MAIN, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode("utf-8", errors="ignore")
            match = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                return match.group(1)
    except Exception as e:
        log.error(f"Version check failed: {e}")
    return None

# ── Subscription polling ──────────────────────────────────────────────────────
def poll_subscription():
    while True:
        time.sleep(30)
        token = get_stored_token()
        if not token:
            continue
        try:
            valid, info = verify_token_sync(token)
            plan = info.get("plan")
            payload = json.dumps({
                "valid":       valid,
                "reason":      info.get("reason", ""),
                "sub_expires": info.get("sub_expires"),
                "plan":        plan,
            })
            _js(f'window._onSubUpdate({payload})')
            if not valid and proxy_is_active():
                log.info("Subscription invalid — disabling proxy")
                disable_proxy()
                _js('window._onSubKick()')
            elif plan and USER_PLAN != plan:
                USER_PLAN = plan
                _js(f'window._onPlanChange({json.dumps(plan)})')
        except Exception as e:
            log.debug(f"Sub poll error: {e}")

# ── WebSocket Tunnel (Premium only) ───────────────────────────────────────────
_tunnel_running = False
_tunnel_thread = None

def _tunnel_run():
    global _tunnel_running
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind(('127.0.0.1', 19999))
    except Exception:
        log.error("Failed to bind local proxy on 127.0.0.1:19999")
        return
    server.listen(50)
    server.settimeout(1)
    _tunnel_running = True
    log.info("Local proxy listening on 127.0.0.1:19999")

    while _tunnel_running:
        try:
            client, addr = server.accept()
            threading.Thread(target=_handle_tunnel_client, args=(client,), daemon=True).start()
        except socket.timeout:
            continue
        except Exception as e:
            if _tunnel_running:
                log.debug(f"Accept error: {e}")
    server.close()

def _handle_tunnel_client(client):
    ws = None
    try:
        ws = websocket.create_connection(TUNNEL_URL, timeout=10)
        def forward(src, dst, is_ws=False):
            try:
                while True:
                    if is_ws:
                        data = src.recv()
                    else:
                        data = src.recv(4096)
                    if not data:
                        break
                    if is_ws:
                        dst.send(data)
                    else:
                        dst.sendall(data)
            except:
                pass
        t1 = threading.Thread(target=forward, args=(client, ws, False), daemon=True)
        t2 = threading.Thread(target=forward, args=(ws, client, True), daemon=True)
        t1.start()
        t2.start()
        t1.join(timeout=60)
        t2.join(timeout=60)
    except Exception as e:
        log.debug(f"Tunnel handler error: {e}")
    finally:
        try: client.close()
        except: pass
        try: ws.close()
        except: pass

def start_tunnel():
    global _tunnel_thread
    if _tunnel_thread and _tunnel_thread.is_alive():
        return
    _tunnel_thread = threading.Thread(target=_tunnel_run, daemon=True)
    _tunnel_thread.start()
    time.sleep(0.5)
    log.info("Tunnel started")

def stop_tunnel():
    global _tunnel_running
    _tunnel_running = False
    log.info("Tunnel stopped")

# ── Helper functions for proxy configuration ───────────────────────────────────
def _set_home_proxy():
    """Set proxy configuration for HOME plan"""
    global PROXY_IP, PROXY_PORT, PROXY_ADDR, TUNNEL_URL, LOCAL_PROXY
    PROXY_IP = "static.unblockr.org"
    PROXY_PORT = 8888
    PROXY_ADDR = f"{USER_TOKEN}:x@{PROXY_IP}:{PROXY_PORT}" if USER_TOKEN else None
    TUNNEL_URL = None
    LOCAL_PROXY = None
    log.info(f"Home proxy configured: {PROXY_ADDR}")

def _set_premium_proxy():
    """Set proxy configuration for PREMIUM plan"""
    global PROXY_IP, PROXY_PORT, PROXY_ADDR, TUNNEL_URL, LOCAL_PROXY
    TUNNEL_URL = "wss://tunnel.unblockr.org"
    LOCAL_PROXY = "127.0.0.1:19999"
    PROXY_ADDR = LOCAL_PROXY
    PROXY_IP = "127.0.0.1"
    PROXY_PORT = 19999
    log.info(f"Premium proxy configured: {PROXY_ADDR}")

def _clear_proxy_config():
    """Clear all proxy configuration"""
    global PROXY_IP, PROXY_PORT, PROXY_ADDR, TUNNEL_URL, LOCAL_PROXY, USER_PLAN
    PROXY_IP = None
    PROXY_PORT = None
    PROXY_ADDR = None
    TUNNEL_URL = None
    LOCAL_PROXY = None
    USER_PLAN = None

def _apply_plan_config(plan: str):
    """Apply proxy configuration based on plan type"""
    if plan == "home":
        _set_home_proxy()
    elif plan == "premium":
        _set_premium_proxy()
    else:
        _clear_proxy_config()

# ── API Class ──────────────────────────────────────────────────────────────────
# ── API Class ──────────────────────────────────────────────────────────────────
class API:
    def __init__(self):
        self.settings = load_settings()
        self._remote_ver = None
        self._ver_checked = False
        self._window_ref = None
        self._disabler_running = False
        self._disabler_active = get_disabler_state()

    def startup(self):
        """Initialize the application on startup"""
        global USER_TOKEN, USER_PLAN, PROXY_IP, PROXY_PORT, PROXY_ADDR, TUNNEL_URL, LOCAL_PROXY
        threading.Thread(target=self._bg_version_check, daemon=True).start()
        
        token = get_stored_token()
        username = self.settings.get("username", "")
        
        logged_in = False
        sub_expires = None
        sub_reason = "no_token"
        plan = None
        proxy_active = False
        
        if token:
            USER_TOKEN = token
            # This will set USER_PLAN, PROXY_IP, PROXY_PORT, PROXY_ADDR, etc.
            valid, info = verify_token_sync(token)
            logged_in = valid
            sub_expires = info.get("sub_expires")
            sub_reason = info.get("reason", "")
            plan = info.get("plan")
            # USER_PLAN and proxy config are already set by verify_token_sync
            
            if not valid:
                log.info(f"Token invalid on startup: {sub_reason}")
                PROXY_ADDR = None
        else:
            log.info("No token found on startup")
        
        # Check if proxy is active with current settings
        if PROXY_ADDR:
            proxy_active = proxy_is_active()
            log.info(f"Proxy active status on startup: {proxy_active}")
        
        log.info(f"Startup - Plan: {plan}, Proxy_ADDR: {PROXY_ADDR}")
        
        return {
            "proxy_active": proxy_active,
            "version": VERSION,
            "logo": logo_b64(),
            "disabler_active": self._disabler_active,
            "logged_in": logged_in,
            "username": username if logged_in else "",
            "sub_expires": sub_expires,
            "sub_reason": sub_reason,
            "plan": plan,
        }

    def do_login(self, username: str, password: str):
        """Handle user login"""
        global USER_TOKEN, USER_PLAN, PROXY_IP, PROXY_PORT, PROXY_ADDR, TUNNEL_URL, LOCAL_PROXY
        data, code = auth_request("/auth/login", {"username": username, "password": password})
        
        if "token" not in data:
            return {"success": False, "error": data.get("error", "Login failed")}
        
        USER_TOKEN = data["token"]
        save_token(data["token"], data.get("username", username))
        plan = data.get("plan")
        USER_PLAN = plan
        
        # Set proxy config based on plan
        if plan == "home":
            PROXY_IP = "static.unblockr.org"
            PROXY_PORT = 8888
            PROXY_ADDR = f"{USER_TOKEN}:x@{PROXY_IP}:{PROXY_PORT}" if USER_TOKEN else None
            TUNNEL_URL = None
            LOCAL_PROXY = None
            log.info(f"Home proxy configured: {PROXY_ADDR}")
        elif plan == "premium":
            TUNNEL_URL = "wss://tunnel.unblockr.org"
            LOCAL_PROXY = "127.0.0.1:19999"
            PROXY_ADDR = LOCAL_PROXY
            PROXY_IP = "127.0.0.1"
            PROXY_PORT = 19999
            log.info(f"Premium proxy configured: {PROXY_ADDR}")
        else:
            PROXY_ADDR = None
            log.info(f"No valid plan: {plan}")
        
        return {
            "success": True,
            "username": data.get("username", username),
            "sub_expires": data.get("sub_expires"),
            "plan": plan,
        }

    def do_signup(self, username: str, password: str):
        """Handle user signup"""
        global USER_TOKEN, USER_PLAN, PROXY_IP, PROXY_PORT, PROXY_ADDR, TUNNEL_URL, LOCAL_PROXY
        data, code = auth_request("/auth/signup", {"username": username, "password": password})
        
        if "token" not in data:
            return {"success": False, "error": data.get("error", "Signup failed")}
        
        USER_TOKEN = data["token"]
        save_token(data["token"], data.get("username", username))
        plan = data.get("plan")
        USER_PLAN = plan
        
        # Set proxy config based on plan
        if plan == "home":
            PROXY_IP = "static.unblockr.org"
            PROXY_PORT = 8888
            PROXY_ADDR = f"{USER_TOKEN}:x@{PROXY_IP}:{PROXY_PORT}" if USER_TOKEN else None
            TUNNEL_URL = None
            LOCAL_PROXY = None
        elif plan == "premium":
            TUNNEL_URL = "wss://tunnel.unblockr.org"
            LOCAL_PROXY = "127.0.0.1:19999"
            PROXY_ADDR = LOCAL_PROXY
            PROXY_IP = "127.0.0.1"
            PROXY_PORT = 19999
        else:
            PROXY_ADDR = None
        
        return {
            "success": True,
            "username": data.get("username", username),
            "sub_expires": data.get("sub_expires"),
            "plan": plan,
        }

    def do_logout(self):
        """Handle user logout"""
        global PROXY_ADDR
        clear_token()
        PROXY_ADDR = None
        return {"success": True}

    # ── Disabler Methods ──────────────────────────────────────────────────────
    def activate_disabler(self):
        """Activate the Chrome extension disabler"""
        if not USER_PLAN:
            return {"started": False, "error": "no_plan"}
        
        log.info("activate_disabler called from JS")
        self._disabler_running = True
        
        def _run():
            try:
                run_disabler()
            finally:
                self._disabler_running = False
        
        threading.Thread(target=_run, daemon=True).start()
        return {"started": True}

    def restore_disabler(self):
        """Restore Chrome extensions from backup"""
        log.info("restore_disabler called from JS")
        self._disabler_running = True
        
        def _run():
            try:
                run_restorer()
            finally:
                self._disabler_running = False
        
        threading.Thread(target=_run, daemon=True).start()
        return {"started": True}

    # ── Proxy Methods ─────────────────────────────────────────────────────────
    def toggle_proxy(self):
        """Toggle the proxy on/off"""
        if proxy_is_active():
            disable_proxy()
            return {"proxy_active": False, "online": None, "stats": {}, "error": None}
        
        token = get_stored_token()
        if not token:
            return {"proxy_active": False, "online": False, "stats": {}, "error": "not_logged_in"}
        
        if not USER_PLAN:
            return {"proxy_active": False, "online": False, "stats": {}, "error": "no_plan"}
        
        valid, info = verify_token_sync(token)
        if not valid:
            reason = info.get("reason", "invalid_token")
            log.info(f"Toggle blocked: {reason}")
            return {"proxy_active": False, "online": False, "stats": {}, "error": reason}
        
        ok, data = check_server(timeout=5)
        if not ok:
            return {"proxy_active": False, "online": False, "stats": {}, "error": "server_unreachable"}
        
        enable_proxy()
        return {"proxy_active": True, "online": True, "stats": data, "error": None}

    def get_stats(self):
        """Get current proxy statistics"""
        ok, data = check_server(timeout=3)
        return {"online": ok, "stats": data}

    def get_version_info(self):
        """Get version information"""
        return {
            "local": VERSION,
            "remote": self._remote_ver or "checking...",
            "checked": self._ver_checked,
            "update_avail": self._ver_checked and self._remote_ver is not None and self._remote_ver != VERSION,
        }

    # ── Background Tasks ──────────────────────────────────────────────────────
    def _bg_version_check(self):
        """Background version check"""
        remote = fetch_remote_version()
        self._remote_ver = remote
        self._ver_checked = True
        update_avail = remote is not None and remote != VERSION
        try:
            if self._window_ref:
                self._window_ref.evaluate_js(
                    f'onVersionCheck("{remote or "unavailable"}", {str(update_avail).lower()})'
                )
        except Exception:
            pass

    # ── Utility Methods ───────────────────────────────────────────────────────
    def open_updater(self):
        """Open the updater"""
        vbs = APP_DIR / "updater_launcher.vbs"
        try:
            if vbs.exists():
                subprocess.Popen(["wscript.exe", str(vbs)], shell=False)
            elif (APP_DIR / "updater.py").exists():
                subprocess.Popen([sys.executable, str(APP_DIR / "updater.py")], shell=False)
            window.hide()
        except Exception:
            pass
        return {"launched": True}

    def reopen(self):
        """Reopen the main window"""
        try:
            window.show()
        except Exception:
            pass

    def launch_uninstaller(self):
        """Launch the uninstaller"""
        vbs = APP_DIR / "uninstall_launcher.vbs"
        try:
            if vbs.exists():
                subprocess.Popen(["wscript.exe", str(vbs)], shell=False)
            elif (APP_DIR / "uninstall.py").exists():
                subprocess.Popen([sys.executable, str(APP_DIR / "uninstall.py")], shell=False)
        except Exception:
            pass
        time.sleep(0.5)
        os._exit(0)
    
    def close(self):
        """Close the application"""
        if proxy_is_active():
            log.info("Close blocked — proxy still active")
            return {"blocked": "proxy"}
        if self._disabler_running:
            log.info("Close blocked — disabler running")
            return {"blocked": "disabler"}
        try:
            window.evaluate_js('showClosingToast()')
            time.sleep(0.5)
        except Exception:
            pass
        try:
            pos = window.get_position()
            size = window.get_size()
            s = self.settings
            s["window"] = {"x": pos[0], "y": pos[1], "w": size[0], "h": size[1]}
            save_settings(s)
        except Exception:
            pass
        os._exit(0)

# ── HTML (truncated for brevity - same as original) ────────────────────────────
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
    --premium:  #ffd700;
    --premium-glow: rgba(255,215,0,0.15);
    --mono:     'DM Mono', monospace;
    --display:  'Syne', sans-serif;
  }
  *, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:var(--mono); background:var(--bg); color:var(--text); height:100vh; overflow:hidden; user-select:none; position:relative; }
  
  /* Premium glow effect */
  @keyframes premiumPulse {
    0%, 100% { opacity: 0.6; }
    50% { opacity: 1; }
  }
  
  .premium-glow {
    animation: premiumPulse 2s ease-in-out infinite;
  }

  #loader, #auth-screen, #error-overlay, #app, .toast {
    position: relative;
    z-index: 1;
  }

  #loader { position:fixed; inset:0; background:var(--bg); display:flex; flex-direction:column; align-items:center; justify-content:center; z-index:998; transition:opacity 0.5s ease, transform 0.5s ease; }
  #loader.fade-out { opacity:0; transform:scale(1.02); pointer-events:none; }
  .loader-logo { width:68px; height:68px; object-fit:contain; margin-bottom:18px; animation:float 3s ease-in-out infinite; }
  @keyframes float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-6px)} }
  .loader-word { font-family:var(--display); font-size:26px; font-weight:800; color:var(--text); margin-bottom:4px; }
  .loader-word .r { color:var(--accent); }
  .loader-sub { font-size:11px; color:var(--muted); letter-spacing:0.12em; text-transform:uppercase; margin-bottom:36px; }
  .progress-track { width:220px; height:2px; background:var(--border); border-radius:2px; overflow:hidden; margin-bottom:14px; }
  .progress-fill { height:100%; background:linear-gradient(90deg,var(--accent),var(--on)); border-radius:2px; width:0%; transition:width 0.4s cubic-bezier(0.4,0,0.2,1); }
  .loader-status { font-size:11px; color:var(--muted); letter-spacing:0.06em; }

  #auth-screen { position:fixed; inset:0; background:var(--bg); display:none; align-items:center; justify-content:center; z-index:900; }
  #auth-screen.visible { display:flex; }
  .auth-card { background:var(--surface); border:1px solid var(--border); border-radius:16px; padding:40px; width:360px; text-align:center; position:relative; z-index:2; }
  .auth-card::before { content:''; position:absolute; top:0; left:0; right:0; height:2px; background:linear-gradient(90deg,var(--accent),transparent); border-radius:16px 16px 0 0; }
  .auth-close { position:absolute; top:14px; right:14px; width:26px; height:26px; background:transparent; border:1px solid var(--border); border-radius:6px; color:var(--muted); font-size:14px; cursor:pointer; display:flex; align-items:center; justify-content:center; transition:all 0.15s; }
  .auth-close:hover { background:var(--off-dim); border-color:var(--off); color:var(--off); }
  .auth-logo { width:52px; height:52px; object-fit:contain; margin-bottom:14px; }
  .auth-title { font-family:var(--display); font-size:22px; font-weight:800; color:var(--text); margin-bottom:4px; }
  .auth-title .r { color:var(--accent); }
  .auth-sub { font-size:11px; color:var(--muted); letter-spacing:0.1em; text-transform:uppercase; margin-bottom:24px; }
  .auth-tabs { display:flex; gap:4px; margin-bottom:20px; background:var(--raised); border-radius:8px; padding:3px; }
  .auth-tab { flex:1; padding:8px; border:none; border-radius:6px; font-family:var(--mono); font-size:12px; cursor:pointer; transition:all 0.15s; background:transparent; color:var(--muted); }
  .auth-tab.active { background:var(--surface); color:var(--text); }
  .auth-input { width:100%; padding:11px 14px; background:var(--raised); border:1px solid var(--border); border-radius:8px; color:var(--text); font-family:var(--mono); font-size:13px; margin-bottom:10px; outline:none; transition:border-color 0.15s; }
  .auth-input:focus { border-color:var(--accent); }
  .auth-btn { width:100%; padding:12px; border-radius:9px; font-family:var(--mono); font-size:13px; font-weight:500; cursor:pointer; transition:all 0.2s; margin-top:4px; border:1px solid rgba(61,158,255,0.4); background:var(--accent-d); color:var(--accent); }
  .auth-btn:hover { background:rgba(61,158,255,0.18); }
  .auth-btn:disabled { opacity:0.4; pointer-events:none; }
  .auth-error { font-size:11px; color:var(--off); margin-top:10px; min-height:16px; }

  #error-overlay { position:fixed; inset:0; background:rgba(7,10,15,0.92); display:none; flex-direction:column; align-items:center; justify-content:center; z-index:500; backdrop-filter:blur(4px); }
  #error-overlay.visible { display:flex; }
  .error-icon { font-size:34px; margin-bottom:14px; color:var(--off); }
  .error-title { font-family:var(--display); font-size:19px; font-weight:700; color:var(--off); margin-bottom:8px; }
  .error-sub { font-size:12px; color:var(--muted); text-align:center; line-height:1.7; max-width:290px; margin-bottom:24px; }
  .error-actions { display:flex; gap:10px; }
  .retry-btn { padding:10px 26px; background:var(--off-dim); border:1px solid var(--off); border-radius:8px; color:var(--off); font-family:var(--mono); font-size:12px; cursor:pointer; transition:all 0.2s; }
  .retry-btn:hover { background:var(--off); color:#fff; }
  .dismiss-btn { padding:10px 18px; background:transparent; border:1px solid var(--border2); border-radius:8px; color:var(--muted); font-family:var(--mono); font-size:12px; cursor:pointer; transition:all 0.2s; }
  .dismiss-btn:hover { color:var(--text); border-color:var(--text); }

  #app { display:flex; flex-direction:column; height:100vh; opacity:0; transition:opacity 0.4s ease; position:relative; z-index:1; }
  #app.visible { opacity:1; }

  .titlebar { height:50px; background:var(--surface); border-bottom:1px solid var(--border); display:flex; align-items:center; justify-content:space-between; padding:0 18px 0 16px; -webkit-app-region:drag; flex-shrink:0; position:relative; z-index:2; }
  .titlebar-left { display:flex; align-items:center; gap:10px; -webkit-app-region:no-drag; }
  .titlebar-left img { width:26px; height:26px; object-fit:contain; }
  .titlebar-word { font-family:var(--display); font-size:17px; font-weight:800; color:var(--text); letter-spacing:-0.3px; }
  .titlebar-word .r { color:var(--accent); }
  .titlebar-right { display:flex; align-items:center; gap:10px; -webkit-app-region:no-drag; }
  .server-pill { display:flex; align-items:center; gap:6px; padding:4px 10px; background:var(--raised); border:1px solid var(--border); border-radius:100px; font-size:11px; color:var(--muted); }
  .dot { width:6px; height:6px; border-radius:50%; background:var(--muted); }
  .dot.on  { background:var(--on); animation:blink 2.5s infinite; }
  .dot.off { background:var(--off); }
  @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }
  .plan-pill { padding:4px 10px; border-radius:100px; font-size:10px; font-weight:600; letter-spacing:0.06em; font-family:var(--mono); }
  .plan-pill.premium { background:linear-gradient(135deg, rgba(255,215,0,0.15), rgba(255,215,0,0.05)); border:1px solid rgba(255,215,0,0.4); color:var(--premium); text-shadow: 0 0 8px rgba(255,215,0,0.3); }
  .plan-pill.home { background:var(--on-dim); border:1px solid rgba(0,229,160,0.25); color:var(--on); }
  .plan-pill.none { background:var(--raised); border:1px solid var(--border); color:var(--muted); }
  .user-pill { display:flex; align-items:center; gap:8px; padding:4px 10px; background:var(--raised); border:1px solid var(--border); border-radius:100px; font-size:11px; color:var(--muted); }
  .user-pill .uname { color:var(--accent); }
  .logout-btn { padding:2px 8px; background:transparent; border:1px solid var(--border); border-radius:5px; color:var(--muted); font-family:var(--mono); font-size:10px; cursor:pointer; transition:all 0.15s; }
  .logout-btn:hover { color:var(--off); border-color:rgba(229,80,80,0.4); }
  .close-btn { width:26px; height:26px; background:transparent; border:1px solid var(--border); border-radius:6px; color:var(--muted); font-size:14px; cursor:pointer; display:flex; align-items:center; justify-content:center; transition:all 0.15s; }
  .close-btn:hover { background:var(--off-dim); border-color:var(--off); color:var(--off); }

  .body { flex:1; display:flex; overflow:hidden; position:relative; z-index:1; }
  .sidebar { width:190px; background:var(--surface); border-right:1px solid var(--border); padding:20px 0; flex-shrink:0; display:flex; flex-direction:column; gap:2px; position:relative; z-index:2; }
  .nav-item { display:flex; align-items:center; gap:10px; padding:10px 18px; font-size:12px; color:var(--muted); cursor:pointer; border-left:2px solid transparent; transition:all 0.15s; letter-spacing:0.04em; position:relative; }
  .nav-item:hover { color:var(--text); background:var(--raised); }
  .nav-item.active { color:var(--accent); border-left-color:var(--accent); background:var(--accent-d); }
  .nav-icon { font-size:13px; width:16px; text-align:center; }
  .nav-badge { position:absolute; right:14px; top:50%; transform:translateY(-50%); padding:2px 6px; border-radius:100px; font-size:9px; font-weight:600; letter-spacing:0.04em; }
  .nav-badge.new { background:rgba(61,158,255,0.18); border:1px solid rgba(61,158,255,0.35); color:var(--accent); }
  .sidebar-bottom { margin-top:auto; padding:14px 18px; border-top:1px solid var(--border); }
  .version-tag { font-size:10px; color:var(--muted); letter-spacing:0.08em; }
  .sub-expiry { font-size:10px; margin-top:5px; }
  .sub-expiry.ok  { color:var(--on); }
  .sub-expiry.exp { color:var(--off); }
  .sub-expiry.none { color:var(--muted); }

  .content { flex:1; overflow-y:auto; padding:32px 36px; position:relative; z-index:2; }
  .content::-webkit-scrollbar { width:4px; }
  .content::-webkit-scrollbar-track { background:transparent; }
  .content::-webkit-scrollbar-thumb { background:var(--border2); border-radius:2px; }
  .page { display:none; animation:fadeUp 0.3s ease; }
  .page.active { display:block; }
  @keyframes fadeUp { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }

  .main-grid { display:grid; grid-template-columns:1fr 240px; gap:18px; align-items:start; }
  .disabler-card { background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:24px 28px; margin-bottom:18px; position:relative; overflow:hidden; grid-column:1/-1; }
  .disabler-card::before { content:''; position:absolute; top:0; left:0; right:0; height:2px; background:linear-gradient(90deg,var(--accent),transparent); }
  .disabler-card.active::before { background:linear-gradient(90deg,var(--on),transparent); }
  .disabler-card.locked { opacity:0.5; }
  
  /* Premium card styling */
  body.premium-active .disabler-card,
  body.premium-active .toggle-card,
  body.premium-active .stat-card,
  body.premium-active .updates-card,
  body.premium-active .about-card {
    border-color: rgba(255,215,0,0.2);
    box-shadow: 0 0 20px rgba(255,215,0,0.05);
  }
  
  .disabler-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:6px; }
  .disabler-title { font-family:var(--display); font-size:15px; font-weight:700; color:var(--text); }
  .disabler-badge { display:inline-flex; align-items:center; gap:5px; padding:2px 10px; border-radius:100px; font-size:8px; font-weight:500; }
  .disabler-badge.off { background:var(--off-dim); border:1px solid rgba(229,80,80,0.2); color:var(--off); }
  .disabler-badge.on  { background:var(--on-dim); border:1px solid rgba(0,229,160,0.25); color:var(--on); }
  .disabler-desc { font-size:11px; color:var(--muted); line-height:1.6; margin-bottom:16px; }
  .disabler-btns { display:flex; gap:10px; align-items:center; }
  .dis-btn { padding:9px 20px; border-radius:8px; font-family:var(--mono); font-size:12px; font-weight:500; cursor:pointer; transition:all 0.2s; border:1px solid var(--border2); background:var(--raised); color:var(--text); }
  .dis-btn.activate { border-color:rgba(0,229,160,0.4); background:var(--on-dim); color:var(--on); }
  .dis-btn.activate:hover { background:rgba(0,229,160,0.2); transform:translateY(-1px); }
  .dis-btn.restore { border-color:rgba(229,80,80,0.4); background:var(--off-dim); color:var(--off); }
  .dis-btn.restore:hover { background:rgba(229,80,80,0.2); transform:translateY(-1px); }
  .dis-btn:disabled { opacity:0.4; pointer-events:none; }
  .dis-progress { margin-top:14px; display:none; }
  .dis-progress.visible { display:block; }
  .dis-prog-row { display:flex; justify-content:space-between; font-size:10px; color:var(--muted); margin-bottom:6px; }
  .dis-prog-pct { color:var(--accent); }
  .dis-track { height:2px; background:var(--border); border-radius:2px; overflow:hidden; }
  .dis-fill { height:100%; background:linear-gradient(90deg,var(--accent),var(--on)); border-radius:2px; width:0%; transition:width 0.35s cubic-bezier(0.4,0,0.2,1); }
  .dis-error { font-size:11px; color:var(--off); margin-top:8px; display:none; }
  .no-plan-overlay { position:absolute; inset:0; background:rgba(7,10,15,0.85); display:flex; align-items:center; justify-content:center; z-index:10; border-radius:14px; backdrop-filter:blur(2px); }
  .no-plan-overlay span { font-size:12px; color:var(--muted); letter-spacing:0.06em; font-family:var(--mono); }

  .toggle-card { background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:24px 24px 22px; position:relative; overflow:hidden; transition:border-color 0.3s; }
  .toggle-card::before { content:''; position:absolute; top:0; left:0; right:0; height:2px; background:linear-gradient(90deg,var(--accent),transparent); transition:background 0.4s; }
  .toggle-card.on::before { background:linear-gradient(90deg,var(--on),transparent); }
  .toggle-card.locked { opacity:0.5; }
  .status-label { font-size:10px; letter-spacing:0.1em; text-transform:uppercase; color:var(--muted); margin-bottom:10px; }
  .status-value { font-family:var(--display); font-size:22px; font-weight:800; line-height:1; margin-bottom:4px; transition:color 0.3s; }
  .status-value.on  { color:var(--on); }
  .status-value.off { color:var(--text); }
  .status-desc { font-size:12px; color:var(--muted); margin-bottom:18px; line-height:1.6; }
  .toggle-btn { display:flex; align-items:center; gap:12px; padding:13px 24px; border-radius:10px; border:1px solid var(--border2); background:var(--raised); color:var(--text); font-family:var(--mono); font-size:13px; font-weight:500; cursor:pointer; transition:all 0.2s cubic-bezier(0.4,0,0.2,1); width:fit-content; }
  .toggle-btn:hover { transform:translateY(-2px); box-shadow:0 8px 24px rgba(0,0,0,0.3); }
  .toggle-btn.activate { border-color:rgba(0,229,160,0.4); background:var(--on-dim); color:var(--on); }
  .toggle-btn.activate:hover { box-shadow:0 8px 24px rgba(0,229,160,0.15); }
  .toggle-btn.deactivate { border-color:rgba(229,80,80,0.4); background:var(--off-dim); color:var(--off); }
  .toggle-btn.deactivate:hover { box-shadow:0 8px 24px rgba(229,80,80,0.15); }
  .toggle-btn.loading { opacity:0.6; pointer-events:none; }
  .btn-dot { width:8px; height:8px; border-radius:50%; background:currentColor; flex-shrink:0; }

  .stats-col { display:flex; flex-direction:column; gap:10px; }
  .stat-card { background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:18px 20px; position:relative; overflow:hidden; }
  .stat-card::after { content:''; position:absolute; top:0; left:0; width:3px; height:100%; }
  .stat-card.green::after { background:var(--on); }
  .stat-card.red::after   { background:var(--off); }
  .stat-card.blue::after  { background:var(--accent); }
  .stat-label { font-size:10px; letter-spacing:0.1em; text-transform:uppercase; color:var(--muted); margin-bottom:6px; }
  .stat-val { font-family:var(--display); font-size:24px; font-weight:700; line-height:1; }
  .stat-card.green .stat-val { color:var(--on); }
  .stat-card.red   .stat-val { color:var(--off); }
  .stat-card.blue  .stat-val { color:var(--accent); }

  .info-strip { margin-top:16px; background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:14px 18px; display:flex; align-items:center; gap:8px; font-size:11px; color:var(--muted); grid-column:1/-1; }
  .info-strip code { background:var(--raised); border:1px solid var(--border); border-radius:4px; padding:1px 7px; color:var(--accent); font-family:var(--mono); font-size:11px; }

  .updates-card { background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:32px; max-width:500px; }
  .updates-header { display:flex; align-items:center; gap:14px; margin-bottom:24px; }
  .updates-logo { width:44px; height:44px; object-fit:contain; }
  .updates-title { font-family:var(--display); font-size:20px; font-weight:800; color:var(--text); }
  .updates-title .r { color:var(--accent); }
  .ver-row { display:flex; gap:12px; margin-bottom:20px; }
  .ver-box { flex:1; background:var(--raised); border:1px solid var(--border); border-radius:10px; padding:14px 16px; }
  .ver-box-label { font-size:10px; color:var(--muted); letter-spacing:0.1em; text-transform:uppercase; margin-bottom:6px; }
  .ver-box-val { font-family:var(--display); font-size:20px; font-weight:700; color:var(--text); }
  .update-status { display:flex; align-items:center; gap:8px; padding:10px 14px; border-radius:8px; font-size:12px; margin-bottom:20px; }
  .update-status.checking { background:rgba(74,96,112,0.15); border:1px solid var(--border); color:var(--muted); }
  .update-status.ok       { background:rgba(0,229,160,0.08); border:1px solid rgba(0,229,160,0.2); color:var(--on); }
  .update-status.avail    { background:rgba(61,158,255,0.08); border:1px solid rgba(61,158,255,0.25); color:var(--accent); }
  .update-btn { display:flex; align-items:center; gap:10px; padding:12px 22px; border-radius:9px; border:1px solid rgba(61,158,255,0.35); background:rgba(61,158,255,0.1); color:var(--accent); font-family:var(--mono); font-size:12px; cursor:pointer; transition:all 0.2s; width:fit-content; }
  .update-btn:hover { background:rgba(61,158,255,0.18); transform:translateY(-1px); }
  .update-btn:disabled { opacity:0.4; pointer-events:none; }
  .spinner { width:12px; height:12px; border:2px solid rgba(61,158,255,0.3); border-top-color:var(--accent); border-radius:50%; animation:spin 0.7s linear infinite; }
  @keyframes spin { to{transform:rotate(360deg)} }

  .about-card { background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:32px; max-width:520px; }
  .about-header { display:flex; align-items:center; gap:16px; margin-bottom:6px; }
  .about-logo { width:48px; height:48px; object-fit:contain; }
  .about-name { font-family:var(--display); font-size:28px; font-weight:800; color:var(--text); }
  .about-name .r { color:var(--accent); }
  .about-ver { font-size:11px; color:var(--muted); letter-spacing:0.1em; text-transform:uppercase; margin-bottom:20px; }
  .about-body { font-size:13px; color:var(--muted); line-height:1.8; }
  .divider { height:1px; background:var(--border); margin:20px 0; }
  .kv-row { display:flex; justify-content:space-between; align-items:center; padding:9px 0; border-bottom:1px solid var(--border); font-size:12px; }
  .kv-row:last-child { border-bottom:none; }
  .kv-key { color:var(--muted); }
  .kv-val { color:var(--text); font-family:var(--mono); }

  .toast { position:fixed; bottom:28px; left:50%; transform:translateX(-50%) translateY(20px); background:var(--raised); border-radius:10px; padding:11px 20px; display:flex; align-items:center; gap:10px; font-size:12px; color:var(--text); box-shadow:0 8px 32px rgba(0,0,0,0.4); opacity:0; pointer-events:none; transition:opacity 0.25s ease, transform 0.25s ease; z-index:600; white-space:nowrap; }
  .toast.show { opacity:1; transform:translateX(-50%) translateY(0); }
  .toast.warning { border:1px solid rgba(229,80,80,0.35); }
  .toast.info    { border:1px solid rgba(61,158,255,0.35); }
  .toast-icon.warn { color:var(--off); font-size:14px; flex-shrink:0; }
  .toast-icon.info { color:var(--accent); font-size:14px; flex-shrink:0; }
</style>
</head>
<body id="body">

<div id="auth-screen">
  <div class="auth-card">
    <button class="auth-close" id="auth-close-btn" onclick="closeAuthScreen()" style="display:none">&#x2715;</button>
    <img class="auth-logo" id="auth-logo" src="" alt="UnblockR">
    <div class="auth-title">Unblock<span class="r">R</span></div>
    <div class="auth-sub">Sign in to continue</div>
    <div class="auth-tabs">
      <button class="auth-tab active" id="tab-login" onclick="switchTab('login')">Login</button>
      <button class="auth-tab" id="tab-signup" onclick="switchTab('signup')">Sign Up</button>
    </div>
    <input class="auth-input" type="text" id="auth-username" placeholder="Username" autocomplete="off">
    <input class="auth-input" type="password" id="auth-password" placeholder="Password">
    <button class="auth-btn" id="auth-submit-btn" onclick="submitAuth()">Sign In</button>
    <div class="auth-error" id="auth-error"></div>
  </div>
</div>

<div id="loader">
  <img class="loader-logo" id="loader-img" src="" alt="UnblockR">
  <div class="loader-word">Unblock<span class="r">R</span></div>
  <div class="loader-sub">Starting up</div>
  <div class="progress-track"><div class="progress-fill" id="prog"></div></div>
  <div class="loader-status" id="loader-status">Initialising...</div>
</div>

<div id="error-overlay">
  <div class="error-icon">&#x26A0;</div>
  <div class="error-title">Server Unreachable</div>
  <div class="error-sub">Could not connect to UnblockR.<br><br>The server may be offline or you may not be on the correct network.</div>
  <div class="error-actions">
    <button class="retry-btn" onclick="retryToggle()">&#x21BA;&nbsp; Retry</button>
    <button class="dismiss-btn" onclick="dismissError()">Dismiss</button>
  </div>
</div>

<div id="app">
  <div class="titlebar">
    <div class="titlebar-left">
      <img id="title-img" src="" alt="">
      <div class="titlebar-word">Unblock<span class="r">R</span></div>
    </div>
    <div class="titlebar-right">
      <div class="server-pill">
        <div class="dot" id="server-dot"></div>
        <span id="server-label">UnblockR Status</span>
      </div>
      <span class="plan-pill none" id="plan-pill">No Plan</span>
      <div class="user-pill" id="user-pill" style="display:none">
        <span class="uname" id="user-pill-name"></span>
        <button class="logout-btn" onclick="doLogout()">Logout</button>
      </div>
      <button class="close-btn" onclick="closeApp()">&#x2715;</button>
    </div>
  </div>

  <div class="body">
    <div class="sidebar" id="sidebar">
      <div class="nav-item active" data-page="main"><span class="nav-icon">&#x2B21;</span> Dashboard</div>
      <div class="nav-item" data-page="updates">
        <span class="nav-icon">&#x2191;</span> Updates
        <span class="nav-badge" id="nav-update-badge" style="display:none"></span>
      </div>
      <div class="nav-item" data-page="about"><span class="nav-icon">&#x25C8;</span> About</div>
      <div class="sidebar-bottom">
        <div class="version-tag">v<span id="ver-tag">—</span></div>
        <div class="sub-expiry none" id="sub-expiry"></div>
      </div>
    </div>

    <div class="content">
      <div class="page active" id="page-main">
        <div class="main-grid">
          <div class="disabler-card" id="disabler-card">
            <div class="no-plan-overlay" id="no-plan-overlay" style="display:none"><span>Subscribe to a plan to access this feature</span></div>
            <div class="disabler-header">
              <div class="disabler-title">Linewize Disabler</div>
              <span class="disabler-badge off" id="dis-badge">&#x25CF; Inactive</span>
            </div>
            <div class="disabler-desc">Manipulates Chrome extensions and closes Chrome. Required before activating the proxy. Use the restore button to reverse.</div>
            <div class="disabler-btns">
              <button class="dis-btn activate" id="dis-activate-btn" onclick="activateDisabler()">Activate</button>
              <button class="dis-btn restore" id="dis-restore-btn" onclick="restoreDisabler()" style="display:none">Restore Extensions</button>
            </div>
            <div class="dis-progress" id="dis-progress">
              <div class="dis-prog-row"><span id="dis-msg">Starting...</span><span class="dis-prog-pct" id="dis-pct">0%</span></div>
              <div class="dis-track"><div class="dis-fill" id="dis-fill"></div></div>
            </div>
            <div class="dis-error" id="dis-error"></div>
          </div>

          <div class="toggle-card locked" id="toggle-card">
            <div class="status-label">Active Unblocker</div>
            <div class="status-value off" id="status-val">INACTIVE</div>
            <div class="status-desc" id="status-desc">Removes the annoying 'domain has been blocked'.</div>
            <button class="toggle-btn activate" id="toggle-btn" onclick="toggleProxy()" disabled>
              <span class="btn-dot"></span>
              <span id="toggle-label">Activate UnblockR</span>
            </button>
          </div>

          <div class="stats-col">
            <div class="stat-card green"><div class="stat-label">Allowed</div><div class="stat-val" id="stat-allowed">—</div></div>
            <div class="stat-card red"><div class="stat-label">Blocked</div><div class="stat-val" id="stat-blocked">—</div></div>
            <div class="stat-card blue"><div class="stat-label">Filter size</div><div class="stat-val" id="stat-domains">—</div></div>
          </div>

          <div class="info-strip">
            <span>&#x2B21;</span>
            <span>Connect to <code id="info-proxy-addr">UnblockR</code></span>
            &nbsp;&middot;&nbsp;
            <span>Covers all WinINet apps (Chrome, Edge, Discord, Steam)</span>
          </div>
        </div>
      </div>

      <div class="page" id="page-updates">
        <div class="updates-card">
          <div class="updates-header">
            <img class="updates-logo" id="updates-img" src="" alt="">
            <div class="updates-title">Unblock<span class="r">R</span> Updates</div>
          </div>
          <div class="ver-row">
            <div class="ver-box"><div class="ver-box-label">Installed</div><div class="ver-box-val" id="upd-local">—</div></div>
            <div class="ver-box"><div class="ver-box-label">Latest</div><div class="ver-box-val" id="upd-remote">—</div></div>
          </div>
          <div class="update-status checking" id="upd-status">
            <span class="spinner"></span>
            <span id="upd-status-text">Checking for updates...</span>
          </div>
          <button class="update-btn" id="upd-btn" onclick="openUpdater()" disabled>
            <span class="spinner" id="upd-btn-spinner"></span>
            <span id="upd-btn-label">Checking...</span>
          </button>
        </div>
      </div>

      <div class="page" id="page-about">
        <div class="about-card">
          <div class="about-header">
            <img class="about-logo" id="about-img" src="" alt="UnblockR">
            <div class="about-name">Unblock<span class="r">R</span></div>
          </div>
          <div class="about-ver">Version <span id="about-ver">—</span></div>
          <div class="about-body">UnblockR unblocks all appropriate content like AI and games, but blocks adult content, gambling, malware, and other inappropriate sites across all apps on your device.</div>
          <div class="divider"></div>
          <div class="kv-row"><span class="kv-key">Edition</span><span class="kv-val" id="about-plan">—</span></div>
          <div class="kv-row"><span class="kv-key">Server</span><span class="kv-val" id="about-server">UnblockR</span></div>
          <div class="kv-row"><span class="kv-key">Coverage</span><span class="kv-val">HTTP + HTTPS (domain level)</span></div>
          <div class="kv-row"><span class="kv-key">Safe search</span><span class="kv-val">Google &middot; Bing &middot; YouTube &middot; DDG &middot; Yahoo</span></div>
<div class="kv-row"><span class="kv-key">Built by</span><span class="kv-val">396abc</span></div>
          <div class="divider"></div>
          <button class="dis-btn restore" id="uninstall-btn" onclick="doUninstall()" style="width:100%;text-align:center;">Uninstall UnblockR</button>
        </div>
      </div>
    </div>
  </div>
</div>

<div class="toast warning" id="toast-warning">
  <span class="toast-icon warn">&#x26A0;</span>
  <span id="toast-warning-msg">Cannot close right now.</span>
</div>
<div class="toast info" id="toast-info">
  <span class="toast-icon info">&#x2139;</span>
  <span id="toast-info-msg">Closing...</span>
</div>

<script>
  let proxyActive  = false;
  let appVersion   = '—';
  let userPlan     = null;
  let updateAvail  = false;
  let statsInterval = null;
  let _toastWarnTimer = null;
  let _toastInfoTimer = null;
  let _authMode = 'login';

  function applyLogo(src) {
    if (!src) return;
    ['loader-img','title-img','about-img','updates-img','auth-logo'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.src = src;
    });
  }

  function setProgress(pct, msg) {
    document.getElementById('prog').style.width = pct + '%';
    document.getElementById('loader-status').textContent = msg;
  }

  function showApp() {
    document.getElementById('loader').classList.add('fade-out');
    setTimeout(() => {
      document.getElementById('loader').style.display = 'none';
      document.getElementById('app').classList.add('visible');
    }, 500);
  }

  function showAuthScreen() {
    document.getElementById('loader').classList.add('fade-out');
    setTimeout(() => {
      document.getElementById('loader').style.display = 'none';
      document.getElementById('auth-screen').classList.add('visible');
    }, 500);
  }

  function applyPlanUI(plan) {
    userPlan = plan;
    const pill = document.getElementById('plan-pill');
    const titleWord = document.querySelector('.titlebar-word');
    const aboutPlan = document.getElementById('about-plan');
    const noPlanOverlay = document.getElementById('no-plan-overlay');
    const disCard = document.getElementById('disabler-card');
    const toggleCard = document.getElementById('toggle-card');
    const infoAddr = document.getElementById('info-proxy-addr');
    const serverLabel = document.getElementById('server-label');
    const disActBtn = document.getElementById('dis-activate-btn');
    const tglBtn = document.getElementById('toggle-btn');
    const body = document.getElementById('body');
    
    pill.className = 'plan-pill ' + (plan === 'premium' ? 'premium' : plan === 'home' ? 'home' : 'none');
    
    if (plan === 'premium') {
      pill.textContent = 'PREMIUM';
      if (titleWord) titleWord.innerHTML = 'Unblock<span class="r">R</span> <span style="color:#ffd700;font-size:12px;">PREMIUM</span>';
      if (aboutPlan) aboutPlan.innerHTML = '<span style="color:#ffd700;">PREMIUM</span> — Works Anywhere';
      if (noPlanOverlay) noPlanOverlay.style.display = 'none';
      if (disCard) disCard.classList.remove('locked');
      if (toggleCard) toggleCard.classList.remove('locked');
      if (infoAddr) infoAddr.innerHTML = '<span style="color:#ffd700;">Premium Tunnel</span>';
      if (serverLabel) serverLabel.innerHTML = '<span style="color:#ffd700;">Premium Network</span>';
      if (disActBtn) disActBtn.disabled = false;
      if (tglBtn) tglBtn.disabled = false;
      body.classList.add('premium-active');
    } else if (plan === 'home') {
      pill.textContent = 'HOME';
      if (titleWord) titleWord.innerHTML = 'Unblock<span class="r">R</span> HOME';
      if (aboutPlan) aboutPlan.textContent = 'HOME Edition — Local Network Only';
      if (noPlanOverlay) noPlanOverlay.style.display = 'none';
      if (disCard) disCard.classList.remove('locked');
      if (toggleCard) toggleCard.classList.remove('locked');
      if (infoAddr) infoAddr.textContent = 'static.unblockr.org:8888';
      if (serverLabel) serverLabel.textContent = 'HOME Network';
      if (disActBtn) disActBtn.disabled = false;
      if (tglBtn) tglBtn.disabled = false;
      body.classList.remove('premium-active');
    } else {
      pill.textContent = 'No Plan';
      if (titleWord) titleWord.innerHTML = 'Unblock<span class="r">R</span>';
      if (aboutPlan) aboutPlan.textContent = 'None — Subscribe to activate';
      if (noPlanOverlay) noPlanOverlay.style.display = 'flex';
      if (disCard) disCard.classList.add('locked');
      if (toggleCard) toggleCard.classList.add('locked');
      if (infoAddr) infoAddr.textContent = 'No plan active';
      if (serverLabel) serverLabel.textContent = 'UnblockR Status';
      if (disActBtn) disActBtn.disabled = true;
      if (tglBtn) tglBtn.disabled = true;
      body.classList.remove('premium-active');
    }
  }

  function switchTab(mode) {
    _authMode = mode;
    document.getElementById('tab-login').classList.toggle('active', mode === 'login');
    document.getElementById('tab-signup').classList.toggle('active', mode === 'signup');
    document.getElementById('auth-submit-btn').textContent = mode === 'login' ? 'Sign In' : 'Create Account';
    document.getElementById('auth-error').textContent = '';
  }

  async function submitAuth() {
    const btn  = document.getElementById('auth-submit-btn');
    const user = document.getElementById('auth-username').value.trim();
    const pass = document.getElementById('auth-password').value;
    const err  = document.getElementById('auth-error');
    if (!user || !pass) { err.textContent = 'Please fill in all fields.'; return; }
    btn.disabled = true;
    btn.textContent = 'Please wait...';
    err.textContent = '';
    try {
      const result = _authMode === 'login'
        ? await pywebview.api.do_login(user, pass)
        : await pywebview.api.do_signup(user, pass);
      if (result.success) {
        applyPlanUI(result.plan);
        applyUserState(result.username, result.sub_expires);
        document.getElementById('auth-screen').classList.remove('visible');
        document.getElementById('app').classList.add('visible');
      } else {
        const msgs = {s
          invalid_credentials: 'Incorrect username or password.',
          username_taken: 'Username already taken.',
          no_subscription: 'Account created — contact admin.',
          subscription_expired: 'Your subscription has expired.',
          account_disabled: 'This account has been disabled.',
        };
        err.textContent = msgs[result.error] || result.error || 'Something went wrong.';
        btn.disabled = false;
        btn.textContent = _authMode === 'login' ? 'Sign In' : 'Create Account';
      }
    } catch(e) {
      err.textContent = 'Could not reach server.';
      btn.disabled = false;
      btn.textContent = _authMode === 'login' ? 'Sign In' : 'Create Account';
    }
  }

  document.addEventListener('keydown', e => {
    if (e.key === 'Enter' && document.getElementById('auth-screen').classList.contains('visible')) {
      submitAuth();
    }
  });

  function applyUserState(username, subExpires) {
    const pill = document.getElementById('user-pill');
    if (username) {
      pill.style.display = '';
      document.getElementById('user-pill-name').textContent = username;
    } else {
      pill.style.display = 'none';
    }
    updateSubExpiry(subExpires);
  }

  function updateSubExpiry(subExpires) {
    const subEl = document.getElementById('sub-expiry');
    if (!subExpires) {
      subEl.className = 'sub-expiry none';
      subEl.textContent = 'No subscription';
      return;
    }
    const exp = new Date(subExpires);
    const now = new Date();
    const ok = exp > now;
    subEl.className = 'sub-expiry ' + (ok ? 'ok' : 'exp');
    const dateStr = exp.toLocaleDateString() + ' ' + exp.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
    subEl.textContent = ok ? 'Sub until: ' + dateStr : 'Expired: ' + dateStr;
  }

  async function doLogout() {
    if (proxyActive) {
      await pywebview.api.toggle_proxy();
      applyState({proxy_active:false,online:false,stats:{}});
    }
    await pywebview.api.do_logout();
    applyUserState('', null);
    applyPlanUI(null);
    document.getElementById('auth-username').value = '';
    document.getElementById('auth-password').value = '';
    document.getElementById('auth-error').textContent = '';
    document.getElementById('auth-submit-btn').disabled = false;
    document.getElementById('auth-submit-btn').textContent = 'Sign In';
    switchTab('login');
    document.getElementById('auth-close-btn').style.display = 'flex';
    document.getElementById('app').classList.remove('visible');
    document.getElementById('auth-screen').classList.add('visible');
  }

  function closeAuthScreen() {
    document.getElementById('auth-screen').classList.remove('visible');
    document.getElementById('app').classList.add('visible');
  }

  window._onSubUpdate = function(info) {
    updateSubExpiry(info.sub_expires);
    const plan = info.plan;
    if (plan !== userPlan) {
      applyPlanUI(plan);
      if (!plan && document.getElementById('disabler-card').classList.contains('active')) {
        showWarningToast('Plan removed — restoring extensions...');
        pywebview.api.restore_disabler();
      }
    }
    const btn   = document.getElementById('toggle-btn');
    const label = document.getElementById('toggle-label');
    const card  = document.getElementById('toggle-card');
    const disActive = document.getElementById('disabler-card').classList.contains('active');
    
    if (!info.valid && !proxyActive) {
      btn.className   = 'toggle-btn deactivate';
      btn.disabled    = true;
      btn.style.borderColor = 'rgba(229,80,80,0.4)';
      btn.style.background  = 'rgba(229,80,80,0.08)';
      btn.style.color       = 'var(--off)';
      btn.style.opacity     = '0.7';
      label.textContent = 'Unavailable';
      card.classList.add('locked');
      const msgs = {
        subscription_expired: 'Your subscription has expired.',
        no_subscription: 'No active subscription.',
        account_disabled: 'Your account has been disabled.',
      };
      showWarningToast(msgs[info.reason] || 'Subscription issue.');
    } else if (info.valid && !proxyActive && plan) {
      btn.style.borderColor = '';
      btn.style.background  = '';
      btn.style.color       = '';
      btn.style.opacity     = '';
      if (disActive) {
        btn.className   = 'toggle-btn activate';
        btn.disabled    = false;
        label.textContent = 'Activate UnblockR';
        card.classList.remove('locked');
      } else {
        btn.className   = 'toggle-btn activate';
        btn.disabled    = true;
        label.textContent = 'Activate UnblockR';
      }
    }
  };

  window._onSubKick = function() {
    applyState({proxy_active:false,online:false,stats:{}});
    stopStatsPoll();
    showWarningToast('Proxy deactivated — subscription expired.');
  };

  window._onPlanChange = function(plan) {
    applyPlanUI(plan);
  };

async function boot() {
    setProgress(30, 'Loading...');
    await sleep(200);
    setProgress(70, 'Checking subscription...');
    let result;
    try { result = await pywebview.api.startup(); }
    catch(e) { setProgress(100,'Ready.'); await sleep(200); showApp(); return; }

    applyLogo(result.logo);
    appVersion  = result.version;
    proxyActive = result.proxy_active;
    userPlan    = result.plan;

    document.getElementById('ver-tag').textContent   = appVersion;
    document.getElementById('about-ver').textContent = appVersion;
    document.getElementById('upd-local').textContent = appVersion;

    if (result.logged_in) {
      applyUserState(result.username, result.sub_expires);
    }
    
    applyPlanUI(userPlan);
    
    if (result.disabler_active && !userPlan) {
      setProgress(95, 'Plan expired — restoring extensions...');
      await pywebview.api.restore_disabler();
      await sleep(1000);
    }

    setProgress(100, 'Ready.');
    await sleep(250);
    applyState({proxy_active:proxyActive, online:proxyActive, stats:{}});
    applyDisablerState(result.disabler_active === true && userPlan !== null);

    if (result.logged_in) {
      showApp();
    } else {
      showAuthScreen();
    }
  }

  function onVersionCheck(remoteVer, avail) {
    updateAvail = avail;
    document.getElementById('upd-remote').textContent = remoteVer;
    const badge   = document.getElementById('nav-update-badge');
    const status  = document.getElementById('upd-status');
    const stext   = document.getElementById('upd-status-text');
    const btn     = document.getElementById('upd-btn');
    const bspinner= document.getElementById('upd-btn-spinner');
    const blabel  = document.getElementById('upd-btn-label');
    if (avail) {
      badge.textContent = 'NEW'; badge.className = 'nav-badge new'; badge.style.display = '';
      status.className = 'update-status avail';
      stext.textContent = 'Update available';
    } else {
      badge.style.display = 'none';
      status.className = 'update-status ok';
      stext.textContent = 'You are up to date';
    }
    btn.disabled = false;
    bspinner.style.display = 'none';
    blabel.textContent = 'Open Updater';
  }

  function applyState(result) {
    proxyActive = result.proxy_active;
    const stats  = result.stats || {};
    const online = result.online;
    const dot = document.getElementById('server-dot');
    if (proxyActive && online)  dot.className = 'dot on';
    else if (!proxyActive)      dot.className = 'dot';
    else                        dot.className = 'dot off';
    const card  = document.getElementById('toggle-card');
    const val   = document.getElementById('status-val');
    const desc  = document.getElementById('status-desc');
    const btn   = document.getElementById('toggle-btn');
    const label = document.getElementById('toggle-label');
    const disActive = document.getElementById('disabler-card').classList.contains('active');
    if (proxyActive) {
      card.classList.remove('locked');
      val.className = 'status-value on'; val.textContent = 'ACTIVE';
      desc.textContent = 'All system traffic is routed through UnblockR.';
      btn.className = 'toggle-btn deactivate'; btn.disabled = false;
      label.textContent = 'Deactivate UnblockR';
    } else {
      val.className = 'status-value off'; val.textContent = 'INACTIVE';
      desc.textContent = "Removes the annoying 'domain has been blocked'.";
      btn.className = 'toggle-btn activate';
      label.textContent = 'Activate UnblockR';
      btn.disabled = !disActive || !userPlan;
      if (!disActive || !userPlan) card.classList.add('locked');
      else card.classList.remove('locked');
    }
    function fmt(n) {
      if (!n && n !== 0) return '\u2014';
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
    const disActive = document.getElementById('disabler-card').classList.contains('active');
    if (!userPlan) {
      showWarningToast('Subscribe to a plan to use the proxy.');
      return;
    }
    if (!proxyActive) {
      const subEl = document.getElementById('sub-expiry');
      const subInvalid = subEl.classList.contains('exp') || subEl.classList.contains('none');
      if (subInvalid) {
        showWarningToast('No active subscription.');
        return;
      }
      if (!disActive) {
        showWarningToast('Enable Linewize Disabler before connecting');
        return;
      }
    }
    btn.classList.add('loading');
    label.textContent = proxyActive ? 'Deactivating...' : 'Connecting...';
    try {
      const result = await pywebview.api.toggle_proxy();
      if (result.error === 'server_unreachable') {
        showError();
      } else if (result.error === 'not_logged_in' || result.error === 'token_not_found') {
        doLogout();
      } else if (result.error === 'no_plan') {
        showWarningToast('Subscribe to a plan to use the proxy.');
      } else if (result.error === 'subscription_expired' || result.error === 'no_subscription') {
        showWarningToast('Your subscription has expired.');
      } else {
        applyState(result);
        if (result.proxy_active) startStatsPoll();
        else stopStatsPoll();
      }
    } catch(e) {
      label.textContent = 'Error';
    }
    btn.classList.remove('loading');
  }

  function showError() { document.getElementById('error-overlay').classList.add('visible'); }
  function dismissError() { document.getElementById('error-overlay').classList.remove('visible'); }
  async function retryToggle() {
    const btn = document.querySelector('.retry-btn');
    btn.textContent = 'Checking...'; btn.style.pointerEvents = 'none';
    try {
      const result = await pywebview.api.toggle_proxy();
      if (result.error === 'server_unreachable') {
        btn.textContent = 'Still offline — Retry'; btn.style.pointerEvents = '';
      } else {
        dismissError(); applyState(result);
        if (result.proxy_active) startStatsPoll();
      }
    } catch(e) { btn.textContent = 'Failed — Retry'; btn.style.pointerEvents = ''; }
  }

  function startStatsPoll() {
    stopStatsPoll();
    statsInterval = setInterval(async () => {
      try { const s = await pywebview.api.get_stats(); applyState({proxy_active:proxyActive,online:s.online,stats:s.stats}); } catch(e) {}
    }, 10000);
  }
  function stopStatsPoll() { if (statsInterval) { clearInterval(statsInterval); statsInterval = null; } }

  async function openUpdater() {
    const btn = document.getElementById('upd-btn');
    btn.disabled = true;
    document.getElementById('upd-btn-label').textContent = 'Opening...';
    await pywebview.api.open_updater();
    setTimeout(() => { btn.disabled = false; document.getElementById('upd-btn-label').textContent = 'Open Updater'; }, 2000);
  }

  function applyDisablerState(active) {
    const card        = document.getElementById('disabler-card');
    const badge       = document.getElementById('dis-badge');
    const activateBtn = document.getElementById('dis-activate-btn');
    const restoreBtn  = document.getElementById('dis-restore-btn');
    const toggleCard  = document.getElementById('toggle-card');
    const toggleBtn   = document.getElementById('toggle-btn');
    if (!userPlan) {
      if (activateBtn) activateBtn.disabled = true;
      if (toggleBtn) toggleBtn.disabled = true;
      if (toggleCard) toggleCard.classList.add('locked');
    }
    if (active) {
      if (card) { card.className = 'disabler-card active'; }
      if (badge) { badge.className = 'disabler-badge on'; badge.innerHTML = '&#x25CF; Active'; }
      if (activateBtn) activateBtn.style.display = 'none';
      if (restoreBtn) restoreBtn.style.display = '';
      if (userPlan && toggleBtn) { toggleBtn.disabled = false; }
      if (userPlan && toggleCard) { toggleCard.classList.remove('locked'); }
    } else {
      if (card) { card.className = 'disabler-card'; }
      if (badge) { badge.className = 'disabler-badge off'; badge.innerHTML = '&#x25CF; Inactive'; }
      if (activateBtn) activateBtn.style.display = '';
      if (restoreBtn) restoreBtn.style.display = 'none';
      if (userPlan && toggleBtn) { toggleBtn.disabled = true; }
      if (userPlan && toggleCard) { toggleCard.classList.add('locked'); }
    }
  }

  async function activateDisabler() {
    if (!userPlan) {
      showWarningToast('Subscribe to a plan first.');
      return;
    }
    const btn = document.getElementById('dis-activate-btn');
    btn.disabled = true; btn.textContent = 'Working...';
    document.getElementById('dis-progress').classList.add('visible');
    document.getElementById('dis-error').style.display = 'none';
    const result = await pywebview.api.activate_disabler();
    if (result && result.error === 'no_plan') {
      showWarningToast('Subscribe to a plan first.');
      document.getElementById('dis-progress').classList.remove('visible');
      btn.disabled = false; btn.textContent = 'Activate';
    }
  }

  async function restoreDisabler() {
    const btn = document.getElementById('dis-restore-btn');
    btn.disabled = true; btn.textContent = 'Restoring...';
    document.getElementById('dis-progress').classList.add('visible');
    document.getElementById('dis-error').style.display = 'none';
    if (proxyActive) { await pywebview.api.toggle_proxy(); applyState({proxy_active:false,online:false,stats:{}}); }
    await pywebview.api.restore_disabler();
  }

  window._disablerProgress = function(pct, msg) {
    const fill = document.getElementById('dis-fill');
    const pctEl = document.getElementById('dis-pct');
    const msgEl = document.getElementById('dis-msg');
    if (fill) fill.style.width = pct + '%';
    if (pctEl) pctEl.textContent = pct + '%';
    if (msgEl) msgEl.textContent = msg;
  };
  window._disablerDone = function(isActive) {
    document.getElementById('dis-progress').classList.remove('visible');
    const btn = isActive ? document.getElementById('dis-activate-btn') : document.getElementById('dis-restore-btn');
    if (btn) { btn.disabled = false; btn.textContent = isActive ? 'Activate' : 'Restore Extensions'; }
    applyDisablerState(isActive);
  };
  window._disablerError = function(msg) {
    const err = document.getElementById('dis-error');
    if (err) { err.textContent = 'Error: ' + msg; err.style.display = 'block'; }
    document.getElementById('dis-progress').classList.remove('visible');
    const actBtn = document.getElementById('dis-activate-btn');
    const resBtn = document.getElementById('dis-restore-btn');
    if (actBtn) { actBtn.disabled = false; actBtn.textContent = 'Retry'; }
    if (resBtn) { resBtn.disabled = false; resBtn.textContent = 'Restore Extensions'; }
  };

  function showWarningToast(msg) {
    const t = document.getElementById('toast-warning');
    if (!t) return;
    document.getElementById('toast-warning-msg').textContent = msg;
    t.classList.add('show');
    if (_toastWarnTimer) clearTimeout(_toastWarnTimer);
    _toastWarnTimer = setTimeout(() => t.classList.remove('show'), 3500);
  }
  function showInfoToast(msg) {
    const t = document.getElementById('toast-info');
    if (!t) return;
    document.getElementById('toast-info-msg').textContent = msg;
    t.classList.add('show');
    if (_toastInfoTimer) clearTimeout(_toastInfoTimer);
    _toastInfoTimer = setTimeout(() => t.classList.remove('show'), 3000);
  }
  window.showClosingToast = function() { showInfoToast('Closing...'); };

  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
      document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
      document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
      item.classList.add('active');
      const page = document.getElementById('page-' + item.dataset.page);
      if (page) page.classList.add('active');
    });
  });

  async function closeApp() {
    if (!window.pywebview) return;
    const result = await pywebview.api.close();
    if (result && result.blocked) {
      const msgs = { proxy:'Deactivate the proxy before closing.', disabler:'Wait for the process to finish before closing.' };
      showWarningToast(msgs[result.blocked] || 'Cannot close right now.');
    }
  }

async function doUninstall() {
    if (proxyActive) {
      showWarningToast('Deactivate the proxy before uninstalling.');
      return;
    }
    const btn = document.getElementById('uninstall-btn');
    btn.disabled = true;
    btn.textContent = 'Launching uninstaller...';
    await pywebview.api.launch_uninstaller();
  }

  function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
  window.addEventListener('pywebviewready', boot);
</script>
</body>
</html>"""
# ── Entry point ────────────────────────────────────────────────────────────────
settings = load_settings()
api = API()
icon = str(ICON_PATH) if ICON_PATH.exists() else None

window = webview.create_window(
    "UnblockR",
    html=HTML,
    js_api=api,
    x=settings["window"].get("x", 120),
    y=settings["window"].get("y", 120),
    width=settings["window"].get("w", 960),
    height=settings["window"].get("h", 620),
    resizable=True,
    frameless=True,
    easy_drag=True,
    background_color="#070a0f",
)

api._window_ref = window

threading.Thread(target=poll_subscription, daemon=True).start()

log.info(f"UnblockR v{VERSION} — window ready, starting webview")
log.info(f"LOG FILE: {LOG_PATH}")
log.info(f"CHROME_DIR exists: {CHROME_DIR.exists()}")
log.info(f"APP_DIR: {APP_DIR}")
webview.start(icon=icon, debug=False)
