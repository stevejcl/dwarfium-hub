"""Help of the Synchronize tab (user-requested Oct 2026): the simplest
case - Dwarfium Lite on the home PC, and on a laptop taken for a weekend
or holidays - as what to do before leaving, when back, and when the
laptop is used at home instead. Markdown, English and French."""
from __future__ import annotations

from hub.i18n import language

HELP_SYNC = {
    "en": """
## Synchronize two Dwarfium Lite installations

**The usual case:** Dwarfium Lite on your **home PC**, and another one on a **laptop** you take for a weekend or holidays to shoot elsewhere (with its own sites).
Both have the same Dwarfs, but each installation keeps its own list of programs, results and sites: synchronizing brings them together, both ways.

> **The golden rule:** a Dwarf is driven by **one** Dwarfium Lite at a time. Before switching from one computer to the other, synchronize - and never leave both connected to the same Dwarf.

### Once: let the hub see the laptop

1. On the laptop, share the Dwarfium Lite folder (right click → *Properties* → *Sharing*).
2. In the hub (on the home PC), **Add a folder** → `\\\\laptop-name\\share`. It is kept for next time.
3. At each hub start, the laptop is compared in the background when it is on the network: a notice tells you when something differs.

### Before leaving for the weekend

1. Prepare your programs (targets for the trip) in Dwarfium Lite on the PC - or directly on the laptop.
2. Laptop on and on the home network. In the hub: **Synchronize** tab → A = the hub's Dwarfium Lite, B = the laptop.
3. Make sure Dwarfium Lite is **closed on the laptop**, tick the confirmation.
4. **Compare**: check the list - the programs to run (*ToDo*) go to the laptop, flagged with an orange dot.
5. **Synchronize**: the hub stops its own Dwarfium Lite meanwhile, makes a backup of both sides, then starts it again.

On site, use Dwarfium Lite **on the laptop only**. Add the new observing site there (Wi-Fi, location): it will come back with the rest.

### Back home

1. Laptop on the home network, **Dwarfium Lite closed on the laptop**.
2. **Compare** (or the hub's notice at startup): the programs run during the weekend are *Done* on the laptop - they replace the *ToDo* copies of the PC, so they will **not be run again**. Their results and the new sites come to the PC.
3. **Synchronize**. Back to the PC for the next nights.

### Using the laptop at home instead of the PC

Same thing as a trip, without leaving:

1. **Synchronize** before switching to the laptop (PC → laptop: the programs to run).
2. Close Dwarfium Lite on the PC, use the laptop.
3. **Synchronize** again before going back to the PC (laptop → PC: what was done, the results).

### Good to know

- **Dwarfs** are recognized by their identifier (the end of their Bluetooth name), whatever their name on each side. Their **IP is never changed**: it can be different at home and in the field.
- **A program at two stages**: the most advanced wins (*Done* / *Error* over *Current* over *ToDo*); at the same stage, the latest written.
- **Sites and dashboard display** (a Dwarf hidden, the cards' order): what is missing on one side is copied - a Dwarf's display only with that Dwarf when the other side doesn't have it; one different on each side is only shown, never overwritten.
- **Nothing is written before Synchronize**, every line can be unticked, and a **zip backup** of both installations is made first (in their `sync_backups` folder).
- **A remote laptop or mini PC** (not on the home network): with Tailscale, the share works the same way (`\\\\tailscale-name\\share`) - see the README.
""",
    "fr": """
## Synchroniser deux installations de Dwarfium Lite

**Le cas habituel :** Dwarfium Lite sur votre **PC à la maison**, et un autre sur un **portable** que vous emmenez en week-end ou en vacances pour faire des sessions ailleurs (avec ses propres lieux).
Les deux ont les mêmes Dwarfs, mais chaque installation garde sa propre liste de programmes, de résultats et de lieux : la synchronisation les réunit, dans les deux sens.

> **La règle d'or :** un Dwarf n'est piloté que par **un seul** Dwarfium Lite à la fois. Avant de passer d'un ordinateur à l'autre, synchronisez - et ne laissez jamais les deux connectés au même Dwarf.

### Une seule fois : que le hub voie le portable

1. Sur le portable, partagez le dossier de Dwarfium Lite (clic droit → *Propriétés* → *Partage*).
2. Dans le hub (sur le PC), **Ajouter un dossier** → `\\\\nom-du-portable\\partage`. Il est mémorisé.
3. À chaque démarrage du hub, le portable est comparé en arrière-plan s'il est sur le réseau : une notification vous prévient s'il y a des différences.

### Avant de partir en week-end

1. Préparez vos programmes (les cibles du séjour) dans Dwarfium Lite sur le PC - ou directement sur le portable.
2. Portable allumé et sur le réseau de la maison. Dans le hub : onglet **Synchroniser** → A = le Dwarfium Lite du hub, B = le portable.
3. Vérifiez que Dwarfium Lite est **fermé sur le portable**, cochez la confirmation.
4. **Comparer** : vérifiez la liste - les programmes à faire (*ToDo*) partent vers le portable, signalés par une pastille orange.
5. **Synchroniser** : le hub arrête son Dwarfium Lite le temps de la synchronisation, sauvegarde les deux côtés, puis le relance.

Sur place, utilisez Dwarfium Lite **uniquement sur le portable**. Ajoutez-y le nouveau lieu d'observation (Wi-Fi, position) : il reviendra avec le reste.

### Au retour

1. Portable sur le réseau de la maison, **Dwarfium Lite fermé sur le portable**.
2. **Comparer** (ou la notification du hub au démarrage) : les programmes faits pendant le week-end sont *Done* sur le portable - ils remplacent les copies *ToDo* du PC, ils ne seront donc **pas relancés**. Leurs résultats et les nouveaux lieux arrivent sur le PC.
3. **Synchroniser**. Vous repassez sur le PC pour les nuits suivantes.

### Utiliser le portable à la maison à la place du PC

Comme pour un séjour, sans partir :

1. **Synchroniser** avant de passer sur le portable (PC → portable : les programmes à faire).
2. Fermez Dwarfium Lite sur le PC, utilisez le portable.
3. **Synchroniser** à nouveau avant de revenir au PC (portable → PC : ce qui a été fait, les résultats).

### Bon à savoir

- **Les Dwarfs** sont reconnus par leur identifiant (la fin de leur nom Bluetooth), quel que soit leur nom de chaque côté. Leur **IP n'est jamais modifiée** : elle peut être différente à la maison et sur le terrain.
- **Un programme à deux stades** : le plus avancé l'emporte (*Done* / *Error* sur *Current* sur *ToDo*) ; au même stade, le plus récent.
- **Lieux et affichage du tableau de bord** (un Dwarf masqué, l'ordre des cartes) : ce qui manque d'un côté est copié - l'affichage d'un Dwarf seulement avec ce Dwarf quand l'autre côté ne l'a pas ; un élément différent de chaque côté est seulement signalé, jamais écrasé.
- **Rien n'est écrit avant Synchroniser**, chaque ligne peut être décochée, et une **sauvegarde zip** des deux installations est faite avant (dans leur dossier `sync_backups`).
- **Un portable ou un mini PC à distance** (pas sur le réseau de la maison) : avec Tailscale, le partage fonctionne de la même façon (`\\\\nom-tailscale\\partage`) - voir le README.
""",
}


def help_sync() -> str:
    return HELP_SYNC.get(language(), HELP_SYNC["en"])
