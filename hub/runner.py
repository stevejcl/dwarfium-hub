"""Start / stop the applications.

Each app is started from its install folder (its user data is relative
to its working directory) with a fixed port, so the hub - and the other
app - always know where it answers. Started detached: closing the hub
leaves the apps running. Whether an app runs is asked on its port
(GET /api/app-info), so an app started outside the hub (double-click) is
seen too, and another program on that port isn't taken for it.
"""
from __future__ import annotations

import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from hub.apps import AppSpec, exe_name

_procs: dict[str, subprocess.Popen] = {}


def port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex((host, port)) == 0


RUNNING, STARTING, OTHER, STOPPED = "running", "starting", "other", "stopped"


@dataclass(frozen=True)
class Probe:
    # RUNNING, STARTING (started by the hub, not answering yet), OTHER
    # (another program on the port) or STOPPED
    state: str
    version: str | None = None  # the running app's version, when it says it


def _get_json(port: int, path: str):
    response = requests.get(f"http://127.0.0.1:{port}{path}", timeout=2,
                            proxies={"http": None, "https": None})
    return response.json() if response.ok else None


def probe(app: AppSpec, port: int) -> Probe:
    """Blocking: what answers on the app's port. An app the hub started
    that doesn't answer yet (a one-file build unpacks itself first: it can
    take a while) is STARTING."""
    proc = _procs.get(app.id)
    if proc is not None and proc.poll() is not None:
        _procs.pop(app.id, None)
    if not port_in_use(port):
        return Probe(STARTING if started_by_hub(app) else STOPPED)
    try:
        info = _get_json(port, "/api/app-info")
        if isinstance(info, dict) and info.get("app"):
            if info["app"] == app.app_key:
                return Probe(RUNNING, str(info.get("version") or "") or None)
            return Probe(OTHER)
        if app.legacy_probe:            # a version before /api/app-info
            path, key = app.legacy_probe
            data = _get_json(port, path)
            if isinstance(data, dict) and key in data:
                return Probe(RUNNING)
    except (requests.RequestException, ValueError):
        # No HTTP answer (yet): the app the hub just started, still loading?
        if started_by_hub(app):
            return Probe(STARTING)
    return Probe(OTHER)


def started_by_hub(app: AppSpec) -> bool:
    proc = _procs.get(app.id)
    return proc is not None and proc.poll() is None


def start(app: AppSpec, folder: Path, port: int, lan: bool = False) -> None:
    exe = folder / exe_name(app)
    if not exe.is_file():
        raise FileNotFoundError(f"{exe} not found")
    if port_in_use(port):
        raise RuntimeError(f"port {port} already in use")
    args = [str(exe)] + [a.format(port=port) for a in app.args]
    if lan:
        args += list(app.lan_args)
    kwargs: dict = {"cwd": str(folder), "stdin": subprocess.DEVNULL,
                    "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    else:
        kwargs["start_new_session"] = True
    _procs[app.id] = subprocess.Popen(args, **kwargs)


def wait_until_up(app: AppSpec, port: int, timeout_s: float = 60) -> Probe:
    """Blocking: until the app itself answers on its port, it exited, or
    the time is up."""
    end = time.monotonic() + timeout_s
    result = Probe(STOPPED)
    while time.monotonic() < end:
        result = probe(app, port)
        if result.state != STARTING:
            return result               # up, exited, or another program got the port
        time.sleep(0.5)
    return result


def stop(app: AppSpec) -> bool:
    """Stops an app the hub started; False when it wasn't started here."""
    proc = _procs.pop(app.id, None)
    if proc is None or proc.poll() is not None:
        return False
    # A one-file build runs as two processes (the bootloader and the app):
    # stop the whole tree / process group, not only the first one
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        import os
        import signal
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
    return True
