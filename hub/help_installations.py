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

### What the cards show

- ● running, with its version - ○ stopped (the computer answers, Dwarfium Lite doesn't) - ☁ unreachable (off, other network, Tailscale down).
- Its Dwarfs: connected, capturing, or only known; a clock when a program waits to be sent.
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

### Ce que montrent les cartes

- ● actif, avec sa version - ○ arrêté (l'ordinateur répond, pas Dwarfium Lite) - ☁ injoignable (éteint, autre réseau, Tailscale arrêté).
- Ses Dwarfs : connecté, en capture, ou seulement connu ; une horloge quand un programme attend d'être envoyé.
- La synchronisation avec ce PC (vérifiée au démarrage du hub) et un bouton **Comparer**.
- **Ouvrir** : ce Dwarfium Lite dans votre navigateur.
""",
}


def help_installations() -> str:
    return HELP_INSTALLATIONS.get(language(), HELP_INSTALLATIONS["en"])
