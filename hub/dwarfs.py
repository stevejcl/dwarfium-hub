"""The Dwarfs of both applications, side by side, and the links between
them.

Dwarfium Lite (Astro Dwarf Session) knows its Dwarfs from devices.json
(display name -> config_<slug>.py / .ini pair): the IP is DWARF_IP in the
.py (else dwarf_ip in the .ini), the model DWARF_ID, and the link to Scope
Archive is [CONFIG] dwarfium_id (= Scope Archive's Dwarf.id) and
dwarfium_base_url in the .ini.

Scope Archive keeps its Dwarfs in the Dwarf table of db/dwarf_backup.db
(type = the same model numbers as DWARF_ID, ip_sta_mode = the IP; from
its V3.4.3, ble_id = the Dwarf's identifier).

Which physical Dwarf: the last 6 hex digits of its MAC address, printed
on it, also end its Bluetooth name - Dwarfium Lite's DWARF_UID (e.g.
DWARF3_A1B2C3) - and are Scope Archive's ble_id. When both sides have it,
two Dwarfs are the same device for sure (or for sure not).

Both are read from the files, whether the apps run or not. Writing:
Dwarfium Lite reads its files when it starts (and may write its .ini
back), so they are only changed while it is stopped - line by line,
everything else in them kept as it is. Scope Archive's database is
written through SQLite (safe while it runs); the first write of a hub
session copies it to db/dwarf_backup.db.hub before.

A Dwarf of Scope Archive can't be created in Dwarfium Lite from here: it
needs the Dwarf's UID and a Site (Wi-Fi, location), which Dwarfium Lite's
own pairing / manual configuration supply - the hub opens that page with
the name, model and IP filled in.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

MODELS = {"1": "Dwarf II", "2": "Dwarf 3", "4": "Dwarf Mini"}
SA_DB = Path("db") / "dwarf_backup.db"
SA_DB_BACKUP = SA_DB.with_name("dwarf_backup.db.hub")


class DwarfsError(Exception):
    pass


@dataclass
class LiteDwarf:
    """A Dwarf of Dwarfium Lite."""
    name: str
    config_py: str               # relative to Dwarfium Lite's folder, as in devices.json
    config_ini: str
    model: str = ""              # "1" / "2" / "4"
    ip: str = ""
    uid: str = ""                # the Bluetooth name
    dwarfium_id: str = ""        # Scope Archive's Dwarf.id it is linked to
    dwarfium_base_url: str = ""


@dataclass
class ArchiveDwarf:
    """A Dwarf of Scope Archive."""
    id: int
    name: str
    model: str = ""
    ip: str = ""
    description: str = ""
    ble_id: str = ""             # 6 hex digits, "" unknown


def normalize_ble_id(text: str | None) -> str:
    """The 6 hex digits (upper case), "" when the text doesn't give them -
    the same rule as Scope Archive's api/dwarf_identity.py: after the last
    "_" of a Bluetooth name (DWARF3_3C2E2A, DWARF_mini_19A608) exactly 6
    hex digits, else the 6 digits themselves or a whole MAC address."""
    text = (text or "").strip()
    if "_" in text:
        tail = text.rsplit("_", 1)[1]
        return tail.upper() if re.fullmatch(r"[0-9A-Fa-f]{6}", tail) else ""
    compact = re.sub(r"[\s:.\-]", "", text)
    if re.fullmatch(r"[0-9A-Fa-f]{6}", compact):
        return compact.upper()
    if re.fullmatch(r"[0-9A-Fa-f]{12}", compact):
        return compact[-6:].upper()
    return ""


def ble_id_from_bluetooth_name(text: str | None) -> str:
    """The identifier when the whole text is a Dwarf Bluetooth name - a
    Scope Archive before V3.4.3, where it was noted as the description."""
    text = (text or "").strip()
    return normalize_ble_id(text) if re.fullmatch(r"DWARF\w*_[0-9A-Fa-f]{6}", text, flags=re.IGNORECASE) else ""


LINKED, MISMATCH, BROKEN, SUGGESTED, LITE_ONLY, ARCHIVE_ONLY = (
    "linked", "mismatch", "broken", "suggested", "lite_only", "archive_only")


@dataclass
class Row:
    status: str
    lite: LiteDwarf | None = None
    archive: ArchiveDwarf | None = None
    # what differs between the two sides of a pair: "name", "ip", "model",
    # "ble_id" (Scope Archive doesn't have Dwarfium Lite's identifier)
    differences: list[str] = field(default_factory=list)
    # both sides have the Dwarf's identifier, and it is the same
    verified: bool = False


# ── Dwarfium Lite ────────────────────────────────────────────────────────
_PY_VALUE = r'^{key}\s*=\s*"(.*)"\s*$'


def _py_value(text: str, key: str) -> str:
    m = re.search(_PY_VALUE.format(key=key), text, flags=re.MULTILINE)
    return m.group(1).strip() if m else ""


def _ini_values(text: str) -> dict[str, str]:
    """[CONFIG]'s keys (lower case) -> values, without configparser: no
    interpolation surprise with a '%' in a Wi-Fi password."""
    values, in_config = {}, False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            in_config = stripped.lower() == "[config]"
        elif in_config and "=" in stripped and not stripped.startswith(("#", ";")):
            key, value = stripped.split("=", 1)
            values[key.strip().lower()] = value.strip()
    return values


def read_lite(folder: Path) -> list[LiteDwarf]:
    try:
        entries = json.loads((folder / "devices.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, ValueError) as e:
        raise DwarfsError(f"devices.json: {e}")
    dwarfs = []
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict) or not entry.get("config_py"):
            continue
        d = LiteDwarf(name=str(entry.get("name") or ""), config_py=entry["config_py"],
                      config_ini=entry.get("config_ini") or "")
        try:
            py = (folder / d.config_py).read_text(encoding="utf-8")
            d.model, d.ip, d.uid = _py_value(py, "DWARF_ID"), _py_value(py, "DWARF_IP"), _py_value(py, "DWARF_UID")
        except OSError:
            pass
        try:
            ini = _ini_values((folder / d.config_ini).read_text(encoding="utf-8")) if d.config_ini else {}
        except OSError:
            ini = {}
        d.ip = d.ip or ini.get("dwarf_ip", "")
        d.dwarfium_id = ini.get("dwarfium_id", "")
        d.dwarfium_base_url = ini.get("dwarfium_base_url", "")
        dwarfs.append(d)
    return dwarfs


def _write_text(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".hub_tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _set_ini_values(path: Path, values: dict[str, str]) -> None:
    """Sets [CONFIG] keys, every other line kept as it is."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        lines = []
    todo = dict(values)
    out, in_config, config_end = [], False, None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("["):
            if in_config:
                config_end = len(out)
            in_config = stripped.lower() == "[config]"
        elif in_config and "=" in stripped and not stripped.startswith(("#", ";")):
            key = stripped.split("=", 1)[0].strip().lower()
            if key in todo:
                out.append(f"{key} = {todo.pop(key)}")
                continue
        out.append(line)
    if todo:
        added = [f"{k} = {v}" for k, v in todo.items()]
        if not any(l.strip().lower() == "[config]" for l in out):
            out = ["[CONFIG]"] + added + out
        else:
            end = len(out) if config_end is None else config_end    # None: [CONFIG] is the last section
            while end > 0 and not out[end - 1].strip():              # before the section's blank lines
                end -= 1
            out[end:end] = added
    _write_text(path, "\n".join(out) + "\n")


