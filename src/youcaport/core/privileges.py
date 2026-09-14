"""Accès privilégié (sudo) : identifier et arrêter les processus protégés.

Toute commande système privilégiée passe par ce module. Disponible sous
POSIX uniquement (Windows n'a ni `sudo` ni `ss`).
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import time

from youcaport.core.process_manager import (
    ARRET_DOUX,
    TEMPS_ATTENTE_ARRET,
    ProcessusArretImpossibleError,
)

_COMMANDE_SS = ["ss", "-ltnpnH"]

_MOTIF_PID = re.compile(r"pid=([0-9]+)")
_MOTIF_NOM = re.compile(r'"([^"]+)"')

_MESSAGE_PREAUTH = (
    "Informations privilégiées indisponibles : authentifiez d'abord une fois "
    "avec `sudo -v` puis relancez la commande."
)
_MESSAGE_REFUS = "Authentification privilégiée refusée ou non accordée."


class SudoNonDisponibleError(Exception):
    """sudo est indisponible ou l'authentification n'est pas possible."""


def sudo_disponible() -> bool:
    """Indique si sudo est exécutable sur ce système (POSIX uniquement)."""
    return sys.platform != "win32" and shutil.which("sudo") is not None


def connexions_privilegiees(interactif: bool = False) -> dict[int, dict]:
    """Ports en écoute protégés avec leur processus réel, via `sudo ss -ltnpnH`.

    Lève SudoNonDisponibleError si sudo est absent, si l'authentification
    n'est pas possible (mode non interactif) ou si l'utilisateur la refuse.
    """
    if not sudo_disponible():
        raise SudoNonDisponibleError("sudo est indisponible sur ce système.")

    identite = _identite_cachee()
    if not identite and (not interactif or not sys.stdin.isatty()):
        raise SudoNonDisponibleError(_MESSAGE_PREAUTH)

    commande = ["sudo", *(["-n"] if identite else []), *_COMMANDE_SS]
    try:
        resultat = subprocess.run(commande, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired as exc:
        raise SudoNonDisponibleError("Le délai de réponse de sudo est dépassé.") from exc

    if resultat.returncode != 0:
        raise SudoNonDisponibleError(_MESSAGE_REFUS)

    return _parser_connexions_ss(resultat.stdout)


def arreter_privilegie(pid: int, arret_doux: bool = ARRET_DOUX) -> None:
    """Arrête un processus protégé via sudo : SIGTERM puis SIGKILL en dernier recours.

    Lève SudoNonDisponibleError si l'authentification n'est pas en cache,
    ProcessusArretImpossibleError si le processus survit malgré SIGKILL.
    """
    if not sudo_disponible():
        raise SudoNonDisponibleError("sudo est indisponible sur ce système.")
    if not _identite_cachee():
        raise SudoNonDisponibleError(_MESSAGE_PREAUTH)

    signal = "TERM" if arret_doux else "KILL"
    if _envoyer_signal(pid, signal) and _attendre_disparition(pid, TEMPS_ATTENTE_ARRET):
        return

    if (
        arret_doux
        and _envoyer_signal(pid, "KILL")
        and _attendre_disparition(pid, TEMPS_ATTENTE_ARRET)
    ):
        return

    raise ProcessusArretImpossibleError(f"Le processus {pid} n'a pas pu être arrêté.")


def _identite_cachee() -> bool:
    """Indique si les identifiants sudo sont déjà validés (aucun prompt)."""
    return subprocess.run(["sudo", "-n", "-v"], capture_output=True).returncode == 0


def _envoyer_signal(pid: int, signal: str) -> bool:
    """Envoie un signal à un processus via sudo (`kill -<signal>`)."""
    resultat = subprocess.run(
        ["sudo", "-n", "kill", f"-{signal}", str(pid)],
        capture_output=True,
    )
    return resultat.returncode == 0


def _attendre_disparition(pid: int, duree: float = TEMPS_ATTENTE_ARRET) -> bool:
    """Attend qu'un processus disparaisse, dans la limite du délai donné."""
    echeance = time.monotonic() + duree
    while time.monotonic() < echeance:
        if not _processus_existe(pid):
            return True
        time.sleep(0.1)
    return False


def _processus_existe(pid: int) -> bool:
    """Indique si un processus existe encore (`kill -0` sous sudo)."""
    resultat = subprocess.run(["sudo", "-n", "kill", "-0", str(pid)], capture_output=True)
    return resultat.returncode == 0


def _parser_connexions_ss(texte: str) -> dict[int, dict]:
    """Convertit la sortie `ss -ltnpnH` en mapping {port: {pid, nom, etat}}."""
    resultats: dict[int, dict] = {}
    for ligne in texte.splitlines():
        colonnes = ligne.split()
        if len(colonnes) < 6 or colonnes[0] != "LISTEN":
            continue

        port = colonnes[3].rsplit(":", 1)[-1]
        if not port.isdigit():
            continue

        processus = " ".join(colonnes[5:])
        pid = _MOTIF_PID.search(processus)
        nom = _MOTIF_NOM.search(processus)
        if pid is None or nom is None:
            continue

        resultats[int(port)] = {
            "pid": int(pid.group(1)),
            "nom": nom.group(1),
            "etat": "LISTEN",
        }
    return resultats
