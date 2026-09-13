"""Détection automatique des ports utilisés par un projet (V3)."""

from __future__ import annotations

import os

from youcaport.core import port_manager, process_manager
from youcaport.core.port_manager import InfoPort
from youcaport.core.process_manager import Processus
from youcaport.core.validator import YoucaPortError


class ProjetIntrouvableError(YoucaPortError):
    """Le chemin fourni ne correspond à aucun dossier existant."""


def lister_ports_projet(chemin: str) -> list[InfoPort]:
    """Liste les ports en écoute dont au moins un processus appartient au projet."""
    repertoire = os.path.realpath(os.path.expanduser(chemin))
    if not os.path.isdir(repertoire):
        raise ProjetIntrouvableError(f"Dossier introuvable : {chemin}")

    return [
        info
        for info in port_manager.lister_ports_utilises()
        if info.processus is not None and _processus_appartient(info.processus, repertoire)
    ]


def _processus_appartient(processus: Processus, repertoire: str) -> bool:
    cwd = process_manager.cwd_processus(processus.pid)
    if cwd and _dans(cwd, repertoire):
        return True
    if processus.executable and _dans(processus.executable, repertoire):
        return True
    return any(jeton.startswith(repertoire) for jeton in processus.commande.split())


def _dans(chemin: str, repertoire: str) -> bool:
    chemin = os.path.realpath(chemin)
    return chemin == repertoire or chemin.startswith(repertoire + os.sep)
