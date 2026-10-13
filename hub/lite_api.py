"""Dwarfium Lite's local API, as the hub uses it (3.2.4+): show one of its
pages in its own window, identify a Dwarf (its ring light flashes)."""
from __future__ import annotations

import requests

_NO_PROXY = {"http": None, "https": None}


def open_page(port: int, path: str) -> bool:
    """Blocking. True when Dwarfium Lite showed the page in its window;
    False (older version, no window, no answer): open a browser instead."""
    try:
        response = requests.post(f"http://127.0.0.1:{port}/api/open-page", json={"path": path},
                                 timeout=5, proxies=_NO_PROXY)
        return response.ok and bool(response.json().get("shown"))
    except (requests.RequestException, ValueError):
        return False


def identify(port: int, ip: str) -> str:
    """Blocking. ok, busy, no_answer, occupied or failed - or lite_old
    (a version without it), lite_unreachable."""
    try:
        response = requests.get(f"http://127.0.0.1:{port}/api/identify", params={"ip": ip},
                                timeout=40, proxies=_NO_PROXY)
    except requests.RequestException:
        return "lite_unreachable"
    if response.status_code == 404:
        return "lite_old"
    try:
        return str(response.json().get("result") or "failed")
    except (ValueError, AttributeError):
        return "failed"
