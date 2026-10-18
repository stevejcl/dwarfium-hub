"""Launcher and watchdog (user-requested Oct 2026): the hub starts the
applications ticked "Start with the hub" when it starts - with Windows too,
hub/autorun.py - and starts again the ones ticked "Restart automatically"
that stopped by themselves.

Runs in the hub's own process, not in its page: a window reloaded or closed
leaves it running. Only an application the hub started can be restarted:
its process gives an exit code (runner.take_exit). 0 is a normal close - its
window closed by the user, not restarted; anything else a crash. Stopped
from the hub (its Stop button, an update, Synchronize) is never seen as an
exit at all. At most MAX_RESTARTS within RESTART_WINDOW_S, then it gives up
(shown on its card) until the box is ticked again - an application that
crashes at once isn't started over and over.
"""
from __future__ import annotations

import asyncio
import time

from nicegui import run

from hub import config, runner
from hub.apps import APPS, AppSpec, exe_name
from hub.i18n import t

CHECK_S = 15                # how often the applications are looked at
START_GAP_S = 5             # between the applications started at startup
MAX_RESTARTS = 3
RESTART_WINDOW_S = 10 * 60

_restarts: dict[str, list[float]] = {}      # app id -> its restart times
_gave_up: set[str] = set()
_last: dict[str, str] = {}                  # app id -> what was last done


def _installed(cfg: dict, spec: AppSpec) -> bool:
    return (config.app_folder(cfg, spec) / exe_name(spec)).is_file()


def _flag(cfg: dict, spec: AppSpec, key: str) -> bool:
    return bool(config.app_settings(cfg, spec.id).get(key))


def gave_up(app_id: str) -> bool:
    return app_id in _gave_up


def forgive(app_id: str) -> None:
    """"Restart automatically" ticked again: a fresh count."""
    _gave_up.discard(app_id)
    _restarts.pop(app_id, None)


def status(app_id: str) -> str:
    """The card's line about it ("" when nothing happened)."""
    return _last.get(app_id, "")


async def _start(cfg: dict, spec: AppSpec) -> bool:
    """Starts it when nothing answers on its port. True when it answers."""
    port = config.app_port(cfg, spec)
    state = await run.io_bound(runner.probe, spec, port)
    if state.state in (runner.RUNNING, runner.STARTING):
        return True
    if state.state == runner.OTHER:
        print(f"[hub] {spec.name}: port {port} used by another program - not started")
        return False
    try:
        await run.io_bound(runner.start, spec, config.app_folder(cfg, spec), port, config.app_lan(cfg, spec))
    except Exception as e:
        print(f"[hub] {spec.name} not started: {e!r}")
        return False
    state = await run.io_bound(runner.wait_until_up, spec, port, 180)
    return state.state in (runner.RUNNING, runner.STARTING)


async def _autostart() -> None:
    cfg = config.load()
    first = True
    for spec in APPS:       # Scope Archive first: Dwarfium Lite says hello to it
        if not (_installed(cfg, spec) and _flag(cfg, spec, "autostart")):
            continue
        if not first:
            await asyncio.sleep(START_GAP_S)
        first = False
        if await _start(cfg, spec):
            _last[spec.id] = t("wd_autostarted", time=time.strftime("%H:%M"))


async def _check() -> None:
    cfg = config.load()
    for spec in APPS:
        if not _installed(cfg, spec):
            continue
        # probe() records the exit of a process the hub started
        await run.io_bound(runner.probe, spec, config.app_port(cfg, spec))
        code = runner.take_exit(spec)
        if code is None:
            continue
        if code == 0:
            _last[spec.id] = t("wd_closed", time=time.strftime("%H:%M"))
            continue
        if not _flag(cfg, spec, "restart") or spec.id in _gave_up:
            _last[spec.id] = t("wd_crashed", time=time.strftime("%H:%M"), code=code)
            continue
        now = time.time()
        recent = [s for s in _restarts.get(spec.id, []) if now - s < RESTART_WINDOW_S]
        if len(recent) >= MAX_RESTARTS:
            _gave_up.add(spec.id)
            _last[spec.id] = t("wd_gave_up", n=MAX_RESTARTS, minutes=RESTART_WINDOW_S // 60)
            print(f"[hub] {spec.name}: stopped {MAX_RESTARTS} times within {RESTART_WINDOW_S // 60} min - no more restart")
            continue
        _restarts[spec.id] = recent + [now]
        print(f"[hub] {spec.name} stopped by itself (exit code {code}): restarting it")
        ok = await _start(cfg, spec)
        _last[spec.id] = t("wd_restarted" if ok else "wd_restart_failed",
                           time=time.strftime("%H:%M"), code=code, n=len(recent) + 1)


async def watch() -> None:
    """The hub's background task (dwarfium_hub.py): startup, then a check
    every CHECK_S. Never ends on an error."""
    try:
        await _autostart()
    except Exception as e:
        print(f"[hub] autostart failed: {e!r}")
    while True:
        await asyncio.sleep(CHECK_S)
        try:
            await _check()
        except Exception as e:
            print(f"[hub] watchdog check failed: {e!r}")
