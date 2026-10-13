"""Latest release of an application on GitHub (public API, no token).

The tags are 'v<version>' (Astro Dwarf Session: v3.2.3) or 'vV<version>'
(Scope Archive: vV3.4.2, its CHANGELOG writes [V3.4.2]); both compare as
plain numbers.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import requests

from hub.apps import AppSpec, asset_name

_API = "https://api.github.com/repos/{repo}/releases/latest"
_TIMEOUT_S = 15


@dataclass
class Release:
    tag: str
    version: str           # tag without its leading v / V
    name: str
    notes: str             # release body (markdown)
    published: str
    asset_url: str | None  # this system's zip, None when the release has none
    asset_size: int
    sha256: str | None     # GitHub's asset digest ("sha256:..."), when given
    page_url: str


def clean_version(tag: str) -> str:
    return re.sub(r"^[vV]+", "", (tag or "").strip())


def version_key(version: str) -> tuple:
    """'3.4.2' < '3.4.10'; text after the numbers (beta...) sorts first."""
    numbers = [int(n) for n in re.findall(r"\d+", clean_version(version).split("-")[0])]
    return tuple(numbers) + ((0,) if "-" in (version or "") else (1,))


def is_newer(latest: str | None, installed: str | None) -> bool:
    if not latest:
        return False
    if not installed:
        return True
    return version_key(latest) > version_key(installed)


def latest_release(app: AppSpec) -> Release:
    """Blocking. Raises requests.RequestException / ValueError."""
    response = requests.get(_API.format(repo=app.repo), timeout=_TIMEOUT_S,
                            headers={"Accept": "application/vnd.github+json"})
    response.raise_for_status()
    data = response.json()
    wanted = asset_name(app)
    asset = next((a for a in data.get("assets", []) if a.get("name") == wanted), None)
    digest = (asset or {}).get("digest") or ""
    return Release(
        tag=data.get("tag_name", ""),
        version=clean_version(data.get("tag_name", "")),
        name=data.get("name") or data.get("tag_name", ""),
        notes=data.get("body") or "",
        published=(data.get("published_at") or "")[:10],
        asset_url=(asset or {}).get("browser_download_url"),
        asset_size=int((asset or {}).get("size") or 0),
        sha256=digest.split(":", 1)[1] if digest.startswith("sha256:") else None,
        page_url=data.get("html_url", ""),
    )
