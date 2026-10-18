"""Windows: the hub started at the opening of the user's session (user-
requested Oct 2026) - then it starts the applications ticked "Start with the
hub" (hub/watchdog.py). The current user's Run key, no administrator rights
needed; its window opens minimized (--minimized). Only for the built hub
(an executable to start), not when run from source."""
from __future__ import annotations

import sys

_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_NAME = "DwarfiumHub"


def supported() -> bool:
    return sys.platform == "win32" and bool(getattr(sys, "frozen", False))


def _command() -> str:
    return f'"{sys.executable}" --minimized'


def enabled() -> bool:
    if not supported():
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _KEY) as key:
            value, _kind = winreg.QueryValueEx(key, _NAME)
    except OSError:
        return False
    return bool(value)


def set_enabled(on: bool) -> None:
    """Raises OSError when the key can't be written."""
    if not supported():
        return
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _KEY, 0, winreg.KEY_SET_VALUE) as key:
        if on:
            # The hub's current place: moved since, ticking again rewrites it
            winreg.SetValueEx(key, _NAME, 0, winreg.REG_SZ, _command())
        else:
            try:
                winreg.DeleteValue(key, _NAME)
            except FileNotFoundError:
                pass
