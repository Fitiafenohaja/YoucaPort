# YoucaPort

[![PyPI version](https://img.shields.io/pypi/v/youcaport)](https://pypi.org/project/youcaport/)
[![Python versions](https://img.shields.io/pypi/pyversions/youcaport)](https://pypi.org/project/youcaport/)
[![CI](https://github.com/Fitiafenohaja/YoucaPort/actions/workflows/ci.yml/badge.svg)](https://github.com/Fitiafenohaja/YoucaPort/actions/workflows/ci.yml)
[![Licence](https://img.shields.io/github/license/Fitiafenohaja/YoucaPort)](./LICENSE)

> Gestionnaire de ports en ligne de commande — trouve, vérifie et libère les ports réseau
> utilisés localement, sans avoir besoin de connaître `lsof`, `ss`, `netstat` ou `kill`.

Testé et livré en continu sur **Linux**, **Windows** et **macOS** (Python 3.11+).

---

## Sommaire

1. [Démarrage rapide](#démarrage-rapide)
2. [Pourquoi YoucaPort ?](#pourquoi-youcaport-)
3. [Installation](#installation)
4. [Utilisation](#utilisation)
5. [Fonctionnalités](#fonctionnalités)
6. [Windows et macOS](#windows-et-macos)
7. [Démarrage d'un processus](#démarrage-dun-processus)
8. [Développement](#développement)
9. [Intégration continue et publication](#intégration-continue-et-publication)
10. [Limites de cette version](#limites-de-cette-version)
11. [Licence](#licence)

---

## Démarrage rapide

```bash
pipx install youcaport          # installé dans son propre environnement (recommandé)

youcaport status                # ports en écoute avec processus & conteneurs identifiés
youcaport check 3000            # un port libre ou occupé ?
youcaport free 3000             # libérer un port (confirmation obligatoire)
youcaport dashboard             # interface web locale : http://127.0.0.1:8421
```

```text
$ youcaport status

17 port(s) en écoute — 5 processus identifiés, 12 non identifiés

PORT    APPLICATION    PID      ÉTAT
──────  ─────────────   ──────   ──────────────
3000    Next.js         447315   En écoute
5173    Vite            321456   En écoute
5432    postgres:16     189230   En écoute (Docker)
```

---

## Pourquoi YoucaPort ?

Quand vous lancez un projet (Next.js, FastAPI, PostgreSQL, Vite...), il arrive que le port
soit déjà occupé :

```text
EADDRINUSE: address already in use
```

Plutôt que de jongler avec `lsof -i :3000`, `kill -9 <PID>` ou le jeu de `ss`/`netstat`,
YoucaPort centralise tout dans une interface simple et claire en français. Il va plus loin en
identifiant les processus **protégés** (services système, moteur Docker) grâce à un mode sudo,
et en vous proposant les **ports libres** proches en cas de conflit.

---

## Installation

### pipx (recommandé pour une CLI)

Sur Debian/Ubuntu, `pip install` global refuse d'installer dans un système géré
(externally-managed, PEP 668) : `pipx` crée un environnement isolé dédié à la CLI.

```bash
sudo apt install pipx           # ou : brew install pipx
pipx install youcaport
```

### pip (environnement virtuel)

```bash
python3 -m venv ~/youcaport-venv
~/youcaport-venv/bin/pip install youcaport
~/youcaport-venv/bin/youcaport --version
```

### Depuis les sources

```bash
git clone https://github.com/Fitiafenohaja/YoucaPort.git
cd youcaport
poetry install
poetry build
pipx install dist/youcaport-*.whl
```

### Exécutable autonome

Un binaire sans Python requis est joint à chaque [release GitHub](https://github.com/Fitiafenohaja/YoucaPort/releases) :

```bash
./dist/youcaport --help
```

**Prérequis** : Python 3.11+. Plateformes supportées : **Linux**, **Windows**, **macOS**
(couvertes par les jobs CI).

---

## Utilisation

### Menu interactif

```bash
youcaport
```

Lance le menu principal (version affichée, astuce d'utilisation) : ports utilisés, vérifier
un port, libérer un port, accès aux fonctionnalités avancées via un sous-menu.

### Commandes directes

```bash
youcaport status                      # tous les ports en écoute
youcaport check 3000                  # un port précis
youcaport free 3000                   # libérer après confirmation obligatoire
youcaport --help                      # aide complète (riche, avec astuces --sudo)
youcaport --version
```

```text
$ youcaport check 3000

✗ Port 3000 occupé

Application : Next.js
PID          : 447315
État         : En cours d'exécution

Ports libres suggérés : 3001, 3002, 3003
```

---

## Fonctionnalités

### Ports libres à proximité — Auto Port

Quand un port est occupé, `check` propose automatiquement des ports libres proches. Une
commande dédiée existe aussi :

```bash
youcaport suggest 3000 --count 5      # 5 ports libres autour de 3000
```

### Profils de projets — Port Profiles

Associez des ports à des projets nommés (stockage : `~/.config/youcaport/profiles.json`) :

```bash
youcaport profile add frontend 3000    # associe le port 3000 au projet "frontend"
youcaport profile list                 # liste les profils
youcaport profile show frontend        # état des ports d'un profil
youcaport profile remove frontend      # supprime le profil
```

### Ports d'un projet — Project Management

Détecte automatiquement les ports utilisés par les processus lancés depuis un dossier :

```bash
youcaport project /chemin/vers/mon/projet
youcaport project .                    # depuis le dossier du projet
```

### Dashboard web local

Interface web locale (bibliothèque standard, aucune dépendance supplémentaire), mise à jour
manuelle ou automatique :

```bash
youcaport dashboard                    # ouvre http://127.0.0.1:8421
youcaport dashboard --port 9000        # port différent
youcaport dashboard --no-browser       # ne pas ouvrir le navigateur
```

- Statistiques (total, identifiés, non identifiés)
- Recherche et tri par colonne
- Badges d'état et compte à rebours de rafraîchissement
- API JSON sur `/api/ports` pour l'intégration

### Ports protégés (root / docker) — mode sudo

Certains écouteurs (services système, moteur Docker, autre utilisateur) ne sont pas
identifiables par un utilisateur normal : YoucaPort les affiche comme occupés mais
**non identifiés**, sans pouvoir les arrêter. Le mode `--sudo` lève ce voile en interrogeant
`ss` avec les privilèges root :

```bash
youcaport status --sudo            # identifie les ports protégés
youcaport check 8080 --sudo        # détail d'un port protégé
youcaport free 9100 --sudo         # arrête réellement le processus protégé (TERM puis KILL)
youcaport dashboard --sudo         # enrichit l'API/la page (uniquement si sudo déjà authentifié)
```

Comportements importants :

- **CLI** : si sudo n'est pas encore authentifié, le mot de passe est **demandé** au
  lancement ; sans terminal, un message invite à lancer une fois `sudo -v`.
- **Dashboard** : jamais de demande de mot de passe — seuls les identifiants en cache sont
  utilisés (`sudo -n`), sinon les ports restent « non identifiés ».
- L'arrêt reste **toujours confirmé** et passe par **TERM puis KILL** en dernier recours.
- Disponible **sous Linux uniquement** (`ss`) — sans effet sous Windows et macOS.

### Gestion des conteneurs Docker

Quand un port est occupé par le moteur Docker, identifiez puis arrêtez le bon conteneur
(`docker-proxy` n'est qu'un relais — arrêter le conteneur est la bonne manière) :

```bash
youcaport docker list             # conteneurs actifs + leurs ports hôtes
youcaport docker show 5432        # conteneur qui publie le port 5432 (détails)
youcaport docker stop 5432        # arrête le conteneur (confirmation obligatoire)
```

```text
Port 5432 → conteneur Docker
Nom    : postgres-dev
ID     : a1b2c3d4e5f6
Image  : postgres:16
Statut : Up 2 hours
```

Fonctionne partout où le CLI `docker` est disponible. Après l'arrêt, le port revient libre :
`youcaport status` le confirme.

---

## Windows et macOS

YoucaPort est **multiplateforme** (psutil est croisé, couvert par des jobs CI dédiés).

- **Installation** : `pipx install youcaport` (ou via venv).
- **Arrêt d'un processus** : sous Windows, SIGTERM n'existe pas — `terminate()` réalise un
  arrêt immédiat. YoucaPort vous en avertit explicitement avant la confirmation.
- **Profil de projets** :
  - Linux / macOS : `~/.config/youcaport/profiles.json`
  - Windows : `%LOCALAPPDATA%\youcaport\`
- **macOS** : lorsque l'énumération réseau psutil est restreinte (ex. certains contextes
  d'exécution), YoucaPort bascule automatiquement sur `lsof` puis `netstat` — les ports
  restent listés, les processus sans privilège apparaissent en « non identifiés ».
- **Mode sudo et Docker** : Docker fonctionne sur les trois plateformes ; le mode `--sudo`
  est propre à Linux.

---

## Démarrage d'un processus

YoucaPort ne tue jamais brutalement par défaut :

1. **Confirmation obligatoire** (`y/N`) avec rappel de l'application, du PID et du port.
2. Envoi d'un **SIGTERM** (arrêt propre) — `terminate()` sous Windows.
3. Période de grâce de **3 secondes**.
4. **SIGKILL** uniquement si le processus n'a pas répondu au SIGTERM.

Aucune stack trace n'est jamais affichée : chaque erreur (port invalide, permission
insuffisante, processus déjà arrêté...) est traduite en message clair en français, avec un
code de sortie approprié (`0` ou `1`).

---

## Développement

```bash
make install        # ou : poetry install
make test           # ou : poetry run pytest
make lint           # ou : poetry run ruff check .
make format         # ou : poetry run ruff format .
make build          # ou : poetry build
make binary         # ou : ./scripts/dev.sh binary
```

Toutes ces commandes sont aussi disponibles via `scripts/dev.sh`.

**Conventions** : Ruff (100 colonnes) ; lint + format vérifiés en CI ; régression garantie
par `pytest` sur les trois plateformes.

---

## Intégration continue et publication

`.github/workflows/ci.yml` exécute à chaque push/PR :

- **quality** : lint (`ruff check`, `ruff format --check`) + tests (`pytest`) — Python 3.11
  et 3.12 (Linux)
- **tests-windows** : tests sur `windows-latest`, Python 3.12
- **tests-macos** : tests sur `macos-latest`, Python 3.12
- **publish** : déclenché uniquement sur les tags `v*` — publication sur **PyPI** via
  **trusted publishing** (OIDC, aucun token PyPI stocké en secret).

```bash
git tag v0.1.0
git push origin v0.1.0      # déclenche quality + windows + macOS + publication PyPI
```

À compléter manuellement : la **release GitHub** avec le binaire autonome
(`gh release create <tag> dist/youcaport`).

---

## Limites de cette version

Conformément au cahier des charges, YoucaPort reste volontairement simple :

- **Dashboard lourd / comptes / base de données** : hors périmètre ; le dashboard est
  volontairement léger (page locale, stdlib).

---

## Licence

Voir [LICENSE](./LICENSE).