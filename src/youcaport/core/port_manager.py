"""Coordination de la gestion des ports et de leurs processus."""

from __future__ import annotations

from dataclasses import dataclass

from youcaport.core import privileges, process_manager
from youcaport.core.process_manager import Processus, ProcessusArretImpossibleError
from youcaport.core.validator import YoucaPortError, valider_port

OCCUPE = "OCCUPE"
LIBRE = "LIBRE"


class PortNonOccupeError(YoucaPortError):
    """Le port demandé n'est utilisé par aucun processus."""


class PortSansProcessusError(YoucaPortError):
    """Le port est occupé mais aucun processus n'a pu être identifié."""


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

    if processus is not None:
        return InfoPort(port=numero, processus=processus, etat=OCCUPE)

    if process_manager.port_en_ecoute(numero):
        return InfoPort(port=numero, processus=None, etat=OCCUPE)

    return InfoPort(port=numero, processus=None, etat=LIBRE)


def liberer_port(port: int | str) -> InfoPort:
    """Arrête le processus occupant le port puis retourne le nouvel état.

    Lève PortNonOccupeError si le port est déjà libre,
    ProcessusIntrouvableError si le processus est déjà arrêté,
    PermissionSystemeError ou ProcessusArretImpossibleError selon l'échec.
    """
    numero = valider_port(port)
    processus = process_manager.rechercher_premier_processus(numero)

    if processus is None:
        if process_manager.port_en_ecoute(numero):
            raise PortSansProcessusError(
                f"Le port {numero} est occupé mais aucun processus n'y est associé."
            )
        raise PortNonOccupeError(f"Aucun processus trouvé sur le port {numero}.")

    process_manager.arreter_processus(processus.pid)

    apres = verifier_port(numero)
    if apres.etat != LIBRE:
        raise ProcessusArretImpossibleError(
            f"Le processus a été arrêté mais le port {numero} est toujours utilisé."
        )

    return apres


def enrichir_privilegies(infos: list[InfoPort], mapping: dict[int, dict]) -> list[InfoPort]:
    """Remplace les ports sans processus par les données privilégiées (sudo)."""
    retour: list[InfoPort] = []
    for info in infos:
        donnees = mapping.get(info.port) if info.processus is None else None
        if donnees is None:
            retour.append(info)
            continue

        retour.append(
            InfoPort(
                port=info.port,
                processus=Processus(
                    pid=donnees["pid"],
                    nom=donnees["nom"],
                    executable="",
                    commande=donnees["nom"],
                    etat=donnees["etat"],
                ),
                etat=info.etat,
            )
        )
    return retour


def liberer_port_privilegie(port: int | str, mapping: dict[int, dict]) -> InfoPort:
    """Libère via sudo un port protégé dont le processus vient du mapping privilégié."""
    numero = valider_port(port)
    donnees = mapping.get(numero)
    if donnees is None:
        raise PortSansProcessusError(
            f"Le port {numero} est occupé mais aucun processus n'y est associé."
        )

    privileges.arreter_privilegie(donnees["pid"])

    apres = verifier_port(numero)
    if apres.etat != LIBRE:
        raise ProcessusArretImpossibleError(
            f"Le processus a été arrêté mais le port {numero} est toujours utilisé."
        )

    return apres
