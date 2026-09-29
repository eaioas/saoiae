"""Автозапуск при входе в систему через LaunchAgent."""

import os
import plistlib
import subprocess
import sys

LABEL = "com.layoutfix.agent"
PLIST_PATH = os.path.expanduser(f"~/Library/LaunchAgents/{LABEL}.plist")
LOG_PATH = os.path.expanduser("~/Library/Logs/LayoutFix.log")
MAIN_PY = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "main.py"))


def is_enabled():
    return os.path.exists(PLIST_PATH)


def enable(python=None):
    """Создать LaunchAgent. Начнёт действовать со следующего входа
    (или сразу после ``launchctl bootstrap``, см. install.sh)."""
    plist = {
        "Label": LABEL,
        "ProgramArguments": [python or sys.executable, MAIN_PY],
        "RunAtLoad": True,
        "KeepAlive": {"SuccessfulExit": False},
        "ProcessType": "Interactive",
        "StandardOutPath": LOG_PATH,
        "StandardErrorPath": LOG_PATH,
    }
    os.makedirs(os.path.dirname(PLIST_PATH), exist_ok=True)
    with open(PLIST_PATH, "wb") as f:
        plistlib.dump(plist, f)


def disable():
    """Удалить LaunchAgent. Текущий процесс продолжает работать до выхода."""
    if os.path.exists(PLIST_PATH):
        os.remove(PLIST_PATH)


def bootout():
    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{LABEL}"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
