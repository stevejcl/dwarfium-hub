"""Start / stop the applications.

Each app is started from its install folder (its user data is relative
to its working directory) with a fixed port, so the hub - and the other
app - always know where it answers. Started detached: closing the hub
leaves the apps running. Whether an app runs is asked on its port
(GET /api/app-info), so an app started outside the hub (double-click) is
seen too, and another program on that port isn't taken for it.
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import requests

import multiprocessing
import os
import sys

from hub.apps import AppSpec, exe_name
from hub.selfupdate import _clean_env

_procs: dict[str, subprocess.Popen] = {}
# Exit code of an app the hub started that ended by itself (not stopped
# from the hub): read by the watchdog (hub/watchdog.py)
_exits: dict[str, int] = {}


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
        _exits[app.id] = proc.returncode
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


def take_exit(app: AppSpec) -> int | None:
    """The exit code of the app the hub started, once, when it ended by
    itself since the last call (seen by probe()); None otherwise."""
    return _exits.pop(app.id, None)


def started_by_hub(app: AppSpec) -> bool:
    proc = _procs.get(app.id)
    return proc is not None and proc.poll() is None


# ── hand-over to the next hub (self-update) ───────────────────────────────
# The apps are detached, so they outlive the hub. Right before the hub exits
# to update itself it writes their PIDs (save_handoff); the new hub takes
# them over (adopt_handoff) so Stop / Show / auto-restart keep working for
# apps the previous hub started. Only for that short hand-over: the file is
# read once, deleted, and ignored when old (a recycled PID could be anything).
HANDOFF_MAX_AGE_S = 600


def _pid_alive(pid: int) -> bool:
    if sys.platform == "win32":
        import ctypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel32.OpenProcess(0x1000, False, pid)       # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            return bool(kernel32.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:                                # a zombie is gone for our purpose
        with open(f"/proc/{pid}/stat", encoding="utf-8") as f:
            return f.read().rsplit(")", 1)[1].split()[0] != "Z"
    except (OSError, IndexError):
        return True


class AdoptedProcess:
    """A process the previous hub started, taken over after a hub restart.
    Popen-like for what this module and the page use: pid, poll(), wait(),
    kill(), returncode. Its real exit code can't be known (not our child):
    0, so the watchdog reads it as a normal close, not a crash."""

    def __init__(self, pid: int):
        self.pid = pid
        self.returncode: int | None = None

    def poll(self) -> int | None:
        if self.returncode is None and not _pid_alive(self.pid):
            self.returncode = 0
        return self.returncode

    def wait(self, timeout: float | None = None) -> int | None:
        end = None if timeout is None else time.monotonic() + timeout
        while self.poll() is None:
            if end is not None and time.monotonic() >= end:
                raise subprocess.TimeoutExpired(str(self.pid), timeout)
            time.sleep(0.1)
        return self.returncode

    def kill(self) -> None:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/PID", str(self.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            import signal
            try:
                os.kill(self.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


def save_handoff(path: Path) -> int:
    """Writes the PIDs of the apps still running that the hub started.
    Returns how many."""
    procs = {app_id: proc.pid for app_id, proc in _procs.items() if proc.poll() is None}
    path.write_text(json.dumps({"saved_at": time.time(), "procs": procs}), encoding="utf-8")
    return len(procs)


def adopt_handoff(path: Path, max_age_s: float = HANDOFF_MAX_AGE_S) -> list[str]:
    """Takes over the apps the previous hub left (once: the file is deleted).
    Returns the ids adopted."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    path.unlink(missing_ok=True)
    if not isinstance(data, dict) or time.time() - float(data.get("saved_at") or 0) > max_age_s:
        return []
    adopted = []
    for app_id, pid in (data.get("procs") or {}).items():
        if app_id in _procs or not isinstance(pid, int) or pid <= 0:
            continue
        if _pid_alive(pid):
            _procs[app_id] = AdoptedProcess(pid)
            adopted.append(app_id)
    return adopted


def start(app: AppSpec, folder: Path, port: int, lan: bool = False) -> None:
    _exits.pop(app.id, None)            # an earlier run's: not this one's
    exe = folder / exe_name(app)
    if not exe.is_file():
        raise FileNotFoundError(f"{exe} not found")
    if port_in_use(port):
        raise RuntimeError(f"port {port} already in use")
    args = [str(exe)] + [a.format(port=port) for a in app.args]
    if lan:
        args += list(app.lan_args)

    kwargs: dict = {"cwd": str(folder), "stdin": subprocess.DEVNULL,
                "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL,
                "env": _clean_env()}

    # kwargs: dict = {"cwd": str(folder), "stdin": subprocess.DEVNULL,
    #                "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}

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


def bring_to_front(app: AppSpec) -> bool:
    """True when the window was found and brought to front (Windows)."""
    if not sys.platform.startswith("win"):
        return False

    proc = _procs.get(app.id)
    child_pids = set()

    if proc is not None and proc.poll() is None:
        try:
            import psutil
            child_pids = {
                child.pid
                for child in psutil.Process(proc.pid).children(recursive=True)
            }
        except Exception:
            pass
    else:
        print(f"bring_to_front: proc not tracked or manual start, falling back to title search")

    import ctypes
    from ctypes import wintypes
    title_part = app.win_name
    print(f"bring_to_front title:{title_part}")

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    by_child: list[int] = []
    by_self: list[int] = []
    by_title: list[int] = []

    enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def _visit(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if not length:
            return True
        title = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title, length + 1)
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in child_pids:
            by_child.append(hwnd)
        elif pid.value == os.getpid():
            by_self.append(hwnd)
        elif title.value.startswith(title_part):  # not "... - Google Chrome"
            by_title.append(hwnd)
        return True

    user32.EnumWindows(enum_proc(_visit), 0)
    candidates = by_child or by_self or by_title
    if not candidates:
        return False
    hwnd = candidates[0]

    sw_restore = 9
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, sw_restore)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    this_thread = kernel32.GetCurrentThreadId()
    user32.GetForegroundWindow.restype = wintypes.HWND
    foreground = user32.GetForegroundWindow()
    foreground_thread = user32.GetWindowThreadProcessId(foreground, None) if foreground else 0
    attached = bool(foreground_thread) and foreground_thread != this_thread and bool(
        user32.AttachThreadInput(this_thread, foreground_thread, True)
    )
    try:
        user32.BringWindowToTop(hwnd)
        return bool(user32.SetForegroundWindow(hwnd))
    finally:
        if attached:
            user32.AttachThreadInput(this_thread, foreground_thread, False)
