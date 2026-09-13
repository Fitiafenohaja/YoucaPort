# YoucaPort

**Gestionnaire de ports en ligne de commande** — trouve, vérifie et libère les ports réseau
utilisés localement, sans avoir besoin de connaître `lsof`, `ss`, `netstat` ou `kill`.

```text
╭──────────────────────────────╮
│          PORTKEEPER          │
│      Port Manager CLI        │
╰──────────────────────────────╯

1. Ports utilisés
2. Vérifier un port
3. Libérer un port
4. Quitter

Choix :
```

---

## Pourquoi YoucaPort ?

Quand vous lancez un projet (Next.js, FastAPI, PostgreSQL, Vite...), il arrive que le port
soit déjà occupé :

```text
EADDRINUSE: address already in use
```

Plutôt que de jongler avec `lsof -i :3000`, `kill -9 <PID>` et autres commandes système,
YoucaPort centralise tout dans une interface simple :

```text
PORT    APPLICATION    PID      STATUS
────────────────────────────────────────
3000    Next.js        447315   RUNNING
5173    Vite           321456   RUNNING
8000    Uvicorn        221890   RUNNING
5432    PostgreSQL     189230   RUNNING
```

---

## Installation

### Avec pipx (recommandé)

```bash
pipx install youcaport
```

### Avec pip

```bash
pip install youcaport
```

### Depuis les sources

```bash
git clone https://github.com/Fitiafenohaja/YoucaPort.git
cd youcaport
poetry install
poetry build
pipx install dist/youcaport-*.whl
```

