# Changelog

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
