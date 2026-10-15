"""The other Dwarfium Lite installations the hub knows (user-requested
Oct 2026): a source run, a laptop, a mini PC - on the home network or
reached through Tailscale. Kept in hub_config.json ("instances"):

{"id": "a1b2c3", "name": "Mini PC", "kind": "minipc", "access": "tailscale",
 "host": "minipc", "port": 8090, "share": "\\\\minipc\\AstroDwarfSession"}

host + port: its state, read live from Dwarfium Lite's API (/api/app-info,
/api/dwarfs - it listens on every interface). share: its folder, for the
Synchronize tab. Either may be empty (a source run on the same PC has no
share to give: its folder is the share).

The folders added in the Synchronize tab before this ("sync_folders")
become instances with a share only.
"""
from __future__ import annotations

import socket
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import requests

KINDS = ("dev", "laptop", "minipc", "other")
LAN, TAILSCALE = "lan", "tailscale"
DEFAULT_PORT = 8090

# Live state of an instance
ACTIVE, STOPPED, UNREACHABLE, OTHER, NO_ADDRESS = "active", "stopped", "unreachable", "other", "no_address"

_NO_PROXY = {"http": None, "https": None}
_TIMEOUT_S = 3


def new_id() -> str:
    return uuid.uuid4().hex[:8]


def migrate(cfg: dict) -> bool:
    """The Synchronize tab's folders as instances. True when cfg changed."""
    instances = cfg.setdefault("instances", [])
    shares = {i.get("share") for i in instances}
    changed = False
    for folder in cfg.pop("sync_folders", []) or []:
        changed = True
        if folder not in shares:
            instances.append({"id": new_id(), "name": Path(folder).name or folder, "kind": "other",
                              "access": LAN, "host": "", "port": DEFAULT_PORT, "share": folder})
            shares.add(folder)
    return changed


def shares(cfg: dict) -> list[str]:
    return [i["share"] for i in cfg.get("instances", []) if i.get("share")]


def by_share(cfg: dict, share: str) -> dict | None:
    return next((i for i in cfg.get("instances", []) if i.get("share") == share), None)


@dataclass
class Dwarf:
    name: str
    uid: str
    model: str
    connected: bool
    busy: bool
    pending: bool


@dataclass
class Status:
    state: str
    version: str = ""
    dwarfs: list[Dwarf] = field(default_factory=list)


def _reachable(host: str, port: int) -> str:
    """ACTIVE when something listens, STOPPED when the machine refuses
    (it is there, Dwarfium Lite isn't), else UNREACHABLE (off, wrong name,
    Tailscale down)."""
    try:
        with socket.create_connection((host, port), timeout=_TIMEOUT_S):
            return ACTIVE
    except ConnectionRefusedError:
        return STOPPED
    except OSError:
        return UNREACHABLE


def dwarfs(host: str, port: int) -> list[Dwarf]:
    """Blocking. The Dwarfs of a Dwarfium Lite (its virtual "auto:" entries
    left out); [] when it doesn't answer."""
    try:
        response = requests.get(f"http://{host}:{port}/api/dwarfs", timeout=_TIMEOUT_S, proxies=_NO_PROXY)
        devices = response.json().get("devices") or []
    except (requests.RequestException, ValueError, AttributeError):
        return []
    result = []
    for d in devices:
        if not isinstance(d, dict):
            continue
        uid = str(d.get("dwarfUid") or "")
        if uid.startswith("auto:"):
            continue
        result.append(Dwarf(str(d.get("name") or uid), uid, str(d.get("model") or ""),
                            bool(d.get("connected")), bool(d.get("busy")), bool(d.get("hasPending"))))
    return result


def status(host: str, port: int) -> Status:
    """Blocking. What answers at host:port."""
    if not host:
        return Status(NO_ADDRESS)
    state = _reachable(host, port)
    if state != ACTIVE:
        return Status(state)
    try:
        response = requests.get(f"http://{host}:{port}/api/app-info", timeout=_TIMEOUT_S, proxies=_NO_PROXY)
        info = response.json()
    except (requests.RequestException, ValueError):
        return Status(OTHER)
    if not isinstance(info, dict) or info.get("app") != "astro_dwarf_session":
        return Status(OTHER)
    return Status(ACTIVE, str(info.get("version") or ""), dwarfs(host, port))


def share_ok(share: str) -> bool:
    """Blocking (a network share not there can take a while)."""
    try:
        return (Path(share) / "devices.json").is_file()
    except OSError:
        return False


def short_uid(uid: str) -> str:
    from hub.dwarfs import normalize_ble_id
    return normalize_ble_id(uid) or uid