**Prérequis** : Python 3.11+. Plateforme prioritaire : **Linux** (Windows/macOS non testés
pour cette version, mais l'architecture est déjà abstraite pour une extension future).

---

## Utilisation

### Menu interactif

```bash
youcaport
```

Lance le menu principal : ports utilisés / vérifier un port / libérer un port / quitter.

### Commandes directes

```bash
# Lister tous les ports utilisés
youcaport status
```

```bash
# Vérifier un port précis
youcaport check 3000
```

```text
✗ Port 3000 occupé

Application : Next.js
PID          : 447315
État         : En cours d'exécution
```

```bash
# Libérer un port (avec confirmation obligatoire)
youcaport free 3000
```

```text
Port 3000

Application : Next.js
PID         : 447315

Voulez-vous arrêter cette application ?
[y/N]
```

```bash
# Aide et version
youcaport --help
youcaport --version
```

---

## Fonctionnalités avancées (V2 → V5)

### Suggérer des ports libres — Auto Port (V4)

Quand un port est occupé, `check` propose automatiquement des ports libres proches.
Une commande dédiée existe aussi :

```bash
youcaport suggest 3000 --count 5
```

```text
Ports libres suggérés : 3001, 3002, 3003, 3004, 3005
```

### Profils de projets — Port Profiles (V2)

Associez des ports à des projets nommés (stockage : `~/.config/youcaport/profiles.json`) :

```bash
youcaport profile add frontend 3000     # associe le port 3000 au projet "frontend"
youcaport profile list                   # liste les profils
youcaport profile show frontend          # état des ports d'un profil
youcaport profile remove frontend        # supprime le profil
```

### Ports d'un projet — Project Management (V3)

Détecte automatiquement les ports utilisés par les processus tournant depuis un dossier :

```bash
youcaport project /chemin/vers/mon/projet
# ou, depuis le dossier du projet :
youcaport project .
```

### Dashboard web local (V5)

Interface web locale (stdlib, aucune dépendance supplémentaire), auto-rechargée :

```bash
youcaport dashboard            # http://127.0.0.1:8421
youcaport dashboard --port 9000
```

Une API JSON est exposée sur `/api/ports`, pratique pour l'intégration.

### Exécutable autonome (PyInstaller)

```bash
make binary       # ou : ./scripts/dev.sh binary
./dist/youcaport --version
```

---

## Windows

YoucaPort fonctionne aussi sur Windows (psutil est multiplateforme, couvert par un job CI
`windows-latest`). Particularités :

- **Installation** : `pip install youcaport` (ou `pipx install youcaport`) ; l'exécutable
  PyInstaller se construit sur une machine Windows (`make binary` n'est pas requis,
  utiliser `scripts/build_binary.sh` dans un terminal Windows).
- **Arrêt d'un processus** : Windows n'offre pas de signal d'arrêt gracieux (SIGTERM) ;
  `terminate()` réalise un arrêt immédiat. YoucaPort vous en avertit explicitement avant
  la confirmation.
- **Profil de projets** : le fichier `profiles.json` est stocké dans `%LOCALAPPDATA%\youcaport\`
  (au lieu de `~/.config/youcaport/` sur Linux/macOS).

---

## Fonctionnement de l'arrêt d'un processus

YoucaPort ne tue jamais un processus brutalement par défaut :

1. Confirmation obligatoire (`y/N`) avec rappel de l'application, du PID et du port.
2. Envoi d'un **SIGTERM** (arrêt propre).
3. Période de grâce de **3 secondes**.
4. **SIGKILL** uniquement si le processus n'a pas répondu au SIGTERM.

Aucune stack trace n'est jamais affichée à l'utilisateur : chaque erreur (port invalide,
permission insuffisante, processus déjà arrêté...) est traduite en message clair en français,
avec un code de sortie approprié (`0` ou `1`).

---

## Architecture

```text
youcaport/
│
├── pyproject.toml        # source de vérité pour la version et les dépendances
├── poetry.lock
├── README.md
├── LICENSE
│
├── src/youcaport/
│   ├── __init__.py        # version via importlib.metadata (repli tomllib en dev)
│   ├── cli.py              # commandes Typer (status/check/free/suggest/project/dashboard/profile)
│   ├── menu.py             # menu interactif + sous-menu — pas de logique métier
│   ├── dashboard.py        # interface web locale (V5) — stdlib uniquement
│   │
│   ├── core/                # aucune dépendance d'affichage, 100% testable
│   │   ├── port_manager.py    # orchestration, dataclass InfoPort
│   │   ├── process_manager.py # seul module appelant psutil (abstraction Linux/macOS/Windows)
│   │   ├── validator.py       # validateurs + exceptions (PortInvalideError, ...)
│   │   ├── profiles.py        # profils de projets (V2) — JSON via XDG
│   │   ├── suggester.py       # ports libres à proximité (V4)
│   │   └── project_manager.py # ports utilisés par un projet (V3)
│   │
│   └── utils/
│       └── terminal.py     # seul module Rich (tableaux, confirmations, gestion des erreurs)
│
└── tests/
    ├── test_ports.py        # sockets réellement en écoute
    ├── test_processes.py    # sous-processus enfants réellement lancés/tués
    ├── test_validator.py
    ├── test_profiles.py     # profils de projets
    ├── test_suggester.py    # auto-port
    └── test_project.py      # détection par projet
```

**Principes respectés :**
- `core/` ne dépend d'aucune bibliothèque d'affichage (testable en isolation).
- `cli.py` / `menu.py` orchestrent uniquement ; tout l'affichage passe par `utils/terminal.py`.
- Exceptions personnalisées plutôt que codes de retour épars.
- Tests réalistes (sockets et sous-processus réels), mocks réservés aux cas impossibles à
  reproduire en local (ex. permission refusée).

---

## Développement

```bash
# Installer les dépendances (dev incluses)
make install
# ou : poetry install

# Lancer les tests
make test
# ou : poetry run pytest

# Lint + format
make lint
make format
# ou : poetry run ruff check . / poetry run ruff format .

# Build (wheel + sdist)
make build
# ou : poetry build

# Exécutable autonome (PyInstaller)
make binary
# ou : ./scripts/dev.sh binary
```

Toutes ces commandes sont aussi disponibles via `scripts/dev.sh`.

### CI/CD

`.github/workflows/ci.yml` exécute à chaque push/PR :
- lint (`ruff check`, `ruff format --check`)
- tests (`pytest`) sur Python 3.11 et 3.12

À chaque tag `v*`, le workflow publie automatiquement sur PyPI via **trusted publishing**
(OIDC — aucun token PyPI à stocker en secret).

```bash
git tag v0.1.0
git push origin v0.1.0
```

---

## Limites de cette version

Comme prévu par le cahier des charges, YoucaPort reste volontairement simple :

- **Windows / macOS** : l'abstraction existe dans `process_manager.py` (psutil), mais ces
  plateformes ne sont pas testées — seule Linux est validée.
- **Docker management** : hors périmètre MVP.
- **Dashboard lourd / comptes / base de données** : hors périmètre MVP ; le dashboard V5
  est volontairement minimal (page locale, stdlib).

---

## Licence

Voir [LICENSE](./LICENSE).