# Changelog

## [0.1.2] - 2026-10-16
  ### Add
    ### Synchronize tab
    Two Dwarfium Lite installations merged both ways - the hub's, a source run, a laptop's, a mini PC's through a
    Windows share (folders added here, kept in hub_config.json). Dwarfs a side lacks (config files and programs),
    found by their ID whatever their config name; programs by their uuid: missing ones copied, at two stages the most
    advanced kept (Done / Error > Current > ToDo; the latest at the same stage); results, sites and preferences a side
    lacks; a site or preference different on each side only shown. A preview lists every change (each can be
    unticked), a program to run copied to the other side is flagged (double capture). Dwarfium Lite stopped on both
    sides: the hub's is stopped by Synchronize and started again after (nothing synchronized when it can't be - one
    started outside the hub), another folder's confirmed; a zip of both in their sync_backups folder first.
    At startup, the hub's Dwarfium Lite compared in the background with each added folder: a notice when one
    differs, a line per folder in the tab (the same / n changes with Compare / not reachable - a network share that
    doesn't answer given up after 20 s). A remote installation works through a Windows share over Tailscale (README).
    A Help button: the home PC + laptop case step by step - once, before leaving, back home, the laptop used at home.
    ### Installations tab
    A map of the Dwarfium Lite installations: this PC (the hub's Dwarfium Lite and Scope Archive) and the instances
    added there (source run, laptop, mini PC), on the home network or away through Tailscale. Each card: Dwarfium
    Lite running with its version, stopped or unreachable (asked live, /api/app-info and /api/dwarfs, every 20 s while
    the tab is shown); its Dwarfs (connected, capturing, program waiting); its synchronization with this PC and a
    Compare button; Open in the browser. A Dwarf connected to two installations shown in red. Add / change an
    instance: name, type, access, address, port, shared folder, with a Check (Dwarfium Lite answers, its Dwarfs, the
    folder reachable). The Synchronize tab's folders are the instances' shared folders (the ones added before become
    instances). A Help button: this PC, adding an instance, Tailscale (MagicDNS, sharing and firewall).
    Access "Both" for a laptop or mini PC sometimes at home, sometimes away: its home address asked first, then its
    Tailscale one; the card goes to the band where it answered ("reached through Tailscale").

## [0.1.1] - 2026-10-13
  ### Add
    ### Dwarfs tab
    The Dwarfs of Dwarfium Lite and of Scope Archive side by side: linked, "same Dwarf?" (same IP, else same name,
    never two models), broken link, or on one side only. Link (one or all suggestions, or to a Dwarf picked in a
    list), unlink, create in Scope Archive (one or all) already linked, copy a name or an IP from one side to the
    other. A Dwarf only Scope Archive knows opens Dwarfium Lite's manual configuration filled in (its UID and Site
    are entered there), saved linked. Nothing configured yet: Bluetooth pairing or manual configuration in Dwarfium
    Lite first. Dwarfium Lite's files are only changed while it is stopped (only the lines concerned); Scope
    Archive's database is copied to db/dwarf_backup.db.hub before the hub's first change.
    ### Dwarf identifier
    Which physical Dwarf: the last 6 characters of the MAC address printed on it, which also end its Bluetooth name
    (Dwarfium Lite's UID) and are Scope Archive's identifier (V3.4.3+). Shown on both sides; matched first ("Same
    Dwarf (verified)"), never suggested between two different identifiers (nor offered in "Link to…"); a linked pair
    with two different identifiers is shown as "Not the same Dwarf!"; "ID → Scope Archive" copies it to a linked
    Dwarf that lacks it; "Create in Scope Archive" copies it too. "Add to Dwarfium Lite": with the Dwarf on the
    network, Dwarfium Lite (3.2.4) reads its UID and model from its IP - only the Site is left to choose.
    ### Identify a Dwarf
    A button on each row of the Dwarfs tab flashes the Dwarf's ring light, to see which one it is when several are on
    - through Dwarfium Lite (3.2.4+, started if needed), which refuses during a capture; each outcome is said.
    ### Dwarfium Lite's pages in its own window
    "Add to Dwarfium Lite", "Pair by Bluetooth" and "Manual configuration" open the page in Dwarfium Lite's own window,
    brought to the front (3.2.4+), instead of a browser tab one could miss; the browser stays the fallback, and the hub
    says where the page opened.
  ### Fix
    ### "Connection lost" on Start both
    Creating an application's process ran in the hub's own loop: on Windows it can take seconds for a big one-file
    executable (the antivirus scans it first), during which the hub's window lost its server - twice with Start both.
    The process is now created in a worker thread (opening a folder or the browser too), and the card says
    "Starting..." at once.
    ### Taller window
    1000 x 980 instead of 980 x 820: both applications' cards fit without a scrollbar. Exact forms only (6 hex digits after the
    Bluetooth name's last "_", the 6 digits, or a whole MAC address); with a Scope Archive before V3.4.3, a
    description that is the Dwarf's Bluetooth name gives it.

## [0.1.0] - 2026-10-13
  ### Add
    ### First version
    Installs, updates and starts Dwarfium Lite (Astro Dwarf Session) and Dwarfium Scope Archive from their GitHub
    releases: latest version check, download with progress and SHA-256 check, update that only replaces the
    program files (user data never touched), previous version kept for a rollback, fixed ports, start / stop one
    app or both. An existing installation can be adopted instead of reinstalled.
    ### Which application answers on a port
    The hub asks the port (GET /api/app-info, older versions recognised by their own API): another program on the
    port is shown as "Port X used by another program" and the application isn't started over it, instead of being
    taken for the application. The version of an adopted installation is read from the running application and
    recorded.
    ### LAN access
    Option to start Dwarfium Scope Archive reachable from the other devices of the network (--lan).
    ### Starting state
    An application the hub started shows "Starting…" until it answers (a one-file build unpacks itself first and
    can take a while), instead of "Running" then "Stopped"; Stop cancels the start.
    ### Start both: side by side
    Both applications start together, 5 s apart (Scope Archive first), instead of one after the other. Two
    applications can't be given the same port: the port field says "Taken", and starting is refused.
