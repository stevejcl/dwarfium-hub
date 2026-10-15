"""The other Dwarfium Lite installations the hub knows (user-requested
Oct 2026): a source run, a laptop, a mini PC - on the home network or
reached through Tailscale. Kept in hub_config.json ("instances"):

{"id": "a1b2c3", "name": "Mini PC", "kind": "minipc", "access": "tailscale",
 "host": "minipc", "port": 8090, "share": "\\\\minipc\\AstroDwarfSession"}

host + port: its state, read live from Dwarfium Lite's API (/api/app-info,
/api/dwarfs - it listens on every interface). share: its folder, for the
Synchronize tab. Either may be empty (a source run on the same PC has no
share to give: its folder is the share).

access "both" - a laptop or mini PC sometimes at home, sometimes away:
host is its home network address, ts_host its Tailscale one; the home
address is asked first, and the card goes where it answered.

The folders added in the Synchronize tab before this ("sync_folders")
become instances with a share only.
"""
from __future__ import annotations

import ftplib
import socket
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import requests

KINDS = ("release", "dev", "laptop", "minipc", "other")
LAN, TAILSCALE, BOTH = "lan", "tailscale", "both"
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
    ip: str = ""
    ftp: bool | None = None     # its FTP reached from this PC (None: not asked)


@dataclass
class Status:
    state: str
    version: str = ""
    dwarfs: list[Dwarf] = field(default_factory=list)
    via: str = ""       # LAN or TAILSCALE: the address that answered
    host: str = ""


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
                            bool(d.get("connected")), bool(d.get("busy")), bool(d.get("hasPending")),
                            str(d.get("ip") or "")))
    return result


# ── a Dwarf's FTP from this PC ─────────────────────────────────────────────
# Scope Archive downloads a Dwarf's images by FTP (port 21): from the home
# PC, a Dwarf on a remote site's network is reached only through a Tailscale
# subnet router there. Asked once in a while, not at every refresh: the
# Dwarf's FTP server is not to be bothered every 20 s during a capture.
FTP_TTL_S = 300
_ftp_cache: dict[str, tuple[float, bool]] = {}


def ftp_ok(ip: str, fresh: bool = False) -> bool:
    """Blocking. The Dwarf's FTP server answers (its welcome line)."""
    cached = _ftp_cache.get(ip)
    if cached and not fresh and time.monotonic() - cached[0] < FTP_TTL_S:
        return cached[1]
    ok = False
    ftp = ftplib.FTP()
    try:
        ftp.connect(ip, 21, timeout=_TIMEOUT_S)
        ok = True
    except (OSError, EOFError, ftplib.Error):
        ok = False
    finally:
        try:
            ftp.close()
        except OSError:
            pass
    _ftp_cache[ip] = (time.monotonic(), ok)
    return ok


def check_ftp(found: list[Dwarf], fresh: bool = False) -> None:
    """Blocking. ftp set on the connected Dwarfs that have an IP."""
    asked = [d for d in found if d.ip and d.connected]
    if not asked:
        return
    with ThreadPoolExecutor(max_workers=min(4, len(asked))) as pool:
        for d, ok in zip(asked, pool.map(lambda d: ftp_ok(d.ip, fresh), asked)):
            d.ftp = ok


def subnet_of(ip: str) -> str:
    """The /24 network of an IPv4 address (the usual home / site Wi-Fi)."""
    parts = ip.split(".")
    return ".".join(parts[:3]) + ".0/24" if len(parts) == 4 else ""


def status(host: str, port: int, fresh: bool = False) -> Status:
    """Blocking. What answers at host:port (fresh: its Dwarfs' FTP asked
    again now)."""
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
    found = dwarfs(host, port)
    check_ftp(found, fresh)
    return Status(ACTIVE, str(info.get("version") or ""), found)


def share_ok(share: str) -> bool:
    """Blocking (a network share not there can take a while)."""
    try:
        return (Path(share) / "devices.json").is_file()
    except OSError:
        return False


def short_uid(uid: str) -> str:
    from hub.dwarfs import normalize_ble_id
    return normalize_ble_id(uid) or uid


def addresses(inst: dict) -> list[tuple[str, str]]:
    """(via, host) in the order they are asked."""
    host, access = inst.get("host") or "", inst.get("access") or LAN
    if access == BOTH:
        pairs = [(LAN, host), (TAILSCALE, inst.get("ts_host") or "")]
    else:
        pairs = [(TAILSCALE if access == TAILSCALE else LAN, host)]
    return [(via, h) for via, h in pairs if h]


# The address to keep when none has Dwarfium Lite running: one where the
# computer answered beats one not reachable
_ANSWERED = {STOPPED: 2, OTHER: 2, UNREACHABLE: 1}


def status_of(inst: dict, fresh: bool = False) -> Status:
    """Blocking. The first address with Dwarfium Lite running, else the
    one that said the most."""
    port = int(inst.get("port") or DEFAULT_PORT)
    best: Status | None = None
    for via, host in addresses(inst):
        st = status(host, port, fresh)
        st.via, st.host = via, host
        if st.state == ACTIVE:
            return st
        if best is None or _ANSWERED.get(st.state, 0) > _ANSWERED.get(best.state, 0):
            best = st
    if best is not None and best.state == UNREACHABLE:
        best.via = ""       # not reached: where it is isn't known
    return best or Status(NO_ADDRESS)
