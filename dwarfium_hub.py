"""Dwarfium-Hub: installs, updates and starts the Dwarfium applications
(Dwarfium Lite / Astro Dwarf Session, Dwarfium Scope Archive).

    python dwarfium_hub.py              # native window
    python dwarfium_hub.py --no_native  # in a browser (http://127.0.0.1:<port>)
    python dwarfium_hub.py --minimized  # window minimized (started with Windows)
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import socket
import sys
from multiprocessing import freeze_support


def _free_port(start: int = 8790, end: int = 8899) -> int:
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return 0


# The Applications tab without a scrollbar, both cards with their update /
# rollback buttons and the watchdog's lines, plus the title bar (user-requested)
WINDOW_WIDTH, WINDOW_HEIGHT = 1000, 1050


def _window_height(wanted: int = WINDOW_HEIGHT) -> int:
    """At most the screen's height without the taskbar (Windows' work
    area): a window taller than the screen can't be seen whole."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            rect = wintypes.RECT()
            # SPI_GETWORKAREA = 0x0030
            if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
                return max(600, min(wanted, rect.bottom - rect.top))
        except Exception:
            pass
    return wanted


def _suppress_benign_proactor_noise(loop: asyncio.AbstractEventLoop, context: dict) -> None:
    """Windows: a connection the window or browser already reset (closing
    the hub, a page reloaded) makes asyncio's Proactor loop print
    "ConnectionResetError [WinError 10054]" from _call_connection_lost -
    harmless cleanup noise, logged at DEBUG instead (the same filter as
    Dwarfium Lite's). Anything else goes to the default handler."""
    exception = context.get("exception")
    marker = f"{context.get('message', '')} {context.get('handle', '')}"
    if isinstance(exception, ConnectionResetError) and "_call_connection_lost" in marker:
        logging.getLogger("asyncio").debug("Suppressed benign Proactor cleanup noise: %r", exception)
        return
    loop.default_exception_handler(context)


def main() -> None:
    parser = argparse.ArgumentParser(description="Dwarfium-Hub")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--no_native", action="store_true", help="open in a browser instead of a window")
    # Started with Windows (hub/autorun.py): its window minimized
    parser.add_argument("--minimized", action="store_true", help="open the window minimized")
    args, _ = parser.parse_known_args()

    from nicegui import ui

    from hub import ui as hub_ui
    from hub.app_version import get_version
    from hub.logo import LOGO_SVG

    hub_ui.register()
    from nicegui import app, background_tasks
    from hub import watchdog
    # Starts the applications ticked "Start with the hub", then restarts the
    # ones that stopped by themselves - in the hub's process, not its page
    app.on_startup(lambda: background_tasks.create(watchdog.watch(), name="hub-watchdog"))
    if sys.platform == "win32":
        # On the running loop: there is none before ui.run() starts it
        app.on_startup(lambda: asyncio.get_running_loop().set_exception_handler(_suppress_benign_proactor_noise))
    native = not args.no_native
    # window_size alone turns native mode on: only given with a window
    window = ({"native": True, "window_size": (WINDOW_WIDTH, _window_height())} if native
              else {"native": False, "show": True})
    if native and args.minimized:
        app.native.window_args["minimized"] = True
    ui.run(
        title=f"Dwarfium-Hub {get_version()}",
        host="127.0.0.1",
        port=args.port or _free_port(),
        reload=False,
        favicon=LOGO_SVG,
        **window,
    )


if __name__ in {"__main__", "__mp_main__"}:
    freeze_support()
    main()
