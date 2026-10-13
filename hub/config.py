"""The hub's own settings: hub_config.json next to the hub (its working
folder when run from source), written atomically.

{
  "install_root": "C:/Dwarfium",
  "language": "fr",
  "apps": {"scope_archive": {"path": "C:/Dwarfium/DwarfiumScopeArchive", "port": 8080}, ...}
}
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path


def hub_dir() -> Path:
    """Folder of the hub executable (frozen) or the current folder."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()


CONFIG_FILE = hub_dir() / "hub_config.json"


def default_install_root() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("SystemDrive", "C:") + "\\") / "Dwarfium"
    return Path.home() / "Dwarfium"


def load() -> dict:
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    data.setdefault("install_root", str(default_install_root()))
    data.setdefault("apps", {})
    return data


def save(data: dict) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=CONFIG_FILE.parent, prefix=".hub_config.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, CONFIG_FILE)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def app_settings(data: dict, app_id: str) -> dict:
    return data["apps"].setdefault(app_id, {})
