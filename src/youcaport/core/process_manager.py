"""Abstraction des interactions avec le système (connexions et processus).

Tout appel a psutil passe obligatoirement par ce module.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass

import psutil

from youcaport.core.validator import YoucaPortError

TEMPS_ATTENTE_ARRET = 3.0
# Sur Windows, psutil.terminate() = TerminateProcess (arrêt immédiat) :
# aucune fermeture gracieuse type SIGTERM n'est possible.
ARRET_DOUX = sys.platform != "win32"

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

    Lève PermissionSystemeError si les connexions réseau sont inaccessibles,
    sauf sur macOS où un repli sur `netstat` évite de bloquer l'outil.
    """
    try:
        connexions = psutil.net_connections(kind="tcp")
    except psutil.AccessDenied as exc:
        if sys.platform == "darwin":
            return _lister_connexions_macos()
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


def _lister_connexions_macos() -> list[tuple[int, int]]:
    """Repli macOS sans privilèges : `lsof` (PID réel pour ses propres processus)."""
    try:
        resultat = subprocess.run(
            ["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise PermissionSystemeError(MESSAGE_PERMISSION) from exc

    if resultat.returncode != 0 and not resultat.stdout:
        raise PermissionSystemeError(MESSAGE_PERMISSION)

    return _lister_connexions_macos_from(resultat.stdout)


def _lister_connexions_macos_from(sortie: str) -> list[tuple[int, int]]:
    """Parse la sortie `lsof -nP -iTCP -sTCP:LISTEN` en couples (port, pid)."""
    resultats: set[tuple[int, int]] = set()
    for ligne in sortie.splitlines():
        champs = ligne.split()
        if len(champs) < 6 or champs[0] == "COMMAND":
            continue
        pid = int(champs[1]) if champs[1].isdigit() else -1
        adresse = next((champ for champ in reversed(champs) if ":" in champ), None)
        port = _port_lsof(adresse)
        if port is None:
            continue
        resultats.add((port, pid))

    return sorted(resultats, key=lambda element: element[0])


def _port_lsof(local: str | None) -> int | None:
    """Extrait le port des adresses lsof type `127.0.0.1:3000` ou `*:8080`."""
    if local is None or ":" not in local:
        return None
    suffixe = local.rsplit(":", 1)[1]
    if not suffixe.isdigit():
        return None
    port = int(suffixe)
    return port if 1 <= port <= 65535 else None


def port_en_ecoute(port: int) -> bool:
    """Indique si un port est en écoute, que le processus soit identifiable ou non."""
    return any(port_ecoute == port for port_ecoute, _ in lister_connexions_ecoute())


def construire_processus(pid: int) -> Processus | None:
    """Construit une description d'un processus, ou None s'il est inaccessible."""
    try:
        proc = psutil.Process(pid)
    except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
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
    except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
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

        proc.terminate()  # SIGTERM (POSIX) ; arrêt immédiat sur Windows.
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
    except ValueError as exc:
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
