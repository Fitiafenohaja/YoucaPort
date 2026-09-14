"""Configuration partagée des tests (sonde d'environnement macOS)."""

from __future__ import annotations

import sys

import psutil
import pytest


@pytest.fixture()
def processus_identifiables():
    """Saute le test si le sandbox macOS masque l'identification des processus.

    Sur les exécuteurs macOS restreints (CI), psutil ne peut lister aucune
    connexion réseau même pour l'utilisateur courant : la résolution PID est
    alors impossible et seul le comportement dégradé est testable.
    """
    if sys.platform != "darwin":
        return
    try:
        psutil.net_connections(kind="tcp")
    except (psutil.AccessDenied, OSError):
        pytest.skip("Le sandbox macOS ne permet pas d'identifier les processus.")
