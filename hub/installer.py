"""Download, install / update and roll back an application.

An update never removes anything: the release zip (program files only)
is laid over the installation file by file, so every file the app wrote
itself (devices, configs, database, sessions, .nicegui...) stays as it
is - also in the folders that mix both (Astro Dwarf Session's assets/,
Scope Archive's db/). Before that, each file the zip replaces is copied
to <install>/.hub_backup/ (one previous version kept): rollback() puts
them back and removes the files the update added.

<install>/.hub_version.json records the version the hub installed.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath
from typing import Callable

import requests

VERSION_FILE = ".hub_version.json"
BACKUP_DIR = ".hub_backup"
_MANIFEST = "manifest.json"
_CHUNK = 1 << 20


class InstallError(Exception):
    pass


# ── version ───────────────────────────────────────────────────────────────
def installed_version(target: Path) -> str | None:
    try:
        return json.loads((target / VERSION_FILE).read_text(encoding="utf-8")).get("version")
    except (OSError, ValueError):
        return None


def _write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def has_backup(target: Path) -> str | None:
    """Version a rollback would go back to, or None."""
    try:
        return json.loads((target / BACKUP_DIR / _MANIFEST).read_text(encoding="utf-8")).get("version") or "?"
    except (OSError, ValueError):
        return None


# ── download ──────────────────────────────────────────────────────────────
def download(url: str, dest: Path, expected_sha256: str | None,
             progress: Callable[[int, int], None] | None = None,
             cancelled: Callable[[], bool] | None = None) -> Path:
    """Blocking. Streams to dest, checks the SHA-256 when GitHub gives one."""
    digest = hashlib.sha256()
    with requests.get(url, stream=True, timeout=30) as response:
        response.raise_for_status()
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        with open(dest, "wb") as f:
            for chunk in response.iter_content(_CHUNK):
                if cancelled and cancelled():
                    raise InstallError("cancelled")
                f.write(chunk)
                digest.update(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)
    if expected_sha256 and digest.hexdigest().lower() != expected_sha256.lower():
        dest.unlink(missing_ok=True)
        raise InstallError("checksum mismatch: the download is damaged, try again")
    return dest


# ── install / update ──────────────────────────────────────────────────────
def _members(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    """Files of the zip, with safe relative paths only."""
    out = []
    for info in archive.infolist():
        if info.is_dir():
            continue
        path = PurePosixPath(info.filename.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise InstallError(f"unsafe path in the archive: {info.filename}")
        if path.parts[0] in (BACKUP_DIR, VERSION_FILE):
            continue
        out.append(info)
    return out


def install(zip_path: Path, target: Path, version: str, exe: str,
            progress: Callable[[int, int], None] | None = None) -> None:
    """Lays the zip over target (created if needed). The app must not be
    running (its executable would be locked on Windows)."""
    with zipfile.ZipFile(zip_path) as archive:
        members = _members(archive)
        names = {PurePosixPath(m.filename.replace("\\", "/")).as_posix() for m in members}
        if exe not in names and not any(n.startswith(exe + ".app/") for n in names):
            raise InstallError(f"{exe} is not in the archive: wrong file?")
        target.mkdir(parents=True, exist_ok=True)

        # Previous version's files about to be replaced -> .hub_backup/
        backup = target / BACKUP_DIR
        if backup.exists():
            shutil.rmtree(backup)
        backup.mkdir()
        added = []
        for m in members:
            rel = PurePosixPath(m.filename.replace("\\", "/"))
            current = target.joinpath(*rel.parts)
            if current.is_file():
                saved = backup.joinpath(*rel.parts)
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(current, saved)
            else:
                added.append(rel.as_posix())
        previous = installed_version(target)
        if previous is None and len(added) == len(members):
            shutil.rmtree(backup)      # first install: no previous version to go back to
            backup = None
        else:
            # previous None = installed outside the hub: still restorable
            _write_json(backup / _MANIFEST, {"version": previous, "added": added,
                                              "saved_at": time.strftime("%Y-%m-%d %H:%M:%S")})

        # New files, each written beside then renamed over the old one
        for i, m in enumerate(members, 1):
            rel = PurePosixPath(m.filename.replace("\\", "/"))
            dest = target.joinpath(*rel.parts)
            dest.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=dest.parent, prefix=".hub_new_")
            with os.fdopen(fd, "wb") as out, archive.open(m) as src:
                shutil.copyfileobj(src, out, _CHUNK)
            mode = (m.external_attr >> 16) & 0o777
            if mode:
                os.chmod(tmp, mode)
            elif dest.name == exe:
                os.chmod(tmp, 0o755)
            os.replace(tmp, dest)
            if progress:
                progress(i, len(members))

    exe_path = target / exe
    if exe_path.exists() and os.name != "nt":
        exe_path.chmod(exe_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    _write_json(target / VERSION_FILE, {"version": version, "installed_at": time.strftime("%Y-%m-%d %H:%M:%S")})


def rollback(target: Path) -> str | None:
    """Back to the version before the last update; returns it."""
    backup = target / BACKUP_DIR
    try:
        manifest = json.loads((backup / _MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise InstallError("no previous version to go back to")
    for rel in manifest.get("added", []):
        (target / rel).unlink(missing_ok=True)
    for saved in backup.rglob("*"):
        if saved.is_file() and saved.name != _MANIFEST:
            dest = target / saved.relative_to(backup)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(saved, dest)
    previous = manifest.get("version")
    if previous:
        _write_json(target / VERSION_FILE, {"version": previous, "installed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                                            "rolled_back": True})
    else:
        (target / VERSION_FILE).unlink(missing_ok=True)
    shutil.rmtree(backup)
    return previous
