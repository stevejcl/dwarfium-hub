# Dwarfium-Hub

One place to **install, update and start** the applications of the Dwarfium family:

| Application | What it does |
|---|---|
| [Dwarfium Scope Archive](https://github.com/stevejcl/dwarfium-scope-archive) | Archive, explore and plan your Dwarf sessions |
| [Dwarfium Lite — Astro Dwarf Session](https://github.com/stevejcl/astro_dwarf_session) | Control your Dwarfs, programs and native schedules |

## What it does

- **Latest versions** — reads each application's latest GitHub release and compares it with the installed one; **What's new** shows the release notes.
- **Install / update** — downloads this system's build (with progress), checks its SHA-256, and lays it over the installation **file by file**: only program files are replaced, **your data is never touched** (devices, configs, sessions, database, settings, `.nicegui` storage…).
- **Rollback** — the files an update replaced are kept, *Back to <version>* restores them.
- **Existing installations** — *Use an existing installation* adopts a folder installed by hand instead of reinstalling it (its data stays where it is); its version is read from the application the first time it runs.
- **Start / stop** — each application starts from its own folder on a **fixed port** (Scope Archive 8080, Dwarfium Lite 8090, editable), alone or both together (started side by side, a few seconds apart; two applications can't be given the same port); closing the hub leaves them running. The hub asks the port which application answers (`/api/app-info`): another program on that port is shown as such, and the application isn't started over it.
- **LAN access** — Scope Archive can be started reachable from the other devices of the network (`--lan`); Dwarfium Lite always is.
- English / French.

## Dwarfs

The **Dwarfs** tab shows the Dwarfs of both applications side by side. Linked, a Dwarf opens from one application to the other (Scope Archive's sessions, tonight's plan in Dwarfium Lite…).

| On screen | What the hub offers |
|---|---|
| **Linked** / **Linked (verified)** | copy the name, the IP or the ID from one side to the other when they differ; unlink |
| **Same Dwarf (verified)** (same ID) / **Same Dwarf?** (same IP, else same name, same model) | link — or link all the suggestions at once |
| **Not the same Dwarf!** | linked, but the two IDs differ: unlink |
| **Not in Scope Archive** | create it there, already linked (or all of them); or link it to a Dwarf picked in the list |
| **Not in Dwarfium Lite** | open Dwarfium Lite's manual configuration filled in (name, model, IP) — with the Dwarf on the network its UID and model are read from it (3.2.4+), only the Site is left to choose — saved linked |
| **Broken link** | the Scope Archive Dwarf no longer exists: create it again, link to another one, or unlink |
| *nothing at all* | add the first Dwarf in Dwarfium Lite (Bluetooth pairing or manual configuration), then create it in Scope Archive here |

**ID** — which physical Dwarf: the last 6 characters of the MAC address printed on it. They also end its Bluetooth name (Dwarfium Lite's UID, e.g. `DWARF3_A1B2C3`), and Scope Archive (V3.4.3+) keeps them on its Dwarf page — typed from the label, or read from the Dwarf at its IP. Same ID on both sides: the same Dwarf for sure; two different IDs are never suggested together.

Dwarfium Lite reads its Dwarfs when it starts: its side is only changed while it is stopped, and only the lines concerned (`dwarfium_id`, `dwarfium_base_url` in `config_*.ini`, `DWARF_IP`, the name in `devices.json`). Scope Archive's database is copied to `db/dwarf_backup.db.hub` before the hub's first change.

## Install

Download `DwarfiumHub-<Windows|Linux|macOS>.zip` from the [releases](https://github.com/stevejcl/dwarfium-hub/releases), unzip it anywhere and run `DwarfiumHub`. The applications are installed in `C:\Dwarfium` on Windows, `~/Dwarfium` elsewhere — **Change** at the top of the hub picks another folder.

## Run from source

```bash
pip install -r requirements.txt
python dwarfium_hub.py              # in its own window
python dwarfium_hub.py --no_native  # in a browser
```

Settings are kept in `hub_config.json` next to the hub; each installation records the version the hub installed in its `.hub_version.json` (and the previous version's files in `.hub_backup/`).

## Build

`python buildDwarfiumHub.py` (nicegui-pack, one-file windowed) → `DwarfiumHub-<OS>.zip`. GitHub Actions builds Windows, Linux and macOS on every push to `main`; running the workflow by hand publishes a release `v<version>` from `CHANGELOG.md`.

## Adding an application

One more `AppSpec` in [`hub/apps.py`](hub/apps.py) (repository, release asset prefix, executable, default port). An application that updates itself is declared with `hub_updates=False`: the hub installs it the first time and starts it.