def _set_py_value(path: Path, key: str, value: str) -> None:
    text = path.read_text(encoding="utf-8")
    new, count = re.subn(_PY_VALUE.format(key=key), f'{key} = "{value}"', text, count=1, flags=re.MULTILINE)
    if not count:
        raise DwarfsError(f"no {key} line in {path.name}")
    _write_text(path, new)


def link(folder: Path, dwarf: LiteDwarf, archive_id: int | None, archive_url: str) -> None:
    """Links a Dwarf of Dwarfium Lite to one of Scope Archive (None:
    unlinks it). Dwarfium Lite must be stopped."""
    if not dwarf.config_ini:
        raise DwarfsError(f"{dwarf.name}: no config .ini in devices.json")
    values = {"dwarfium_id": str(archive_id) if archive_id else ""}
    if archive_id:
        values["dwarfium_base_url"] = archive_url
    _set_ini_values(folder / dwarf.config_ini, values)


def set_lite_name(folder: Path, dwarf: LiteDwarf, name: str) -> None:
    """Display name in devices.json (the config file names stay)."""
    path = folder / "devices.json"
    entries = json.loads(path.read_text(encoding="utf-8"))
    for entry in entries:
        if entry.get("config_py") == dwarf.config_py:
            entry["name"] = name
    _write_text(path, json.dumps(entries, indent=2, ensure_ascii=False))


