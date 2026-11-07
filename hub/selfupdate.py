"""Self-update of the hub.

A running program cannot overwrite its own files (on Windows its .exe is
locked). So the hub never installs itself: it

  1. downloads the release zip (installer.download, as for the other apps),
  2. extracts it into a staging folder (extract_zip),
  3. starts a small detached script (apply_and_restart) and exits,
  4. the script waits until the hub's executable is released, copies the
     staged files over the install folder, then starts the new hub.

Like the other apps' zips, the hub's zip only holds program files, so
copying it over the installation leaves the user data (hub config...) alone.
Only a frozen build (PyInstaller) can update itself: from source there is
no executable to replace.
"""
from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath
from typing import Callable, Iterable

WAIT_SECONDS = 90          # how long the script waits for the hub to exit
# Same names and manifest format as installer.py: has_backup() and the
# "Back to <version>" button then work for the hub like for the other apps
BACKUP_DIR = ".hub_backup"
MANIFEST = "manifest.json"


def _clean_env() -> dict[str, str]:
    """An environment stripped of the PyInstaller bootloader variables from the hub,
    ensuring that the launched app (onefile) starts as an independent instance."""
    env = os.environ.copy()
    for k in list(env):
        if k.startswith(("_PYI", "_MEI")):
            env.pop(k, None)
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return env


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def can_self_update() -> bool:
    return is_frozen()


def install_dir() -> Path | None:
    """Folder of the running hub's executable (None when run from source)."""
    return Path(sys.executable).resolve().parent if is_frozen() else None


HANDOFF_FILE = ".hub_handoff.json"    # PIDs of the running apps, for the next hub (runner.py)


def handoff_path() -> Path | None:
    folder = install_dir()
    return folder / HANDOFF_FILE if folder is not None else None


# ── 1. extraction ─────────────────────────────────────────────────────────
def extract_zip(zip_path: Path, dest: Path, exe: str,
                on_progress: Callable[[int, int], None] | None = None) -> None:
    """Extracts the release zip into dest (the zip's root = the install
    folder). Refuses paths escaping dest, keeps the executable bits, and
    accepts a zip wrapped in a single top folder."""
    dest.mkdir(parents=True, exist_ok=True)
    root = dest.resolve()
    with zipfile.ZipFile(zip_path) as z:
        members = z.infolist()
        total = len(members) or 1
        for i, m in enumerate(members, 1):
            target = (dest / m.filename).resolve()
            if target != root and root not in target.parents:
                raise RuntimeError(f"Unsafe path in the zip: {m.filename}")
            z.extract(m, dest)
            mode = m.external_attr >> 16
            if mode and not m.is_dir() and sys.platform != "win32":
                os.chmod(target, mode & 0o777)
            if on_progress:
                on_progress(i, total)
    if not (dest / exe).is_file():
        entries = [p for p in dest.iterdir()]
        if len(entries) == 1 and entries[0].is_dir() and (entries[0] / exe).is_file():
            # Renamed first: on Linux/macOS the wrapper folder and the
            # executable inside can share a name (DwarfiumHub/DwarfiumHub)
            wrapper = entries[0].rename(dest / ".wrapper_tmp")
            for item in wrapper.iterdir():
                shutil.move(str(item), str(dest / item.name))
            wrapper.rmdir()
    if not (dest / exe).is_file():
        raise RuntimeError(f"{exe} not found in the downloaded archive")


