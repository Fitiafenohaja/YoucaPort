"""Coordination de la gestion des ports et de leurs processus."""

from __future__ import annotations

from dataclasses import dataclass

from portkeeper.core import process_manager
from portkeeper.core.process_manager import Processus, ProcessusArretImpossibleError
from portkeeper.core.validator import PortKeeperError, valider_port

OCCUPE = "OCCUPE"
LIBRE = "LIBRE"


class PortNonOccupeError(PortKeeperError):
    """Le port demandé n'est utilisé par aucun processus."""


@dataclass(frozen=True)
class InfoPort:
    """État d'un port et, le cas échéant, le processus qui l'occupe."""

    port: int
    processus: Processus | None
    etat: str


def lister_ports_utilises() -> list[InfoPort]:
    """Liste les ports actuellement en écoute, triés par numéro.

    Lève PermissionSystemeError si les connexions réseau sont inaccessibles.
    """
    infos: dict[tuple[int, int], InfoPort] = {}
    for port, pid in process_manager.lister_connexions_ecoute():
        processus = process_manager.construire_processus(pid) if pid != -1 else None
        infos[(port, pid)] = InfoPort(port=port, processus=processus, etat=OCCUPE)

    return [infos[cle] for cle in sorted(infos)]


def verifier_port(port: int | str) -> InfoPort:
    """Retourne l'état courant d'un port et son processus éventuel."""
    numero = valider_port(port)
    processus = process_manager.rechercher_premier_processus(numero)

    if processus is None:
        return InfoPort(port=numero, processus=None, etat=LIBRE)

    return InfoPort(port=numero, processus=processus, etat=OCCUPE)


def liberer_port(port: int | str) -> InfoPort:
    """Arrête le processus occupant le port puis retourne le nouvel état.

    Lève PortNonOccupeError si le port est déjà libre,
    ProcessusIntrouvableError si le processus est déjà arrêté,
    PermissionSystemeError ou ProcessusArretImpossibleError selon l'échec.
    """
    numero = valider_port(port)
    processus = process_manager.rechercher_premier_processus(numero)

    if processus is None:
        raise PortNonOccupeError(f"Aucun processus trouvé sur le port {numero}.")

    process_manager.arreter_processus(processus.pid)

    apres = verifier_port(numero)
    if apres.etat != LIBRE:
        raise ProcessusArretImpossibleError(
            f"Le processus a été arrêté mais le port {numero} est toujours utilisé."
        )

    return apres