def set_lite_ip(folder: Path, dwarf: LiteDwarf, ip: str) -> None:
    _set_py_value(folder / dwarf.config_py, "DWARF_IP", ip)


# ── Scope Archive ────────────────────────────────────────────────────────
def archive_db(folder: Path) -> Path:
    return folder / SA_DB


def read_archive(folder: Path) -> list[ArchiveDwarf] | None:
    """None: no database yet (Scope Archive never started)."""
    db = archive_db(folder)
    if not db.is_file():
        return None
    try:
        conn = sqlite3.connect(f"{db.resolve().as_uri()}?mode=ro", uri=True, timeout=5)
        try:
            columns = {r[1] for r in conn.execute("PRAGMA table_info(Dwarf)")}
            ble_id = "ble_id" if "ble_id" in columns else "''"       # before V3.4.3
            rows = conn.execute(f"SELECT id, name, type, ip_sta_mode, description, {ble_id} FROM Dwarf ORDER BY name") \
                .fetchall()
        finally:
            conn.close()
    except sqlite3.Error as e:
        raise DwarfsError(f"Scope Archive database: {e}")
    return [ArchiveDwarf(id=r[0], name=r[1] or "", model=str(r[2] or ""), ip=r[3] or "", description=r[4] or "",
                         ble_id=normalize_ble_id(r[5]) or ble_id_from_bluetooth_name(r[4])) for r in rows]


def archive_has_ble_id(folder: Path) -> bool:
    """Scope Archive's database keeps the Dwarf's identifier (V3.4.3+)."""
    try:
        conn = sqlite3.connect(f"{archive_db(folder).resolve().as_uri()}?mode=ro", uri=True, timeout=5)
        try:
            return any(r[1] == "ble_id" for r in conn.execute("PRAGMA table_info(Dwarf)"))
        finally:
            conn.close()
    except sqlite3.Error:
        return False


_backed_up: set[Path] = set()


def _archive_write(folder: Path, sql: str, params: tuple) -> int:
    db = archive_db(folder)
    if not db.is_file():
        raise DwarfsError("Scope Archive has no database yet: start it once")
    conn = sqlite3.connect(str(db), timeout=10)
    try:
        if db not in _backed_up:       # the state before the hub's first change
            backup = sqlite3.connect(str(folder / SA_DB_BACKUP))
            try:
                conn.backup(backup)
            finally:
                backup.close()
            _backed_up.add(db)
        with conn:
            cursor = conn.execute(sql, params)
        return cursor.lastrowid
    except sqlite3.Error as e:
        raise DwarfsError(f"Scope Archive database: {e}")
    finally:
        conn.close()


def create_archive(folder: Path, dwarf: LiteDwarf) -> int:
    """The Dwarf of Dwarfium Lite in Scope Archive (with its identifier
    when Scope Archive keeps it); returns its id. Its USB / backup
    folders are set in Scope Archive afterwards."""
    model = int(dwarf.model) if dwarf.model.isdigit() else None
    if archive_has_ble_id(folder):
        return _archive_write(
            folder,
            "INSERT INTO Dwarf (name, description, usb_astronomy_dir, type, ip_sta_mode, ble_id) VALUES (?, ?, ?, ?, ?, ?)",
            (dwarf.name, "", "", model, dwarf.ip, normalize_ble_id(dwarf.uid) or None))
    return _archive_write(
        folder,
        "INSERT INTO Dwarf (name, description, usb_astronomy_dir, type, ip_sta_mode) VALUES (?, ?, ?, ?, ?)",
        (dwarf.name, "", "", model, dwarf.ip))


