"""Abstraction des interactions avec le système (connexions et processus).

Tout appel a psutil passe obligatoirement par ce module.
"""

from __future__ import annotations

from dataclasses import dataclass

import psutil

from youcaport.core.validator import YoucaPortError

TEMPS_ATTENTE_ARRET = 3.0

MESSAGE_PERMISSION = (
    "Permission insuffisante. YoucaPort ne peut pas accéder aux informations de ce processus."
)


class PermissionSystemeError(YoucaPortError):
    """Le système a refusé l'accès aux informations ou à l'arrêt d'un processus."""


class ProcessusIntrouvableError(YoucaPortError):
    """Le processus n'existe plus (déjà arrêté)."""


class ProcessusArretImpossibleError(YoucaPortError):
    """Le processus n'a pas pu être arrêté malgré les tentatives."""


@dataclass(frozen=True)
class Processus:
    """Description lisible d'un processus système."""

    pid: int
    nom: str
    executable: str
    commande: str
    etat: str


def lister_connexions_ecoute() -> list[tuple[int, int]]:
    """Renvoie la liste des couples (port, pid) actuellement en écoute.

    Lève PermissionSystemeError si les connexions réseau sont inaccessibles.
    """
    try:
        connexions = psutil.net_connections(kind="tcp")
    except psutil.AccessDenied as exc:
        raise PermissionSystemeError(MESSAGE_PERMISSION) from exc

    resultats: set[tuple[int, int]] = set()
    for connexion in connexions:
        if connexion.status != psutil.CONN_LISTEN or not connexion.laddr:
            continue
        port = int(connexion.laddr.port)
        pid = int(connexion.pid) if connexion.pid else -1
        if 1 <= port <= 65535:
            resultats.add((port, pid))

    return sorted(resultats, key=lambda element: element[0])


def port_en_ecoute(port: int) -> bool:
    """Indique si un port est en écoute, que le processus soit identifiable ou non."""
    return any(port_ecoute == port for port_ecoute, _ in lister_connexions_ecoute())


def construire_processus(pid: int) -> Processus | None:
    """Construit une description d'un processus, ou None s'il n'existe plus."""
    try:
        proc = psutil.Process(pid)
    except (psutil.NoSuchProcess, ValueError):
        return None

    nom = _essayer(proc.name, "inconnu")
    executable = _essayer(proc.exe, "")
    commande = _essayer(lambda: " ".join(proc.cmdline()), None)
    if not commande:
        commande = executable
    etat = _essayer(proc.status, "inconnu")

    return Processus(pid=pid, nom=nom, executable=executable, commande=commande, etat=etat)


def rechercher_premier_processus(port: int) -> Processus | None:
    """Retourne le premier processus en écoute sur un port, sinon None."""
    for port_ecoute, pid in lister_connexions_ecoute():
        if port_ecoute == port:
            processus = construire_processus(pid)
            if processus is not None:
                return processus
    return None


def cwd_processus(pid: int) -> str | None:
    """Répertoire de travail courant d'un processus, ou None sinon."""
    try:
        proc = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return None

    return _essayer(proc.cwd, None)


def arreter_processus(pid: int, duree_attente: float = TEMPS_ATTENTE_ARRET) -> None:
    """Arrête proprement un processus : SIGTERM d'abord, SIGKILL en dernier recours.

    Lève ProcessusIntrouvableError si le processus n'existe plus,
    PermissionSystemeError si le signal est refusé,
    ProcessusArretImpossibleError si le processus survit malgré SIGKILL.
    """
    try:
        proc = psutil.Process(pid)
        if not proc.is_running():
            raise ProcessusIntrouvableError(
                f"Le processus {pid} n'est plus actif, le port est disponible."
            )

        proc.terminate()  # SIGTERM : arrêt propre, jamais de SIGKILL en premier.
        proc.wait(timeout=duree_attente)

    except psutil.TimeoutExpired:
        try:
            proc.kill()  # Dernier recours apres la periode de grace.
            proc.wait(timeout=duree_attente)
        except psutil.TimeoutExpired as deriv:
            raise ProcessusArretImpossibleError(
                f"Le processus {pid} n'a pas pu être arrêté."
            ) from deriv
        except psutil.AccessDenied as deriv:
            raise PermissionSystemeError(MESSAGE_PERMISSION) from deriv
    except psutil.NoSuchProcess as exc:
        raise ProcessusIntrouvableError(
            f"Le processus {pid} n'est plus actif, le port est disponible."
        ) from exc
    except psutil.AccessDenied as exc:
        raise PermissionSystemeError(MESSAGE_PERMISSION) from exc


def _essayer(action, valeur_defaut) -> str | None:
    """Exécute une action psutil et renvoie une valeur par défaut en cas d'échec."""
    try:
        valeur = action()
    except (
        psutil.AccessDenied,
        psutil.NoSuchProcess,
        psutil.ZombieProcess,
        PermissionError,
        ProcessLookupError,
    ):
        return valeur_defaut

    texte = str(valeur or "").strip()
    return texte if valeur_defaut is None or texte else valeur_defaut
