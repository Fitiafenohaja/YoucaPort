#!/usr/bin/env bash
#
# Construit un exécutable autonome de YoucaPort (PyInstaller).
# Prérequis : poetry install (groupe de dépendances "packaging").

set -euo pipefail

cd "$(dirname "$0")/.."

echo "Construction du binaire autonome (PyInstaller)..."

poetry run pyinstaller --onefile --clean --name youcaport \
  --collect-all rich \
  --collect-all typer \
  src/youcaport/cli.py

echo
echo "Binaire généré : dist/youcaport"