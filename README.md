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

**Identify** — several Dwarfs on the table: the ✳ button of a row flashes that Dwarf's ring light (through Dwarfium Lite, never during a capture). Dwarfium Lite's pages (manual configuration, pairing) open in its own window.

Dwarfium Lite reads its Dwarfs when it starts: its side is only changed while it is stopped, and only the lines concerned (`dwarfium_id`, `dwarfium_base_url` in `config_*.ini`, `DWARF_IP`, the name in `devices.json`). Scope Archive's database is copied to `db/dwarf_backup.db.hub` before the hub's first change.

## Installations

The **Installations** tab is a map of the Dwarfium Lite installations you use. The hub runs on the home PC (or a home server): it installs and starts Dwarfium Lite there, and Scope Archive if you want it. Every other Dwarfium Lite - a source run for testing, a laptop, a mini PC next to the Dwarfs - is an **instance**: the hub doesn't start it, it shows it and synchronizes with it.

- **A card per installation**, on the *home network* or *away (Tailscale)*: Dwarfium Lite running (its version), stopped (the computer answers, not Dwarfium Lite) or unreachable; its Dwarfs (connected, capturing, a program waiting to be sent); how it stands against this PC (the startup check of the Synchronize tab) with a **Compare** button; **Open** it in the browser.
- **The same Dwarf connected to two installations** is shown in red: a Dwarf is driven by one Dwarfium Lite at a time.
- **+ Add an instance** / ✎: name, type (release - the official version, downloaded / dev - run from the source / laptop / mini PC / other), access (home network / Tailscale), address (IP, computer name, Tailscale MagicDNS name or `100.x` IP, `localhost` for a source run on this PC), port (8090), shared folder (`\\laptop\AstroDwarfSession`, for the synchronization). **Check** asks the instance (`/api/app-info`, `/api/dwarfs` - Dwarfium Lite listens on the network) and opens the folder. Only an address or a folder is needed.
- **Both** (a laptop or mini PC sometimes at home, sometimes away): a home network address and a Tailscale address. The home one is asked first, then the Tailscale one; the card goes to the band where it answered. From such an instance, Scope Archive is best given with this PC's Tailscale name (`http://pc-name:8080`, started with LAN access): it answers at home and away.
- **FTP** — each connected Dwarf gets an FTP badge: does this PC reach the Dwarf's FTP (what Scope Archive downloads from)? For a Dwarf on a remote site's network, that takes a Tailscale **subnet router** on the remote computer (`tailscale set --advertise-routes=192.168.88.0/24`, approved in the admin console; the site's network must differ from the home one) - the badge's tooltip gives the network, the Help the steps. Asked every 5 minutes, and again with ⟳ or Check.
- The states are asked again every 20 s while the tab is shown. The folders of the Synchronize tab are the instances' shared folders (the ones added before this became instances).

A **Help** button explains the setup step by step, Tailscale included (install on both machines, MagicDNS name, sharing and the Windows firewall for the Tailscale network).

## Synchronize

The **Synchronize** tab merges two Dwarfium Lite installations both ways: the hub's own, a source run, a laptop taken to the field, a mini PC (add its folder through a Windows share, `\\minipc\folder` - or give it to the instance in the Installations tab).

- **Dwarfs** — a Dwarf one side lacks is copied there (its `config_*.py` / `.ini`, its programs). The same Dwarf is recognized by its ID, even under another config name (`config_d3` here, `config_dwarf3` there); its name and IP are left as they are on each side.
- **Programs** — found by their uuid. One missing on a side is copied; at two stages, the most advanced wins (Done / Error over Current over ToDo), the latest written at the same stage. A program to run copied to the other side is flagged: run it from one installation only.
- **Results, sites, preferences** — what one side lacks is copied; a site or preference different on each side is only shown.

**At startup** the hub compares its Dwarfium Lite with each added folder in the background: a notice when one differs, and a line per folder in the tab (the same, *n* changes with a **Compare** button, or not reachable — a share that doesn't answer is given up after 20 s).

**A remote installation** (the Dwarf travels with a mini PC or a laptop) — through [Tailscale](https://tailscale.com), Windows file sharing works as on the local network: share the Dwarfium Lite folder on the remote PC and add `\\<tailscale-name>\<share>` (MagicDNS) or `\\100.x.y.z\<share>` here. On the remote PC, Windows Firewall must allow File and Printer Sharing (SMB, port 445) from the Tailscale network, which Windows often classes as a Public network.

**Compare** lists every change, each one can be unticked, nothing is written before **Synchronize**. Dwarfium Lite must be stopped on both sides: **Synchronize** stops the hub's own (and starts it again after) — one started outside the hub must be closed first; for another folder you confirm it is stopped. A zip of both installations is made first, in their `sync_backups` folder.

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
