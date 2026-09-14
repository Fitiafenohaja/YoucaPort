"""Menu interactif principal de YoucaPort."""

from __future__ import annotations

from youcaport import __version__
from youcaport.core import port_manager, privileges, process_manager, suggester
from youcaport.core.port_manager import LIBRE, InfoPort
from youcaport.utils import terminal


def lancer_menu() -> None:
    """Lance la boucle du menu interactif jusqu'à ce que l'utilisateur quitte."""
    while True:
        terminal.afficher_menu(__version__)
        choix = terminal.demander_choix(
            ["1", "2", "3", "4"],
            ["Ports utilisés", "Vérifier un port", "Libérer un port", "Quitter"],
        )

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
    """Affiche la liste des ports puis propose un sous-menu de gestion."""
    try:
        infos = port_manager.lister_ports_utilises()
        if any(info.processus is None for info in infos) and terminal.demander_confirmation(
            "Des ports protégés (root/docker) sont présents. Les identifier avec sudo ?"
        ):
            infos = _enrichir_sudo(infos)
    except Exception as exc:
        terminal.afficher_exception(exc)
        return

    if not infos:
        terminal.afficher_information("Aucun port en écoute actuellement.")
        return

    terminal.afficher_ports(infos)
    _sous_menu_ports()


def _sous_menu_ports() -> None:
    """Sous-menu proposé après l'affichage des ports (vérifier / libérer / retour)."""
    while True:
        choix = terminal.demander_sous_menu()
        if choix is None or choix == "3":
            return
        if choix == "1":
            _verifier_un_port()
        else:
            _liberer_un_port()


def _enrichir_sudo(infos: list[InfoPort]) -> list[InfoPort]:
    """Tente d'enrichir les ports non identifiés avec les données privilégiées."""
    try:
        mapping = privileges.connexions_privilegiees(interactif=True)
    except privileges.SudoNonDisponibleError as exc:
        terminal.afficher_exception(exc)
        return infos
    return port_manager.enrichir_privilegies(infos, mapping)


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
        terminal.afficher_suggestions(suggester.suggerer_ports_libres(info.port))


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

    if info.processus is None:
        terminal.afficher_erreur(
            f"Le port {info.port} est occupé mais aucun processus n'y est associé."
        )
        terminal.afficher_information(
            f"Astuce : `youcaport free --sudo {info.port}` peut arrêter les processus protégés."
        )
        return

    terminal.afficher_resume_processus(info)
    if not process_manager.ARRET_DOUX:
        terminal.afficher_information(
            "Remarque : sur Windows, l'arrêt du processus est immédiat "
            "(aucune fermeture gracieuse n'est possible)."
        )
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
