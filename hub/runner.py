"""Start / stop the applications.

Each app is started from its install folder (its user data is relative
to its working directory) with a fixed port, so the hub - and the other
app - always know where it answers. Started detached: closing the hub
leaves the apps running. Whether an app runs is seen on its port, so an
app started outside the hub (double-click) is seen too.
"""
from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

from hub.apps import AppSpec, exe_name

_procs: dict[str, subprocess.Popen] = {}


def port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex((host, port)) == 0


def is_running(app: AppSpec, port: int) -> bool:
    proc = _procs.get(app.id)
    if proc is not None and proc.poll() is not None:
        _procs.pop(app.id, None)
    return port_in_use(port)


def started_by_hub(app: AppSpec) -> bool:
    proc = _procs.get(app.id)
    return proc is not None and proc.poll() is None


def start(app: AppSpec, folder: Path, port: int) -> None:
    exe = folder / exe_name(app)
    if not exe.is_file():
        raise FileNotFoundError(f"{exe} not found")
    if port_in_use(port):
        raise RuntimeError(f"port {port} already in use")
    args = [str(exe)] + [a.format(port=port) for a in app.args]
    kwargs: dict = {"cwd": str(folder), "stdin": subprocess.DEVNULL,
                    "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    else:
        kwargs["start_new_session"] = True
    _procs[app.id] = subprocess.Popen(args, **kwargs)


def wait_until_up(port: int, timeout_s: float = 60) -> bool:
    """Blocking: until something answers on the port."""
    end = time.monotonic() + timeout_s
    while time.monotonic() < end:
        if port_in_use(port):
            return True
        time.sleep(0.5)
    return False


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
