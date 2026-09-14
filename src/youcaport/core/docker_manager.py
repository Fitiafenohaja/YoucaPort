"""Gestion des conteneurs Docker qui publient des ports (V6).

Interagit avec le CLI `docker ps` / `docker stop` ; aucun accès direct à
l'API Docker ni à la socket.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

from youcaport.core.validator import YoucaPortError

_FORMAT_PS = "{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"


class DockerNonDisponibleError(YoucaPortError):
    """docker est introuvable ou n'a pas pu s'exécuter."""


class ConteneurIntrouvableError(YoucaPortError):
    """Aucun conteneur ne publie le port demandé."""


@dataclass(frozen=True)
class Conteneur:
    """Description d'un conteneur Docker et de ses ports publics publiés."""

    identifiant: str
    nom: str
    image: str
    statut: str
    ports: frozenset[int]


def docker_disponible() -> bool:
    """Indique si le CLI docker est exécutable sur le système."""
    return shutil.which("docker") is not None


def lister_conteneurs() -> list[Conteneur]:
    """Liste les conteneurs en cours d'exécution et leurs ports publics.

    Lève DockerNonDisponibleError si docker est absent ou a échoué.
    """
    if not docker_disponible():
        raise DockerNonDisponibleError("Docker n'est pas installé ou absent du PATH.")

    try:
        resultat = subprocess.run(
            ["docker", "ps", "--format", _FORMAT_PS],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except subprocess.TimeoutExpired as exc:
        raise DockerNonDisponibleError("Le délai de réponse de Docker est dépassé.") from exc

    if resultat.returncode != 0:
        message = (resultat.stderr or "Docker n'a pas pu être interrogé.").strip()
        raise DockerNonDisponibleError(message)

    return _parser_ps(resultat.stdout)


def conteneur_pour_port(port: int) -> Conteneur | None:
    """Retourne le conteneur publiant un port hôte donné, sinon None."""
    for conteneur in lister_conteneurs():
        if port in conteneur.ports:
            return conteneur
    return None


def arreter_conteneur(conteneur: Conteneur) -> None:
    """Arrête proprement un conteneur (`docker stop`).

    Lève DockerNonDisponibleError en cas d'échec.
    """
    if not docker_disponible():
        raise DockerNonDisponibleError("Docker n'est pas installé ou absent du PATH.")

    resultat = subprocess.run(
        ["docker", "stop", conteneur.nom],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if resultat.returncode != 0:
        message = (resultat.stderr or "docker stop a échoué.").strip()
        raise DockerNonDisponibleError(message)


def _parser_ps(texte: str) -> list[Conteneur]:
    """Convertit la sortie `docker ps` (format tabulé) en Conteneur."""
    conteneurs: list[Conteneur] = []
    for ligne in texte.splitlines():
        champs = ligne.split("\t")
        if len(champs) != 5:
            continue
        identifiant, nom, image, statut, ports = champs
        conteneurs.append(
            Conteneur(
                identifiant=identifiant,
                nom=nom,
                image=image,
                statut=statut,
                ports=_parser_ports(ports),
            )
        )
    return conteneurs


def _parser_ports(texte: str) -> frozenset[int]:
    """Extrait les ports publics publiés d'un champ « Ports » de `docker ps`."""
    ports: set[int] = set()
    for liaison in texte.split(","):
        liaison = liaison.strip()
        if "->" not in liaison:
            continue
        publique = liaison.split("->", 1)[0].rsplit(":", 1)[-1]
        if publique.isdigit() and 1 <= int(publique) <= 65535:
            ports.add(int(publique))
    return frozenset(ports)
