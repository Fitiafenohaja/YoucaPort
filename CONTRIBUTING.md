# Contribuer à YoucaPort

Merci de vouloir contribuer ! Ce guide décrit le workflow à suivre pour que tout le monde
travaille sereinement sur `main`.

## Règles d'or

1. **Jamais de poussée directe sur `main`** : la branche est protégée. Tout se fait par
   **pull request** (testée et relue).
2. **Une PR = un changement ciblé** : pas de PR « fourre-tout » — une seule idée, un seul
   correctif, une seule fonctionnalité.
3. **Tout le code passe par les checks CI** : `quality` (ruff + pytest), `tests-windows` et
   `tests-macos` doivent être verts avant fusion.
4. **Les vues restent en français** (interface, messages, erreurs), le code en anglais
   (identifiants).
5. **Les secrets n'existent pas dans le dépôt** : token, mot de passe, `.pypirc` ne doivent
   jamais être commités. Voir `.gitignore`.

## Environnement de développement

Prérequis : [Poetry ≥ 2.0](https://python-poetry.org), Python 3.11+.

```bash
git clone https://github.com/Fitiafenohaja/YoucaPort.git
cd YoucaPort
poetry install
```

Commandes utiles (définies dans le `Makefile` et `scripts/dev.sh`) :

```bash
make test      # poetry run pytest      — régression
make lint      # poetry run ruff check .
make format    # poetry run ruff format .
make build     # poetry build
```

**Conventions de style** : Ruff, 100 colonnes, guillemets doubles, formatage
`ruff format`. Le lint et le format sont vérifiés en CI — lancez `make lint` et
`make format` avant de pousser.

## Workflow type

1. **Forkez** le dépôt (ou créez une branche si vous avez le rôle Write).
2. **Créez une branche** aux noms clairs : `fix/<quoi>`, `feat/<quoi>`, `docs/<quoi>`.
   ```bash
   git checkout -b fix/lecture-clavier
   ```
3. **Développez** en restant à jour avec `main` :
   ```bash
   git fetch origin
   git rebase origin/main
   ```
4. **Testez et vérifiez** :
   ```bash
   make test && make lint
   ```
5. **Commitez** proprement (histoire lisible, messages en français, style « verbe + objet ») :
   ```bash
   git commit -m "fix : lecture clavier fiable (os.read au lieu de sys.stdin.buffer)"
   ```
6. **Poussez et ouvrez une PR** vers `main`, avec `CONTRIBUTING.md` et le template de PR
   en tête. Un mainteneur relit et fusionne après approbation.

## Sécurité du dépôt

Pour éviter les « gaffes » :

- **`main` est protégé** : revue obligatoire, checks CI requis, force-push et suppression
  de la branche interdits.
- **Les tags `v*` sont protégés** : impossible de les déplacer ou de les supprimer.
- **Ne poussez jamais** : artefacts (`dist/`, `build/`), caches, fichiers personnels ou
  secrets — ils sont dans `.gitignore`. En cas de doute :
  ```bash
  git status --short   # vérifiez ce qui sera envoyé
  ```

## Bug ou question ?

Ouvrez une [issue](https://github.com/Fitiafenohaja/YoucaPort/issues) avec le résultat de
`youcaport --version`, votre OS, et les étapes pour reproduire.