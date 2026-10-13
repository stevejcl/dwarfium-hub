# Changelog

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
