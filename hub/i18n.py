"""Texts of the hub, English and French (the hub's setting, else the
system's language)."""
from __future__ import annotations

import locale

TEXTS = {
    "en": {
        "subtitle": "Install, update and start the Dwarfium applications",
        "desc_scope_archive": "Archive, explore and plan your Dwarf sessions",
        "desc_astro_dwarf_session": "Control your Dwarfs, programs and schedules",
        "install_root": "Install folder",
        "change": "Change",
        "installed": "Installed",
        "not_installed": "Not installed",
        "unknown_version": "version unknown (installed outside the hub)",
        "latest": "Latest",
        "checking": "checking…",
        "no_network": "can't reach GitHub",
        "no_asset": "no build for this system in the latest release",
        "up_to_date": "Up to date",
        "install": "Install",
        "update": "Update to {v}",
        "reinstall": "Reinstall",
        "whats_new": "What's new",
        "start": "Start",
        "stop": "Stop",
        "open_folder": "Open folder",
        "rollback": "Back to {v}",
        "rollback_previous": "Back to the previous version",
        "adopt": "Use an existing installation",
        "adopt_hint": "Folder of the existing installation (with {exe})",
        "adopt_bad": "{exe} is not in this folder",
        "port": "Port",
        "running": "Running on port {port}",
        "stopped": "Stopped",
        "port_other": "Port {port} used by another program",
        "port_other_hint": "Another program answers on this port: close it, or give this application another port",
        "port_other_start": "{name} can't start: port {port} is used by another program. Close it, or change the port.",
        "lan": "LAN access",
        "lan_hint": "Reachable from the other devices of the network (phone, tablet), not only from this computer",
        "lan_restart": "Restart {name} to apply the LAN access",
        "start_both": "Start both",
        "stop_both": "Stop both",
        "downloading": "Downloading {v}…",
        "installing": "Installing…",
        "installed_ok": "{name} {v} installed",
        "rolled_back": "{name}: back to {v}",
        "stop_first": "Stop {name} before updating it",
        "stop_outside": "{name} wasn't started from the hub: close it from its own window",
        "started": "{name} started",
        "start_failed": "{name} didn't start: {e}",
        "failed": "Failed: {e}",
        "ok": "OK",
        "cancel": "Cancel",
        "language": "Language",
        "data_safe": "Your data (devices, sessions, database, settings) is never touched by an update.",
    },
    "fr": {
        "subtitle": "Installer, mettre à jour et lancer les applications Dwarfium",
        "desc_scope_archive": "Archiver, explorer et planifier vos sessions Dwarf",
        "desc_astro_dwarf_session": "Piloter vos Dwarfs, programmes et plannings",
        "install_root": "Dossier d'installation",
        "change": "Changer",
        "installed": "Installée",
        "not_installed": "Non installée",
        "unknown_version": "version inconnue (installée hors du hub)",
        "latest": "Dernière",
        "checking": "vérification…",
        "no_network": "GitHub injoignable",
        "no_asset": "pas de build pour ce système dans la dernière version",
        "up_to_date": "À jour",
        "install": "Installer",
        "update": "Mettre à jour en {v}",
        "reinstall": "Réinstaller",
        "whats_new": "Nouveautés",
        "start": "Lancer",
        "stop": "Arrêter",
        "open_folder": "Ouvrir le dossier",
        "rollback": "Revenir à {v}",
        "rollback_previous": "Revenir à la version précédente",
        "adopt": "Utiliser une installation existante",
        "adopt_hint": "Dossier de l'installation existante (avec {exe})",
        "adopt_bad": "{exe} n'est pas dans ce dossier",
        "port": "Port",
        "running": "Lancée sur le port {port}",
        "stopped": "Arrêtée",
        "port_other": "Port {port} utilisé par un autre programme",
        "port_other_hint": "Un autre programme répond sur ce port : fermez-le, ou donnez un autre port à cette application",
        "port_other_start": "{name} ne peut pas démarrer : le port {port} est utilisé par un autre programme. Fermez-le, ou changez de port.",
        "lan": "Accès réseau local",
        "lan_hint": "Accessible depuis les autres appareils du réseau (téléphone, tablette), pas seulement depuis cet ordinateur",
        "lan_restart": "Relancez {name} pour appliquer l'accès réseau local",
        "start_both": "Lancer les deux",
        "stop_both": "Arrêter les deux",
        "downloading": "Téléchargement de {v}…",
        "installing": "Installation…",
        "installed_ok": "{name} {v} installée",
        "rolled_back": "{name} : retour à {v}",
        "stop_first": "Arrêtez {name} avant de la mettre à jour",
        "stop_outside": "{name} n'a pas été lancée par le hub : fermez-la depuis sa fenêtre",
        "started": "{name} lancée",
        "start_failed": "{name} n'a pas démarré : {e}",
        "failed": "Échec : {e}",
        "ok": "OK",
        "cancel": "Annuler",
        "language": "Langue",
        "data_safe": "Vos données (Dwarfs, sessions, base, réglages) ne sont jamais touchées par une mise à jour.",
    },
}

_lang = "en"


def system_language() -> str:
    try:
        code = (locale.getlocale()[0] or "").lower()
    except (ValueError, TypeError):
        code = ""
    return "fr" if code.startswith("fr") else "en"


def set_language(lang: str) -> None:
    global _lang
    _lang = lang if lang in TEXTS else "en"


def language() -> str:
    return _lang


def t(key: str, **kwargs) -> str:
    text = TEXTS[_lang].get(key) or TEXTS["en"].get(key) or key
    return text.format(**kwargs) if kwargs else text