# ── 1b. backup / rollback (installer.py's .hub_backup format) ─────────────
def _safe_rel(rel: str) -> PurePosixPath:
    path = PurePosixPath(rel.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise RuntimeError(f"Unsafe path: {rel}")
    return path


def make_backup(stage: Path, target: Path, previous_version: str | None) -> None:
    """Before an update: copies the files the staged release will replace
    into <install>/.hub_backup/ (reading a running exe is allowed, even on
    Windows) and records the files it adds. One previous version is kept."""
    backup = target / BACKUP_DIR
    if backup.exists():
        shutil.rmtree(backup)
    backup.mkdir()
    added = []
    for f in sorted(p for p in stage.rglob("*") if p.is_file()):
        rel = f.relative_to(stage)
        current = target / rel
        if current.is_file():
            saved = backup / rel
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(current, saved)
        else:
            added.append(rel.as_posix())
    (backup / MANIFEST).write_text(json.dumps(
        {"version": previous_version, "added": added, "saved_at": time.strftime("%Y-%m-%d %H:%M:%S")},
        indent=2), encoding="utf-8")


def prepare_rollback(target: Path, stage: Path) -> list[str]:
    """Stages the backed-up files into stage (the relay script copies them
    over the installation) and returns the files the update added, which
    the script removes - what installer.rollback() does, minus the running
    executable that only the script can replace."""
    backup = target / BACKUP_DIR
    try:
        manifest = json.loads((backup / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise RuntimeError("no previous version to go back to")
    stage.mkdir(parents=True, exist_ok=True)
    for saved in backup.rglob("*"):
        if saved.is_file() and saved.name != MANIFEST:
            dest = stage / saved.relative_to(backup)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(saved, dest)
    return [_safe_rel(rel).as_posix() for rel in manifest.get("added", [])]


# ── 2. the relay script ───────────────────────────────────────────────────
def _bat(value: str) -> str:
    return str(value).replace("%", "%%")


def _windows_script(stage: Path, target: Path, exe: str, args: list[str], log: Path,
                    remove: Iterable[str] = (), drop_backup: bool = False) -> str:
    cmd_args = subprocess.list2cmdline(args)
    cleanup = [f'del /F /Q "%TARGET%\\{_bat(rel.replace("/", chr(92)))}" 2>nul' for rel in remove]
    if drop_backup:
        cleanup.append(f'rmdir /S /Q "%TARGET%\\{BACKUP_DIR}" 2>nul')
    return "\r\n".join([
        "@echo off",
        "chcp 65001 >nul",
        "setlocal",
        f'set "TARGET={_bat(target)}"',
        f'set "STAGE={_bat(stage)}"',
        f'set "EXE={_bat(exe)}"',
        f'set "LOG={_bat(log)}"',
        "set /a N=0",
        ":wait",
        "set /a N+=1",
        f"if %N% gtr {WAIT_SECONDS} goto timeout",
        # Appending nothing fails while the exe is still running (locked)
        '(type nul >>"%TARGET%\\%EXE%") 2>nul && goto copy',
        "ping -n 2 127.0.0.1 >nul",
        "goto wait",
        ":copy",
        'robocopy "%STAGE%" "%TARGET%" /E /R:10 /W:2 /NFL /NDL /NJH /NJS /NP >nul',
        "if errorlevel 8 goto copyfail",
        'rmdir /S /Q "%STAGE%" 2>nul',
        *cleanup,
        f'start "" /D "%TARGET%" "%TARGET%\\%EXE%" {_bat(cmd_args)}',
        "goto end",
        ":timeout",
        'echo The hub did not exit in time: update not applied > "%LOG%"',
        "goto end",
        ":copyfail",
        'echo Copy of the new files failed (robocopy code %errorlevel%) > "%LOG%"',
        # Better an old hub than none
        f'start "" /D "%TARGET%" "%TARGET%\\%EXE%" {_bat(cmd_args)}',
        ":end",
        '(goto) 2>nul & del "%~f0"',
        "",
    ])


def _posix_script(stage: Path, target: Path, exe: str, args: list[str], log: Path,
                  remove: Iterable[str] = (), drop_backup: bool = False) -> str:
    q = shlex.quote
    cleanup = [f'  rm -f -- "$TARGET"/{q(rel)}' for rel in remove]
    if drop_backup:
        cleanup.append(f'  rm -rf -- "$TARGET"/{q(BACKUP_DIR)}')
    return "\n".join([
        "#!/bin/sh",
        f"PID={os.getpid()}",
        f"STAGE={q(str(stage))}",
        f"TARGET={q(str(target))}",
        f"EXE={q(exe)}",
        f"LOG={q(str(log))}",
        "i=0",
        'while kill -0 "$PID" 2>/dev/null; do',
        "  i=$((i+1))",
        f'  if [ "$i" -gt {WAIT_SECONDS} ]; then echo "The hub did not exit in time: update not applied" > "$LOG"; rm -f "$0"; exit 1; fi',
        "  sleep 1",
        "done",
        'if cp -R "$STAGE"/. "$TARGET"/; then',
        '  rm -rf "$STAGE"',
        *cleanup,
        "else",
        '  echo "Copy of the new files failed" > "$LOG"',
        "fi",
        'chmod +x "$TARGET/$EXE" 2>/dev/null',
        'cd "$TARGET" || exit 1',
        f'nohup "./$EXE" {" ".join(q(a) for a in args)} >/dev/null 2>&1 &',
        'rm -f "$0"',
        "",
    ])


def apply_and_restart(work: Path, stage: Path, exe: str,
                      remove: Iterable[str] = (), drop_backup: bool = False) -> None:
    """Starts the detached relay script. The caller must exit the hub right
    after (app.shutdown()): the script waits for that. remove / drop_backup
    are for a rollback: files the update had added, and the backup folder."""
    remove = list(remove)
    target = install_dir()
    if target is None:
        raise RuntimeError("Not a packaged hub: nothing to replace")
    exe_rel = Path(exe).name

    args = sys.argv[1:]
    log = target / "update_failed.txt"
    log.unlink(missing_ok=True)
    if sys.platform == "win32":
        script = work / "update.bat"
        script.write_text(_windows_script(stage, target, exe_rel, args, log, remove, drop_backup), encoding="utf-8")
#        script.write_text(_windows_script(stage, target, exe, args, log, remove, drop_backup), encoding="utf-8")
        flags = (subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
                 | subprocess.CREATE_NO_WINDOW)
        #subprocess.Popen(["cmd", "/c", str(script)], creationflags=flags, close_fds=True,
        #                 cwd=tempfile.gettempdir(),
        #                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        subprocess.Popen(["cmd", "/c", str(script)], creationflags=flags, close_fds=True,
                 cwd=tempfile.gettempdir(), env=_clean_env(),
                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    else:
        script = work / "update.sh"
        script.write_text(_posix_script(stage, target, exe, args, log, remove, drop_backup), encoding="utf-8")
        script.chmod(0o755)
        # subprocess.Popen(["/bin/sh", str(script)], start_new_session=True, close_fds=True,
        #                 cwd=tempfile.gettempdir(),
        #                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        subprocess.Popen(["/bin/sh", str(script)], start_new_session=True, close_fds=True,
                         cwd=tempfile.gettempdir(), env=_clean_env(),
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def failure_note() -> str:
    """What a previous update left in update_failed.txt, '' if nothing."""
    target = install_dir()
    if target is None:
        return ""
    log = target / "update_failed.txt"
    try:
        return log.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
