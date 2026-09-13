"""YoucaPort — gestionnaire de ports en ligne de commande."""

from __future__ import annotations

import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def _version() -> str:
    """Renvoie la version du paquet (source de vérité : pyproject.toml)."""
    try:
        return version("youcaport")
    except PackageNotFoundError:
        chemin_pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
        with chemin_pyproject.open("rb") as fichier:
            projet = tomllib.load(fichier)
        return str(projet["project"]["version"])


__version__ = _version()

__all__ = ["__version__"]
