# Changelog

## [0.1.3] - 2026-10-16
  ### Add
    ### Launcher and watchdog
    Each application's card: "Start with the hub" (started when the hub starts) and "Restart automatically"
    (started again when it stops by itself - a crash, a non-zero exit code; not when its window is closed nor when
    it is stopped from the hub: Stop, an update, Synchronize). At most 3 restarts within 10 min, then it gives up
    until the box is ticked again - shown on the card with the last thing done ("restarted at 21:00 (exit code 1)").
    Windows: "Start the hub with Windows" (the session's Run key, no administrator rights; the built hub only) - the
    hub then opens minimized and starts the applications ticked. It runs in the hub's process: a reloaded window
    doesn't stop it; the hub closed, nothing is watched (the applications keep running). Only an application the hub
    started can be restarted (one started by hand gives no exit code).
    The Applications tab has a Help button too (install / update / rollback, start / stop, the launcher and watchdog).
    Scope Archive's card: LAN access with the two start options on one line (was a line of its own), a shorter page.
  ### BugFix
    ### Startup: "The client this element belongs to has been deleted"
    The window reloaded or closed while the startup check of the shared folders was still running (up to 20 s per
    folder not answering): its notice then had no page left to show in. Dropped silently now; any notice of the hub
    is skipped when its page is gone.

## [0.1.2] - 2026-10-16
  ### BugFix
    ### Windows: ConnectionResetError at exit
    "Exception in callback _ProactorBasePipeTransport._call_connection_lost ... WinError 10054" printed when the hub
    closes (the window's connection already reset): harmless cleanup noise, now logged at DEBUG only - the same
    filter as Dwarfium Lite's.
    ### Synchronize: the count follows the ticks
    The preview's "n change(s)" didn't change when lines were unticked: now "s of n change(s) selected", updated at
    each tick, with Tick all / Untick all; Synchronize disabled when nothing is ticked.
    ### Synchronize: dashboard display
    "Preferences - missing" said nothing: now "Dashboard display - missing - hidden, position 2" (Dwarfium Lite's
    device_prefs.json). A Dwarf's display, when the other side doesn't have that Dwarf, is ticked with the Dwarf's
    own copy (unticking the Dwarf unticks it); not proposed for a Dwarf neither side has any more.
    ### Startup: "'>' not supported between instances of 'NoneType' and 'int'"
    A shared folder not answering within 20 s at the hub's startup check (computer off, Tailscale down): NiceGUI's
    run.io_bound, cancelled by the timeout, gives None instead of raising - the check then failed. None now counts
    as not reachable there, in the Installations states and Check, and in Synchronize / Identify.
  ### Add
    ### Logo
    Dwarfium-Hub's own logo: the Dwarf's lens - the hub - linked to the installations it looks after (the green one:
    Scope Archive), on the night-blue disc of Dwarfium Lite's icon. The executable's icon (DwarfiumHub.ico), the
    window's favicon (instead of 🔭) and next to the page's title.
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
    the tab is shown); its Dwarfs (connected, busy, connecting, program waiting); its synchronization with this PC and a
    Compare button; Open in the browser. A Dwarf connected to two installations shown in red. Add / change an
    instance: name, type, access, address, port, shared folder, with a Check (Dwarfium Lite answers, its Dwarfs, the
    folder reachable). The Synchronize tab's folders are the instances' shared folders (the ones added before become
    instances). A Help button: this PC, adding an instance, Tailscale (MagicDNS, sharing and firewall).
    Access "Both" for a laptop or mini PC sometimes at home, sometimes away: its home address asked first, then its
    Tailscale one; the card goes to the band where it answered ("reached through Tailscale").
    FTP badge on each connected Dwarf: its FTP (what Scope Archive downloads from) reached from this PC or not -
    asked every 5 minutes, again with the refresh button or Check; for a Dwarf on a remote site, the Tailscale
    subnet route to add (its network in the tooltip, the steps in the Help).
    Help "Troubleshooting the network": a name giving "network path not found" while the IP works (resolved to a
    local IPv6 address) - the full Tailscale name or the IP instead; PowerShell tests (ports 445 and 8090,
    tailscale status); firewall, mapped drive, fixed home IP.
    ### Dwarfs tab: another installation
    A Dwarfium Lite list: this PC's or an instance with a shared folder - its Dwarfs read and changed through the
    folder, only when the instance says Dwarfium Lite is stopped there (or, no address to ask, when confirmed); its
    links to Scope Archive written with Scope Archive's address as that computer reaches it (kept per instance, this
    PC's name by default - its Tailscale name works at home and away). Identify and its pages through that
    instance's Dwarfium Lite.
    A link written with another Scope Archive address than that one (an old name, localhost on a remote computer,
    another port - on this PC only the port counts) shown on its row, with Update the address (one, or all).

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
