"""The hub's version: version.py in the executable (the build writes it
from CHANGELOG.md), else the first [X.Y.Z] of CHANGELOG.md."""
from __future__ import annotations

import re
import sys
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def get_version() -> str:
    if getattr(sys, "frozen", False):
        try:
            from version import APP_VERSION  # written by buildDwarfiumHub.py
            return APP_VERSION
        except ImportError:
            pass
    try:
        text = (Path(__file__).resolve().parent.parent / "CHANGELOG.md").read_text(encoding="utf-8")
        m = re.search(r"\[V?([\d.]+[a-z]?)\]", text)
        return m.group(1) if m else ""
    except OSError:
        return ""
