"""Help of the Applications tab: install / update / rollback, start /
stop, and the launcher / watchdog (hub/watchdog.py). Markdown, English and
French."""
from __future__ import annotations

from hub.i18n import language

HELP_APPS = {
    "en": """
## Applications

One card per application: **Dwarfium Scope Archive** (archive, explore, plan) and **Dwarfium Lite** (it drives the Dwarfs).

### Install, update, go back

- **Install** downloads this system's build of the latest release; **Use an existing installation** takes a folder installed by hand instead.
- **Update to …** replaces the program files only: **your data is never touched** (Dwarfs, sessions, database, settings).
- **Back to …** restores the version the last update replaced. **What's new** shows the release notes.

### Start, stop

- Each application starts from its own folder on its **port** (Scope Archive 8080, Dwarfium Lite 8090 - editable). **Start both** starts Scope Archive, then Dwarfium Lite a few seconds later.
- Closing the hub leaves them running. **Stop** only stops an application the hub started: one started by hand is closed from its own window.
- **LAN access** (Scope Archive): reachable from the phone or tablet too. Dwarfium Lite always is.

### Launcher and watchdog

- **Start with the hub**: the application starts when the hub starts.
- **Restart automatically**: the hub starts it again when it stops by itself (a crash) - checked every 15 s. Not when you close its window, nor when you stop it from the hub (Stop, an update, Synchronize). At most 3 times within 10 min: then it gives up, said on its card, until you tick the box again.
- Only an application the hub started can be restarted. The card shows what was last done ("restarted at 21:00").
- **Start the hub with Windows** (under the install folder): the hub opens minimized when your Windows session opens, then starts the applications ticked **Start with the hub**. For a PC that runs the night unattended: after a Windows restart and the session opened, everything starts again.
- The hub is the watchdog: closed, nothing is watched (the applications keep running).
""",
    "fr": """
## Applications

Une carte par application : **Dwarfium Scope Archive** (archiver, explorer, planifier) et **Dwarfium Lite** (il pilote les Dwarfs).

### Installer, mettre à jour, revenir en arrière

- **Installer** télécharge la version de la dernière publication pour ce système ; **Utiliser une installation existante** reprend à la place un dossier installé à la main.
- **Mettre à jour en …** ne remplace que les fichiers du programme : **vos données ne sont jamais touchées** (Dwarfs, sessions, base, réglages).
- **Revenir à …** remet la version remplacée par la dernière mise à jour. **Nouveautés** affiche les notes de version.

### Lancer, arrêter

- Chaque application démarre depuis son dossier, sur son **port** (Scope Archive 8080, Dwarfium Lite 8090 - modifiable). **Lancer les deux** démarre Scope Archive, puis Dwarfium Lite quelques secondes après.
- Fermer le hub les laisse tourner. **Arrêter** n'arrête qu'une application lancée par le hub : une application lancée à la main se ferme depuis sa propre fenêtre.
- **Accès réseau local** (Scope Archive) : joignable aussi depuis le téléphone ou la tablette. Dwarfium Lite l'est toujours.

### Lanceur et surveillance

- **Lancer avec le hub** : l'application démarre au démarrage du hub.
- **Relance auto** : le hub la relance quand elle s'arrête d'elle-même (un plantage) - vérifié toutes les 15 s. Pas quand vous fermez sa fenêtre, ni quand vous l'arrêtez depuis le hub (Arrêter, une mise à jour, Synchroniser). Au plus 3 fois en 10 min : ensuite il abandonne, c'est dit sur sa carte, jusqu'à ce que vous recochiez la case.
- Seule une application lancée par le hub peut être relancée. La carte affiche la dernière action (« relancée à 21:00 »).
- **Lancer le hub avec Windows** (sous le dossier d'installation) : le hub s'ouvre réduit à l'ouverture de votre session Windows, puis lance les applications cochées **Lancer avec le hub**. Pour un PC qui tourne la nuit sans surveillance : après un redémarrage de Windows et la session ouverte, tout repart.
- Le hub est le surveillant : fermé, plus rien n'est surveillé (les applications continuent de tourner).
""",
}


def help_apps() -> str:
    return HELP_APPS.get(language(), HELP_APPS["en"])
