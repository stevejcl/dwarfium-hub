"""Help of the Installations tab: the home PC first, then each other
Dwarfium Lite (source run, laptop, mini PC) as an instance - on the home
network or through Tailscale. Markdown, English and French."""
from __future__ import annotations

from hub.i18n import language

HELP_INSTALLATIONS = {
    "en": """
## Installations

**The hub runs on your home PC** (or a home server): it installs and starts Dwarfium Lite and, if you want, Dwarfium Scope Archive there - the *Applications* tab.
Every other Dwarfium Lite you use - a source run for testing, a laptop, a mini PC next to the Dwarfs - is an **instance**: the hub doesn't start it, but shows its state on this map and synchronizes with it.

> **A Dwarf is driven by one Dwarfium Lite at a time.** When the map sees the same Dwarf connected to two installations, it says so in red.

### Once: this PC

1. *Applications* tab: install Dwarfium Lite (and Scope Archive if you want it).
2. For the other computers to reach it, share its folder on the network (right click → *Properties* → *Sharing*).

### Add an instance

Click **+ Add an instance**, then:

| Field | Example | What for |
|---|---|---|
| Name, type | Laptop · *Laptop* | the card |
| Access | *Home network* or *Tailscale* | where the card goes |
| Address | `192.168.0.60`, `laptop`, `minipc` (Tailscale) | its live state |
| Port | `8090` (a source run: the port you gave it) | its live state |
| Shared folder | `\\\\laptop\\AstroDwarfSession` | the synchronization |

**Check** asks the instance (Dwarfium Lite answers, its version, its Dwarfs) and opens the shared folder. Nothing is required but an address or a folder: a source run on this PC needs only its folder (`L:\\...\\astro_dwarf_session`) and `localhost` with its port.

- On the home network, give the computer a **fixed IP** in your box (or use its name), so the address doesn't change.
- Dwarfium Lite always listens on the network: nothing to set on its side. Windows may ask, the first time, to let it through the firewall: allow *private networks*.

### Reaching an instance away from home: Tailscale

[Tailscale](https://tailscale.com/download) makes a private, encrypted network between your machines - nothing to open on the box.

1. **Install Tailscale** on the home PC and on the laptop / mini PC, signed in to the same account.
2. **MagicDNS** (on by default) names each machine: the address is simply `minipc` (or its `100.x.y.z` IP, shown in the Tailscale window).
3. **Share + firewall**: share the Dwarfium Lite folder, then let the Tailscale network in - Windows often puts it in the *Public* profile: allow *File and printer sharing* (port 445) and Dwarfium Lite (port 8090) for public networks too, or set the Tailscale network to *Private*.

The card then shows the instance live, wherever it is, and the shared folder `\\\\minipc\\AstroDwarfSession` works for the synchronization.

**Sometimes at home, sometimes away** (a laptop, a mini PC that travels): one instance, access **Both** - its home network address and its Tailscale address. The home address is asked first, then the Tailscale one: the card goes to the band where it answered, so you see at a glance where it is. For its shared folder, the Tailscale name (`\\\\minipc\\...`) works in both cases.

**Scope Archive seen from that instance**: in its Dwarfium Lite, give Scope Archive's address with this PC's Tailscale name (`http://pc-name:8080`, Scope Archive started with LAN access) - it answers at home and away, nothing to change when the computer moves.

### The Dwarfs of a remote site, from home (FTP)

The Dwarfium Lite of the remote computer drives its Dwarfs on its own network: nothing more is needed for that. But **Scope Archive on this PC** downloads a Dwarf's images by **FTP** from the Dwarf itself: from home, the Dwarf (e.g. `192.168.88.21` on the site's Wi-Fi) is only reachable if the remote computer lets Tailscale through to its network - a **subnet router**:

1. On the remote computer, in a terminal opened as administrator:
   `tailscale set --advertise-routes=192.168.88.0/24` (the site's network: the Dwarf's IP with `.0/24` at the end - the card's tooltip gives it).
2. In the [Tailscale admin console](https://login.tailscale.com/admin/machines): that computer → *Edit route settings* → tick the route.
3. On this PC (Windows / macOS) the routes are used by default; on Linux: `tailscale set --accept-routes`.

The site's network must not be the same as the home one (two `192.168.0.x` networks can't be told apart): give the site's box or router another range if needed.

On the cards, each connected Dwarf has an **FTP** badge: green, this PC reaches its FTP; red, it doesn't (the tooltip says what to do). It is asked every 5 minutes, and again with the ⟳ button or **Check**. In Scope Archive, give that Dwarf its IP on the site's network.

### Troubleshooting the network

**"Network path not found" with the computer's name, but the IP works**: Windows resolved the name to another address (often a local IPv6 one, `fe80::...`) where sharing doesn't answer. Use the **Tailscale name in full** (`\\\\pc-name.tailXXXX.ts.net\\share`, the suffix is in the Tailscale admin console, *DNS* tab) or the **IP** (`\\\\100.x.y.z\\share`) - the Tailscale IP never changes.

Tests, in PowerShell on this PC:

| Test | Means |
|---|---|
| `Test-NetConnection 100.x.y.z -Port 445` → `TcpTestSucceeded : True` | sharing reachable through Tailscale |
| `Test-NetConnection 192.168.0.x -Port 445` → `True` | sharing reachable on the home network |
| `Test-NetConnection 100.x.y.z -Port 8090` → `True` | Dwarfium Lite reachable (its port) |
| `tailscale status` | the Tailscale names and IPs of your machines |
| `ping pc-name` → `100.x.y.z` | MagicDNS answers the short name |

- `False` on port 445: on the remote computer, share the folder, allow *File and printer sharing* in the firewall for the network profile in use (Tailscale is often *Public*), or set the home network to *Private*.
- `False` on Dwarfium Lite's port: allow it in the firewall (Windows asks the first time it starts - tick public networks too for Tailscale).
- A mapped drive (`W:\\`) works but belongs to your Windows session: the full `\\\\...` path is safer.
- Home address: reserve the computer's IP in your box (static DHCP lease) so it doesn't change.

### What the cards show

- ● running, with its version - ○ stopped (the computer answers, Dwarfium Lite doesn't) - ☁ unreachable (off, other network, Tailscale down).
- Its Dwarfs: connected, capturing, or only known; a clock when a program waits to be sent; FTP reached from this PC or not.
- The synchronization with this PC (checked when the hub starts) and a **Compare** button.
- **Open**: that Dwarfium Lite in your browser.
""",
    "fr": """
## Installations

**Le hub tourne sur votre PC de la maison** (ou un serveur à la maison) : il y installe et démarre Dwarfium Lite et, si vous le voulez, Dwarfium Scope Archive - onglet *Applications*.
Chaque autre Dwarfium Lite que vous utilisez - une version source pour tester, un portable, un mini PC à côté des Dwarfs - est une **instance** : le hub ne la démarre pas, mais montre son état sur cette carte et se synchronise avec elle.

> **Un Dwarf n'est piloté que par un seul Dwarfium Lite à la fois.** Quand la carte voit le même Dwarf connecté à deux installations, elle le signale en rouge.

### Une seule fois : ce PC

1. Onglet *Applications* : installez Dwarfium Lite (et Scope Archive si vous le voulez).
2. Pour que les autres ordinateurs le voient, partagez son dossier sur le réseau (clic droit → *Propriétés* → *Partage*).

### Ajouter une instance

Cliquez sur **+ Ajouter une instance**, puis :

| Champ | Exemple | Sert à |
|---|---|---|
| Nom, type | Portable · *Portable* | la carte |
| Accès | *Réseau maison* ou *Tailscale* | où va la carte |
| Adresse | `192.168.0.60`, `portable`, `minipc` (Tailscale) | son état en direct |
| Port | `8090` (version source : le port que vous lui donnez) | son état en direct |
| Dossier partagé | `\\\\portable\\AstroDwarfSession` | la synchronisation |

**Vérifier** interroge l'instance (Dwarfium Lite répond, sa version, ses Dwarfs) et ouvre le dossier partagé. Seule une adresse ou un dossier est nécessaire : une version source sur ce PC n'a besoin que de son dossier (`L:\\...\\astro_dwarf_session`) et de `localhost` avec son port.

- Sur le réseau de la maison, donnez à l'ordinateur une **IP fixe** dans votre box (ou utilisez son nom), pour que l'adresse ne change pas.
- Dwarfium Lite écoute toujours sur le réseau : rien à régler de son côté. Windows peut demander, la première fois, de le laisser passer le pare-feu : autorisez les *réseaux privés*.

### Joindre une instance hors de la maison : Tailscale

[Tailscale](https://tailscale.com/download) crée un réseau privé et chiffré entre vos machines - rien à ouvrir sur la box.

1. **Installez Tailscale** sur le PC de la maison et sur le portable / mini PC, connectés au même compte.
2. **MagicDNS** (activé par défaut) nomme chaque machine : l'adresse est simplement `minipc` (ou son IP `100.x.y.z`, visible dans la fenêtre de Tailscale).
3. **Partage + pare-feu** : partagez le dossier de Dwarfium Lite, puis laissez entrer le réseau Tailscale - Windows le classe souvent en profil *Public* : autorisez *Partage de fichiers et d'imprimantes* (port 445) et Dwarfium Lite (port 8090) aussi pour les réseaux publics, ou passez le réseau Tailscale en *Privé*.

La carte montre alors l'instance en direct, où qu'elle soit, et le dossier partagé `\\\\minipc\\AstroDwarfSession` fonctionne pour la synchronisation.

**Tantôt à la maison, tantôt ailleurs** (un portable, un mini PC qui voyage) : une seule instance, accès **Les deux** - son adresse sur le réseau maison et son adresse Tailscale. L'adresse maison est interrogée d'abord, puis l'adresse Tailscale : la carte se place dans la zone où elle a répondu, vous voyez d'un coup d'œil où elle se trouve. Pour son dossier partagé, le nom Tailscale (`\\\\minipc\\...`) fonctionne dans les deux cas.

**Scope Archive vu depuis cette instance** : dans son Dwarfium Lite, indiquez l'adresse de Scope Archive avec le nom Tailscale de ce PC (`http://nom-du-pc:8080`, Scope Archive démarré avec l'accès réseau) - elle répond à la maison comme ailleurs, rien à changer quand l'ordinateur se déplace.

### Les Dwarfs d'un site distant, depuis la maison (FTP)

Le Dwarfium Lite de l'ordinateur distant pilote ses Dwarfs sur son propre réseau : rien de plus n'est nécessaire pour cela. Mais **Scope Archive sur ce PC** télécharge les images d'un Dwarf par **FTP**, directement depuis le Dwarf : depuis la maison, le Dwarf (par exemple `192.168.88.21` sur le Wi-Fi du site) n'est joignable que si l'ordinateur distant laisse passer Tailscale vers son réseau - un **routeur de sous-réseau** :

1. Sur l'ordinateur distant, dans un terminal ouvert en administrateur :
   `tailscale set --advertise-routes=192.168.88.0/24` (le réseau du site : l'IP du Dwarf terminée par `.0/24` - l'info-bulle de la carte la donne).
2. Dans la [console d'administration Tailscale](https://login.tailscale.com/admin/machines) : cet ordinateur → *Edit route settings* → cochez la route.
3. Sur ce PC (Windows / macOS) les routes sont utilisées par défaut ; sous Linux : `tailscale set --accept-routes`.

Le réseau du site ne doit pas être le même que celui de la maison (deux réseaux `192.168.0.x` ne peuvent pas être distingués) : donnez si besoin une autre plage à la box ou au routeur du site.

Sur les cartes, chaque Dwarf connecté a un badge **FTP** : vert, ce PC joint son FTP ; rouge, il ne le joint pas (l'info-bulle dit quoi faire). Il est vérifié toutes les 5 minutes, et à nouveau avec le bouton ⟳ ou **Vérifier**. Dans Scope Archive, donnez à ce Dwarf son IP sur le réseau du site.

### Dépannage réseau

**« Chemin réseau introuvable » avec le nom de l'ordinateur, alors que l'IP fonctionne** : Windows a résolu le nom vers une autre adresse (souvent une IPv6 locale, `fe80::...`) où le partage ne répond pas. Utilisez le **nom Tailscale complet** (`\\\\nom-du-pc.tailXXXX.ts.net\\partage`, le suffixe est dans la console d'administration Tailscale, onglet *DNS*) ou l'**IP** (`\\\\100.x.y.z\\partage`) - l'IP Tailscale ne change jamais.

Tests, dans PowerShell sur ce PC :

| Test | Signifie |
|---|---|
| `Test-NetConnection 100.x.y.z -Port 445` → `TcpTestSucceeded : True` | partage joignable par Tailscale |
| `Test-NetConnection 192.168.0.x -Port 445` → `True` | partage joignable sur le réseau maison |
| `Test-NetConnection 100.x.y.z -Port 8090` → `True` | Dwarfium Lite joignable (son port) |
| `tailscale status` | les noms et IP Tailscale de vos machines |
| `ping nom-du-pc` → `100.x.y.z` | MagicDNS répond au nom court |

- `False` sur le port 445 : sur l'ordinateur distant, partagez le dossier, autorisez *Partage de fichiers et d'imprimantes* dans le pare-feu pour le profil réseau utilisé (Tailscale est souvent *Public*), ou passez le réseau maison en *Privé*.
- `False` sur le port de Dwarfium Lite : autorisez-le dans le pare-feu (Windows le demande au premier démarrage - cochez aussi les réseaux publics pour Tailscale).
- Un lecteur réseau (`W:\\`) fonctionne mais dépend de votre session Windows : le chemin complet `\\\\...` est plus sûr.
- Adresse maison : réservez l'IP de l'ordinateur dans votre box (bail DHCP statique) pour qu'elle ne change pas.

### Ce que montrent les cartes

- ● actif, avec sa version - ○ arrêté (l'ordinateur répond, pas Dwarfium Lite) - ☁ injoignable (éteint, autre réseau, Tailscale arrêté).
- Ses Dwarfs : connecté, en capture, ou seulement connu ; une horloge quand un programme attend d'être envoyé ; FTP joint depuis ce PC ou non.
- La synchronisation avec ce PC (vérifiée au démarrage du hub) et un bouton **Comparer**.
- **Ouvrir** : ce Dwarfium Lite dans votre navigateur.
""",
}


def help_installations() -> str:
    return HELP_INSTALLATIONS.get(language(), HELP_INSTALLATIONS["en"])
