"""Synchronization of two Dwarfium Lite (Astro Dwarf Session) installations
(user-requested Oct 2026): the .exe and a source run, a laptop taken to
the field, an installation on a mini PC reached through a Windows share.
Both ways: each side gets what it lacks; a program at two stages keeps
the most advanced one.

What an installation holds (all relative to its folder):
- devices.json + config_<name>.py / .ini per Dwarf,
- per Dwarf, Devices_Sessions/<name>/Astro_Sessions/{ToDo, Current,
  Done, Error, Results} (Astro_Sessions/ at the root for config.py, the
  "Default" profile) - one JSON file per program,
- sites.json (observing sites, by name) and device_prefs.json (per Dwarf
  UID: hidden, position).

The same Dwarf is found on both sides by its identifier (the 6 hex digits
ending its Bluetooth name, DWARF_UID), never by its config file name: it
may be config_d3 here and config_dwarf3 there. A program is found by its
id_command.uuid (its file is renamed on the way to Done / Error), else by
its file name without the date prefix Done / Error files get.

compare() only reads and returns the list of actions (what goes where,
and why); apply() writes the chosen ones, after a zip backup of both
sides. Dwarfium Lite must be stopped on both sides meanwhile: it reads
these files when it starts and writes them while it runs.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from hub.dwarfs import LiteDwarf, normalize_ble_id, read_lite

STATES = ("ToDo", "Current", "Done", "Error")
# A program's progress: the most advanced copy wins
_RANK = {"ToDo": 1, "Current": 2, "Done": 3, "Error": 3}
_DATE_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}_")
BACKUP_DIR = "sync_backups"

A2B, B2A = "a2b", "b2a"
# Action kinds
DEVICE, PROGRAM, RESULT, SITE, PREF = "device", "program", "result", "site", "pref"
# Rows only shown (nothing done): the same item, different on each side
CONFLICT = "conflict"


class SyncError(Exception):
    pass


@dataclass
class Program:
    key: str               # uuid, else file name without date prefix
    state: str
    path: Path
    mtime: float
    data: dict
    name: str              # its description, for display

    @property
    def id_command(self) -> dict:
        return (self.data.get("command") or self.data).get("id_command") or {}


@dataclass
class Device:
    dwarf: LiteDwarf
    key: str               # identifier (6 hex digits), else "name:<name>"
    sessions_dir: Path
    programs: dict[str, Program] = field(default_factory=dict)
    results: dict[str, Path] = field(default_factory=dict)


@dataclass
class Snapshot:
    folder: Path
    devices: dict[str, Device]
    sites: dict[str, dict]
    prefs: dict[str, dict]


@dataclass
class Action:
    kind: str
    direction: str         # A2B / B2A ("" for a CONFLICT row)
    device: str            # Dwarf's display name ("" for sites)
    label: str             # what it is (program, site, Dwarf name...)
    detail: str            # why: a text key of hub/i18n.py ("sy_d_...")
    warning: str = ""      # shown next to it (a ToDo copied: double capture)
    selected: bool = True
    # for apply(): files to copy (src, dst), files to remove, JSON merges
    copies: list[tuple[Path, Path]] = field(default_factory=list)
    removes: list[Path] = field(default_factory=list)
    device_entry: dict | None = None     # a devices.json entry to add (DEVICE)
    json_merge: tuple[str, str, dict] | None = None   # (file, key, value) (SITE / PREF)
    detail_args: dict = field(default_factory=dict)   # the detail text's values


# ── reading ──────────────────────────────────────────────────────────────
def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except (OSError, ValueError) as e:
        raise SyncError(f"{path}: {e}")


def config_name(config_py: str) -> str:
    stem = Path(config_py).stem
    if stem == "config":
        return "Default"
    return stem[len("config_"):] if stem.startswith("config_") else stem


def sessions_dir(folder: Path, config_py: str) -> Path:
    name = config_name(config_py)
    if name == "Default":
        return folder / "Astro_Sessions"
    return folder / "Devices_Sessions" / name / "Astro_Sessions"


def program_key(data: dict, filename: str) -> str:
    uuid = ((data.get("command") or data).get("id_command") or {}).get("uuid")
    return f"uuid:{uuid}" if uuid else "file:" + _DATE_PREFIX.sub("", filename)


def _read_programs(base: Path) -> dict[str, Program]:
    programs: dict[str, Program] = {}
    for state in STATES:
        folder = base / state
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue        # unreadable: left alone
            key = program_key(data, path.name)
            prog = Program(key, state, path, path.stat().st_mtime, data,
                           ((data.get("command") or data).get("id_command") or {}).get("description") or path.stem)
            # The same program twice on one side (shouldn't happen): its most advanced copy
            old = programs.get(key)
            if old is None or (_RANK[state], prog.mtime) > (_RANK[old.state], old.mtime):
                programs[key] = prog
    return programs


def device_key(dwarf: LiteDwarf) -> str:
    ble = normalize_ble_id(dwarf.uid)
    return ble if ble else "name:" + re.sub(r"[\s_-]+", " ", dwarf.name).strip().casefold()


def read(folder: Path) -> Snapshot:
    folder = Path(folder)
    if not (folder / "devices.json").is_file():
        raise SyncError(f"{folder}: no devices.json - not a Dwarfium Lite folder")
    devices: dict[str, Device] = {}
    for dwarf in read_lite(folder):
        base = sessions_dir(folder, dwarf.config_py)
        dev = Device(dwarf, device_key(dwarf), base, _read_programs(base))
        results = base / "Results"
        if results.is_dir():
            dev.results = {p.name: p for p in results.iterdir() if p.is_file()}
        devices.setdefault(dev.key, dev)
    sites = {str(s.get("name")): s for s in _read_json(folder / "sites.json", []) if isinstance(s, dict) and s.get("name")}
    prefs = _read_json(folder / "device_prefs.json", {})
    return Snapshot(folder, devices, sites, prefs if isinstance(prefs, dict) else {})


# ── comparing ────────────────────────────────────────────────────────────
def _target_program_path(dev: Device, prog: Program) -> Path:
    return dev.sessions_dir / prog.state / prog.path.name


def _free_config_names(dwarf: LiteDwarf, target: Path, taken: set[str]) -> tuple[str, str]:
    """The config file names for a Dwarf added to `target`: its own when
    free there, else with _2, _3..."""
    py, ini = Path(dwarf.config_py), Path(dwarf.config_ini or Path(dwarf.config_py).with_suffix(".ini"))
    n = 1
    while True:
        suffix = "" if n == 1 else f"_{n}"
        cand_py = py.with_name(py.stem + suffix + py.suffix).as_posix()
        cand_ini = ini.with_name(ini.stem + suffix + ini.suffix).as_posix()
        if (cand_py not in taken and not (target / cand_py).exists()
                and not (target / cand_ini).exists()
                and not sessions_dir(target, cand_py).exists()):
            return cand_py, cand_ini
        n += 1


def _device_actions(src: Snapshot, dst: Snapshot, direction: str, taken: set[str]) -> list[Action]:
    actions = []
    for key, dev in src.devices.items():
        if key in dst.devices:
            continue
        new_py, new_ini = _free_config_names(dev.dwarf, dst.folder, taken)
        taken.add(new_py)
        copies = [(src.folder / dev.dwarf.config_py, dst.folder / new_py)]
        if dev.dwarf.config_ini and (src.folder / dev.dwarf.config_ini).is_file():
            copies.append((src.folder / dev.dwarf.config_ini, dst.folder / new_ini))
        new_base = sessions_dir(dst.folder, new_py)
        if dev.sessions_dir.is_dir():
            for path in dev.sessions_dir.rglob("*"):
                if path.is_file():
                    copies.append((path, new_base / path.relative_to(dev.sessions_dir)))
        n_prog = len(dev.programs)
        has_todo = any(p.state == "ToDo" for p in dev.programs.values())
        actions.append(Action(
            DEVICE, direction, dev.dwarf.name, dev.dwarf.name,
            "sy_d_new_dwarf", detail_args={"file": new_py, "n": n_prog},
            warning="todo" if has_todo else "",
            copies=copies,
            device_entry={"name": dev.dwarf.name, "config_py": new_py,
                          "config_ini": new_ini if dev.dwarf.config_ini else ""},
        ))
    return actions


def _program_actions(a: Device, b: Device) -> list[Action]:
    actions = []
    for key in sorted(set(a.programs) | set(b.programs)):
        pa, pb = a.programs.get(key), b.programs.get(key)
        if pa and not pb:
            actions.append(_copy_program(pa, a, b, A2B, None))
        elif pb and not pa:
            actions.append(_copy_program(pb, b, a, B2A, None))
        else:
            if pa.state == pb.state and pa.data == pb.data:
                continue                                    # identical
            if pa.state == "Current" and pb.state == "Current":
                actions.append(Action(CONFLICT, "", a.dwarf.name, pa.name, "sy_d_running_both", selected=False))
                continue
            ra, rb = _RANK[pa.state], _RANK[pb.state]
            if ra != rb:
                winner_a = ra > rb
            else:                                           # same stage: the latest written
                winner_a = pa.mtime >= pb.mtime
            if winner_a:
                actions.append(_copy_program(pa, a, b, A2B, pb))
            else:
                actions.append(_copy_program(pb, b, a, B2A, pa))
    return actions


def _copy_program(prog: Program, src_dev: Device, dst_dev: Device, direction: str,
                  replaced: Program | None) -> Action:
    if replaced is None:
        detail, args = "sy_d_missing_state", {"state": prog.state}
    elif replaced.state != prog.state:
        detail, args = "sy_d_state_change", {"old": replaced.state, "new": prog.state}
    else:
        detail, args = "sy_d_newer", {"state": prog.state}
    return Action(
        PROGRAM, direction, src_dev.dwarf.name, prog.name, detail, detail_args=args,
        # A program to run copied: both installations could capture it
        warning="todo" if prog.state == "ToDo" and replaced is None else "",
        copies=[(prog.path, _target_program_path(dst_dev, prog))],
        removes=[replaced.path] if replaced is not None and replaced.path != _target_program_path(dst_dev, prog) else [],
    )


def _result_actions(a: Device, b: Device) -> list[Action]:
    actions = []
    for name in sorted(set(a.results) - set(b.results)):
        actions.append(Action(RESULT, A2B, a.dwarf.name, name, "sy_d_result",
                              copies=[(a.results[name], b.sessions_dir / "Results" / name)]))
    for name in sorted(set(b.results) - set(a.results)):
        actions.append(Action(RESULT, B2A, b.dwarf.name, name, "sy_d_result",
                              copies=[(b.results[name], a.sessions_dir / "Results" / name)]))
    return actions


def _dict_actions(kind: str, file: str, a: dict, b: dict, label) -> list[Action]:
    actions = []
    for key in sorted(set(a) | set(b)):
        va, vb = a.get(key), b.get(key)
        if va is not None and vb is None:
            actions.append(Action(kind, A2B, "", label(key), "sy_d_missing", json_merge=(file, key, va)))
        elif vb is not None and va is None:
            actions.append(Action(kind, B2A, "", label(key), "sy_d_missing", json_merge=(file, key, vb)))
        elif va != vb:
            actions.append(Action(CONFLICT, "", "", label(key), "sy_d_differs", selected=False,
                                  detail_args={"file": file}))
    return actions


def compare(a: Snapshot, b: Snapshot) -> list[Action]:
    """Every action that would make both installations hold the same
    things, A2B / B2A, plus CONFLICT rows (shown, never applied)."""
    if a.folder.resolve() == b.folder.resolve():
        raise SyncError("the same folder twice")
    actions = []
    taken_a = {d.dwarf.config_py for d in a.devices.values()}
    taken_b = {d.dwarf.config_py for d in b.devices.values()}
    actions += _device_actions(a, b, A2B, taken_b)
    actions += _device_actions(b, a, B2A, taken_a)
    for key in sorted(set(a.devices) & set(b.devices)):
        actions += _program_actions(a.devices[key], b.devices[key])
        actions += _result_actions(a.devices[key], b.devices[key])
    actions += _dict_actions(SITE, "sites.json", a.sites, b.sites, lambda k: k)
    names = {d.dwarf.uid: d.dwarf.name for s in (a, b) for d in s.devices.values()}
    actions += _dict_actions(PREF, "device_prefs.json", a.prefs, b.prefs, lambda k: names.get(k, k))
    return actions


# ── writing ──────────────────────────────────────────────────────────────
_BACKED_UP = ("devices.json", "sites.json", "device_prefs.json")


def backup(folder: Path) -> Path:
    """A zip of the files a sync may change: devices.json, sites.json,
    device_prefs.json, the config_*.py / .ini and every Astro_Sessions
    folder. In <folder>/sync_backups/."""
    folder = Path(folder)
    dest = folder / BACKUP_DIR / time.strftime("lite-sync-%Y%m%d-%H%M%S.zip")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for name in _BACKED_UP:
            if (folder / name).is_file():
                z.write(folder / name, name)
        for path in list(folder.glob("config*.py")) + list(folder.glob("config*.ini")):
            z.write(path, path.name)
        for root in (folder / "Astro_Sessions", folder / "Devices_Sessions"):
            if root.is_dir():
                for path in root.rglob("*"):
                    if path.is_file():
                        z.write(path, path.relative_to(folder).as_posix())
    return dest


def _atomic_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".hub_tmp")
    shutil.copy2(src, tmp)
    os.replace(tmp, dst)


def _write_json(path: Path, data) -> None:
    tmp = path.with_name(path.name + ".hub_tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def apply(a: Path, b: Path, actions: list[Action]) -> dict:
    """Writes the selected actions (not CONFLICT rows), after a backup of
    both folders. {"backups": [a_zip, b_zip], "done": n}."""
    chosen = [x for x in actions if x.selected and x.kind != CONFLICT]
    backups = [str(backup(a)), str(backup(b))] if chosen else []
    folders = {A2B: Path(b), B2A: Path(a)}
    for act in chosen:
        for src, dst in act.copies:
            _atomic_copy(src, dst)
        for path in act.removes:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        target = folders[act.direction]
        if act.device_entry is not None:
            entries = _read_json(target / "devices.json", [])
            entries.append(act.device_entry)
            _write_json(target / "devices.json", entries)
        if act.json_merge is not None:
            file, key, value = act.json_merge
            if file == "sites.json":
                sites = _read_json(target / file, [])
                if not any(isinstance(s, dict) and s.get("name") == key for s in sites):
                    sites.append(value)
                    _write_json(target / file, sites)
            else:
                prefs = _read_json(target / file, {})
                prefs.setdefault(key, value)
                _write_json(target / file, prefs)
    return {"backups": backups, "done": len(chosen)}
