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
- **Start / stop** — each application starts from its own folder on a **fixed port** (Scope Archive 8080, Dwarfium Lite 8090, editable), alone or both together; closing the hub leaves them running. The hub asks the port which application answers (`/api/app-info`): another program on that port is shown as such, and the application isn't started over it.
- **LAN access** — Scope Archive can be started reachable from the other devices of the network (`--lan`); Dwarfium Lite always is.
- English / French.

Coming next: one view of the Dwarfs of both applications — link them, create a Dwarf of one application in the other, keep their names and IPs in sync.

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
