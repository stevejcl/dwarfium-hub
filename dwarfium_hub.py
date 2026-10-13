"""Dwarfium-Hub: installs, updates and starts the Dwarfium applications
(Dwarfium Lite / Astro Dwarf Session, Dwarfium Scope Archive).

    python dwarfium_hub.py              # native window
    python dwarfium_hub.py --no_native  # in a browser (http://127.0.0.1:<port>)
"""
from __future__ import annotations

import argparse
import socket
from multiprocessing import freeze_support


def _free_port(start: int = 8790, end: int = 8899) -> int:
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Dwarfium-Hub")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--no_native", action="store_true", help="open in a browser instead of a window")
    args, _ = parser.parse_known_args()

    from nicegui import ui

    from hub import ui as hub_ui
    from hub.app_version import get_version

    hub_ui.register()
    native = not args.no_native
    # window_size alone turns native mode on: only given with a window
    window = {"native": True, "window_size": (980, 820)} if native else {"native": False, "show": True}
    ui.run(
        title=f"Dwarfium-Hub {get_version()}",
        host="127.0.0.1",
        port=args.port or _free_port(),
        reload=False,
        favicon="🔭",
        **window,
    )


if __name__ in {"__main__", "__mp_main__"}:
    freeze_support()
    main()
