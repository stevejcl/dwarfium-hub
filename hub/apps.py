"""The applications of the Dwarfium family the hub manages.

Each one is published as GitHub releases holding one zip per system
(<asset_prefix>-<Windows|Linux|macOS>.zip, the contents of its dist/
folder at the zip's root). The zip only holds program files: the user
data the app writes next to its executable (devices, configs, database,
sessions, .nicegui storage...) is never in it, so installing a zip over
an installation leaves that data alone.

A new application is one more AppSpec in APPS.
"""
from __future__ import annotations

import platform
import sys
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AppSpec:
    id: str
    name: str                      # shown in the hub
    repo: str                      # GitHub owner/name
    asset_prefix: str              # <asset_prefix>-<OS>.zip
    exe: str                       # executable name, without .exe
    default_port: int
    folder: str                    # default install folder name
    # Arguments given at start, {port} replaced; the app's working
    # directory is always its install folder (its data is relative to it)
    args: tuple[str, ...] = ("--port", "{port}")
    # Updated by the hub; False for an app that updates itself (the hub
    # then only installs it the first time and starts it)
    hub_updates: bool = True
    # Name the app gives in GET /api/app-info: tells it from another
    # program on its port, and gives its version
    app_key: str = ""
    # Apps older than /api/app-info: (path, JSON key) only this app answers
    legacy_probe: tuple[str, str] | None = None
    # Extra arguments of the "LAN access" option; () = no such option
    lan_args: tuple[str, ...] = ()
    description: str = ""
    extra: dict = field(default_factory=dict)


APPS: tuple[AppSpec, ...] = (
    AppSpec(
        id="scope_archive",
        name="Dwarfium Scope Archive",
        repo="stevejcl/dwarfium-scope-archive",
        asset_prefix="DwarfiumScopeArchive",
        exe="DwarfiumScopeArchive",
        default_port=8080,          # Dwarfium Lite's default Scope Archive URL is http://localhost:8080
        folder="DwarfiumScopeArchive",
        app_key="dwarfium_scope_archive",
        legacy_probe=("/api/peer/status", "astroDwarfSession"),
        lan_args=("--lan",),        # localhost only otherwise
        description="Archive, explore and plan your Dwarf sessions",
    ),
    AppSpec(
        id="astro_dwarf_session",
        name="Dwarfium Lite (Astro Dwarf Session)",
        repo="stevejcl/astro_dwarf_session",
        asset_prefix="AstroDwarfUI",
        exe="AstroDwarfUI",
        default_port=8090,
        folder="AstroDwarfSession",
        app_key="astro_dwarf_session",
        legacy_probe=("/api/dwarfs", "devices"),
        # Always reachable from the LAN (binds 0.0.0.0): no LAN option
        description="Control your Dwarfs, programs and schedules",
    ),
)

APPS_BY_ID = {a.id: a for a in APPS}


def os_suffix() -> str:
    """The release asset suffix for this system (the builds' RUNNER_OS)."""
    system = platform.system()
    if system == "Windows":
        return "Windows"
    if system == "Darwin":
        return "macOS"
    return "Linux"


def asset_name(app: AppSpec) -> str:
    return f"{app.asset_prefix}-{os_suffix()}.zip"


def exe_name(app: AppSpec) -> str:
    return app.exe + (".exe" if sys.platform == "win32" else "")
