"""Menu interactif principal de PortKeeper."""

from __future__ import annotations

from portkeeper.core import port_manager
from portkeeper.core.port_manager import LIBRE
from portkeeper.utils import terminal


def lancer_menu() -> None:
    """Lance la boucle du menu interactif jusqu'à ce que l'utilisateur quitte."""
    while True:
        terminal.afficher_menu()
        choix = terminal.demander_choix()

        if choix is None or choix == "4":
            terminal.afficher_information("À bientôt !")
            return
        if choix == "1":
            _afficher_ports()
        elif choix == "2":
            _verifier_un_port()
        elif choix == "3":
            _liberer_un_port()

        _poursuivre()


def _afficher_ports() -> None:
    """Affiche la liste des ports actuellement utilisés."""
    try:
        infos = port_manager.lister_ports_utilises()
    except Exception as exc:
        terminal.afficher_exception(exc)
        return

    if not infos:
        terminal.afficher_information("Aucun port en écoute actuellement.")
        return

    terminal.afficher_ports(infos)


def _verifier_un_port() -> None:
    """Demande un port puis affiche s'il est libre ou occupé."""
    valeur = terminal.demander_port()
    try:
        info = port_manager.verifier_port(valeur)
    except Exception as exc:
        terminal.afficher_exception(exc)
        return

    if info.etat == LIBRE:
        terminal.afficher_port_libre(info)
    else:
        terminal.afficher_port_occupe(info)


def _liberer_un_port() -> None:
    """Demande un port puis libère son processus après confirmation."""
    valeur = terminal.demander_port()
    try:
        info = port_manager.verifier_port(valeur)
    except Exception as exc:
        terminal.afficher_exception(exc)
        return

    if info.etat == LIBRE:
        terminal.afficher_erreur(f"Aucun processus trouvé sur le port {info.port}.")
        return

    terminal.afficher_resume_processus(info)
    if not terminal.demander_confirmation():
        terminal.afficher_information("Arrêt annulé, aucun processus arrêté.")
        return

    terminal.afficher_information("Arrêt du processus...")
    try:
        port_manager.liberer_port(info.port)
    except Exception as exc:
        terminal.afficher_exception(exc)
        return

    terminal.afficher_succes("Processus arrêté.")
    terminal.afficher_succes(f"Port {info.port} libéré.")


def _poursuivre() -> None:
    """Attend une touche avant de réafficher le menu."""
    terminal.attendre_entree()