def set_archive_name(folder: Path, archive_id: int, name: str) -> None:
    _archive_write(folder, "UPDATE Dwarf SET name = ? WHERE id = ?", (name, archive_id))


def set_archive_ip(folder: Path, archive_id: int, ip: str) -> None:
    _archive_write(folder, "UPDATE Dwarf SET ip_sta_mode = ? WHERE id = ?", (ip, archive_id))


def set_archive_ble_id(folder: Path, archive_id: int, ble_id: str) -> None:
    if not archive_has_ble_id(folder):
        raise DwarfsError("this Scope Archive doesn't keep the Dwarf's identifier yet (V3.4.3+)")
    _archive_write(folder, "UPDATE Dwarf SET ble_id = ? WHERE id = ?", (ble_id, archive_id))


# ── both ─────────────────────────────────────────────────────────────────
def _norm(name: str) -> str:
    return re.sub(r"[\s_-]+", " ", name).strip().casefold()


def _ids(lite: LiteDwarf, archive: ArchiveDwarf) -> tuple[str, str]:
    return normalize_ble_id(lite.uid), archive.ble_id


def _differences(lite: LiteDwarf, archive: ArchiveDwarf) -> list[str]:
    out = []
    if _norm(lite.name) != _norm(archive.name):
        out.append("name")
    if (lite.ip or archive.ip) and lite.ip != archive.ip:     # also a side without IP
        out.append("ip")
    if lite.model and archive.model and lite.model != archive.model:
        out.append("model")
    lite_id, archive_id = _ids(lite, archive)
    if lite_id and not archive_id:
        out.append("ble_id")
    return out


def _pair(status: str, lite: LiteDwarf, archive: ArchiveDwarf) -> Row:
    lite_id, archive_id = _ids(lite, archive)
    if status == LINKED and lite_id and archive_id and lite_id != archive_id:
        status = MISMATCH          # linked, but two different Dwarfs
    return Row(status, lite, archive, _differences(lite, archive), verified=bool(lite_id) and lite_id == archive_id)


def match(lite: list[LiteDwarf], archive: list[ArchiveDwarf] | None) -> list[Row]:
    """Linked pairs first, then suggested pairs - same identifier, else
    same IP, else same name; never two different identifiers nor two
    different models - then the Dwarfs on one side only."""
    archive = archive or []
    by_id = {a.id: a for a in archive}
    rows, used = [], set()
    free_lite = []
    for d in lite:
        target = by_id.get(int(d.dwarfium_id)) if d.dwarfium_id.isdigit() else None
        if target is not None:
            rows.append(_pair(LINKED, d, target))
            used.add(target.id)
        elif d.dwarfium_id:
            rows.append(Row(BROKEN, d))        # linked to a Dwarf Scope Archive no longer has
        else:
            free_lite.append(d)

    def compatible(d: LiteDwarf, a: ArchiveDwarf) -> bool:
        lite_id, archive_id = _ids(d, a)
        return not (d.model and a.model and d.model != a.model) and not (lite_id and archive_id and lite_id != archive_id)

    # One pass per clue, the surest first, over all the Dwarfs: a Dwarf
    # found by its identifier is never taken by another one's same IP
    clues = (lambda d, a: bool(_ids(d, a)[0]) and _ids(d, a)[0] == _ids(d, a)[1],
             lambda d, a: bool(d.ip) and a.ip == d.ip,
             lambda d, a: bool(_norm(a.name)) and _norm(a.name) == _norm(d.name))
    suggested: dict[int, Row] = {}
    for clue in clues:
        for i, d in enumerate(free_lite):
            if i in suggested:
                continue
            found = next((a for a in archive if a.id not in used and compatible(d, a) and clue(d, a)), None)
            if found:
                suggested[i] = _pair(SUGGESTED, d, found)
                used.add(found.id)
    rows += [suggested[i] for i in sorted(suggested)]
    rows += [Row(LITE_ONLY, d) for i, d in enumerate(free_lite) if i not in suggested]
    rows += [Row(ARCHIVE_ONLY, archive=a) for a in archive if a.id not in used]
    return rows


def archive_url(port: int) -> str:
    return f"http://localhost:{port}"

