#!/usr/bin/env bash
#
# Raccourcis de développement PortKeeper.
# Usage : ./scripts/dev.sh {install|lock|test|lint|format|build}

set -euo pipefail

cd "$(dirname "$0")/.."

COMMANDE="${1:-help}"

case "$COMMANDE" in
  install)
    poetry install
    ;;
  lock)
    poetry lock
    ;;
  test)
    poetry run pytest
    ;;
  lint)
    poetry run ruff check .
    ;;
  format)
    poetry run ruff format .
    ;;
  build)
    poetry build
    ;;
  *)
    echo "Usage : ./scripts/dev.sh {install|lock|test|lint|format|build}"
    exit 0
    ;;
esac