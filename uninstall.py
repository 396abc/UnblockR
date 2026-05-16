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
from pathlib import Path

APP_DIR = Path(os.environ["LOCALAPPDATA"]) / "UnblockR"
SETTINGS = APP_DIR / "settings.json"
START_MENU = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "UnblockR"


def is_proxy_active():
    """Check if a proxy is currently set in Windows."""
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


def is_disabler_active():
    """Check if disabler_active is true in settings.json."""
    try:
        if SETTINGS.exists():
            data = json.loads(SETTINGS.read_text(encoding="utf-8"))
            return data.get("disabler_active", False) is True
        return False
    except Exception:
        return False


def kill_unblockr_processes():
    """Kill any running UnblockR python processes."""
    try:
        result = subprocess.run(
            ["wmic", "process", "where",
             f"commandline like '%{APP_DIR}%' and name='pythonw.exe'",
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
             f"commandline like '%{APP_DIR}%' and name='python.exe'",
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


def main():
    print()
    print("  UnblockR Uninstaller")
    print("  ====================")
    print()

    # check if installed
    if not APP_DIR.exists():
        print("  UnblockR is not installed.")
        print()
        input("  Press Enter to exit...")
        return

    # check proxy
    if is_proxy_active():
        print("  [!] Cannot uninstall: a proxy is currently active.")
        print("      Please disable the proxy in UnblockR before uninstalling.")
        print()
        input("  Press Enter to exit...")
        return

    # check disabler
    if is_disabler_active():
        print("  [!] Cannot uninstall: the disabler is currently active.")
        print("      Please turn off the disabler in UnblockR before uninstalling.")
        print()
        input("  Press Enter to exit...")
        return

    # confirm
    print(f"  This will remove UnblockR from:")
    print(f"  {APP_DIR}")
    print()
    choice = input("  Are you sure? (y/n): ").strip().lower()
    if choice != "y":
        print()
        print("  Uninstall cancelled.")
        print()
        input("  Press Enter to exit...")
        return

    print()
    print("  Stopping UnblockR processes...")
    kill_unblockr_processes()

    print("  Removing application files...")
    try:
        shutil.rmtree(APP_DIR, ignore_errors=True)
        print("  Application directory removed.")
    except Exception as e:
        print(f"  Warning: could not fully remove {APP_DIR}: {e}")

    print("  Removing Start Menu shortcut...")
    try:
        if START_MENU.exists():
            shutil.rmtree(START_MENU, ignore_errors=True)
            print("  Start Menu shortcut removed.")
        else:
            print("  No Start Menu shortcut found.")
    except Exception as e:
        print(f"  Warning: could not remove shortcut: {e}")

    print()
    print("  UnblockR has been uninstalled successfully.")
    print()
    input("  Press Enter to exit...")


if __name__ == "__main__":
    main()
