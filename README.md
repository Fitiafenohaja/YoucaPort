# PortKeeper

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

## Pourquoi PortKeeper ?

Quand vous lancez un projet (Next.js, FastAPI, PostgreSQL, Vite...), il arrive que le port
soit déjà occupé :

```text
EADDRINUSE: address already in use
```

Plutôt que de jongler avec `lsof -i :3000`, `kill -9 <PID>` et autres commandes système,
PortKeeper centralise tout dans une interface simple :

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
pipx install portkeeper
```

### Avec pip

```bash
pip install portkeeper
```

### Depuis les sources

```bash
git clone https://github.com/<votre-compte>/portkeeper.git
cd portkeeper
poetry install
poetry build
pipx install dist/portkeeper-*.whl
```

**Prérequis** : Python 3.11+. Plateforme prioritaire : **Linux** (Windows/macOS non testés
pour cette version, mais l'architecture est déjà abstraite pour une extension future).

---

## Utilisation

### Menu interactif

```bash
portkeeper
```

Lance le menu principal : ports utilisés / vérifier un port / libérer un port / quitter.

### Commandes directes

```bash
# Lister tous les ports utilisés
portkeeper status
```

```bash
# Vérifier un port précis
portkeeper check 3000
```

```text
✗ Port 3000 occupé

Application : Next.js
PID          : 447315
État         : En cours d'exécution
```

```bash
# Libérer un port (avec confirmation obligatoire)
portkeeper free 3000
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
portkeeper --help
portkeeper --version
```

---

## Fonctionnement de l'arrêt d'un processus

PortKeeper ne tue jamais un processus brutalement par défaut :

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
portkeeper/
│
├── pyproject.toml        # source de vérité pour la version et les dépendances
├── poetry.lock
├── README.md
├── LICENSE
│
├── src/portkeeper/
│   ├── __init__.py        # version via importlib.metadata (repli tomllib en dev)
│   ├── cli.py              # commandes Typer (status/check/free) — pas de logique métier
│   ├── menu.py             # menu interactif — pas de logique métier
│   │
│   ├── core/                # aucune dépendance d'affichage, 100% testable
│   │   ├── port_manager.py    # orchestration, dataclass InfoPort
│   │   ├── process_manager.py # seul module appelant psutil (abstraction Linux/macOS/Windows)
│   │   └── validator.py       # validateurs + exceptions (PortInvalideError, ...)
│   │
│   └── utils/
│       └── terminal.py     # seul module Rich (tableaux, confirmations, gestion des erreurs)
│
└── tests/
    ├── test_ports.py        # sockets réellement en écoute
    ├── test_processes.py    # sous-processus enfants réellement lancés/tués
    └── test_validator.py
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

## Limites de cette version (MVP)

Conformément au cahier des charges, ne sont **pas** inclus pour l'instant :

- Windows / macOS (abstraction prévue dans `process_manager.py`, mais non testée)
- Dashboard web
- Docker management
- Port Profiles (association ports ↔ projets)
- Détection automatique de port disponible (« Auto Port »)

Ces éléments sont prévus dans les versions futures (voir le cahier des charges).

---

## Licence

Voir [LICENSE](./LICENSE).