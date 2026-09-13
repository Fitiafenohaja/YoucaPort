"""Aides d'affichage Rich pour l'interface en ligne de commande."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from portkeeper.core.port_manager import InfoPort
from portkeeper.core.process_manager import ProcessusIntrouvableError
from portkeeper.core.validator import PortKeeperError

_console = Console()

_ETATS_FRANCAIS = {
    "running": "En cours d'exécution",
    "sleeping": "En sommeil",
    "idle": "Inactif",
    "stopped": "Arrêté",
    "zombie": "Zombie",
    "dead": "Mort",
    "disk-sleep": "En attente disque",
}


def afficher_ports(infos: list[InfoPort]) -> None:
    """Affiche un tableau des ports utilisés et de leurs processus."""
    tableau = Table(title="Ports utilisés", header_style="bold cyan")
    tableau.add_column("PORT", justify="right")
    tableau.add_column("APPLICATION")
    tableau.add_column("PID", justify="right")
    tableau.add_column("STATUS")

    for info in infos:
        nom = info.processus.nom if info.processus else "inconnu"
        pid = str(info.processus.pid) if info.processus else "-"
        etat = info.processus.etat.upper() if info.processus else "INCONNU"
        tableau.add_row(str(info.port), nom, pid, etat)

    _console.print(tableau)


def afficher_port_libre(info: InfoPort) -> None:
    """Affiche qu'un port est disponible."""
    _console.print(f"[bold green]✓ Port {info.port} disponible[/bold green]")
    _console.print("Aucune application n'utilise actuellement ce port.")


def afficher_port_occupe(info: InfoPort) -> None:
    """Affiche qu'un port est occupé avec les informations du processus."""
    _console.print(f"[bold red]✗ Port {info.port} occupé[/bold red]")
    _afficher_details_processus(info)


def afficher_resume_processus(info: InfoPort) -> None:
    """Affiche le processus occupant un port avant toute action."""
    _console.print(f"Port : {info.port}")
    _console.print()
    if info.processus is None:
        _console.print("Aucun processus actif.")
    else:
        _afficher_details_processus(info)


def afficher_suggestions(ports: list[int]) -> None:
    """Affiche une liste de ports libres suggérés (Auto Port)."""
    if not ports:
        return
    _console.print("[cyan]Ports libres suggérés :[/cyan] " + ", ".join(str(p) for p in ports))


def afficher_profils(profils: dict[str, list[int]]) -> None:
    """Affiche les profils de projets (association ports ↔ projets)."""
    tableau = Table(title="Profils de projets", header_style="bold cyan")
    tableau.add_column("PROJET")
    tableau.add_column("PORTS")

    for nom in profils:
        tableau.add_row(nom, ", ".join(str(port) for port in profils[nom]))

    _console.print(tableau)


def afficher_succes(message: str) -> None:
    """Affiche un message de succès préfixé par ✓."""
    _console.print(f"[green]✓ {message}[/green]")


def afficher_erreur(message: str) -> None:
    """Affiche un message d'erreur préfixé par ✗."""
    _console.print(f"[red]✗ {message}[/red]")


def afficher_information(message: str) -> None:
    """Affiche un message d'information neutre."""
    _console.print(f"[cyan]{message}[/cyan]")


def afficher_exception(exc: Exception) -> None:
    """Affiche une exception comme un message clair, sans trace de pile.

    Un processus déjà arrêté est une issue normale : affichée comme un succès.
    """
    if isinstance(exc, ProcessusIntrouvableError):
        afficher_succes(str(exc))
    elif isinstance(exc, PortKeeperError):
        afficher_erreur(str(exc))
    else:
        afficher_erreur(f"Erreur inattendue : {type(exc).__name__} — {exc}")


def afficher_menu() -> None:
    """Affiche le menu principal en surbrillance."""
    _console.print(Panel("[bold]PORTKEEPER[/bold]\nPort Manager CLI", border_style="cyan"))
    _console.print()
    _console.print("1. Ports utilisés")
    _console.print("2. Vérifier un port")
    _console.print("3. Libérer un port")
    _console.print("4. Quitter")
    _console.print()


def demander_choix(codes: list[str] | None = None) -> str | None:
    """Demande un choix de menu parmi les codes donnés ; None si interrompu."""
    choix = codes or ["1", "2", "3", "4"]
    try:
        return Prompt.ask("Choix", choices=choix, show_choices=False)
    except KeyboardInterrupt:
        return None


def demander_sous_menu() -> str | None:
    """Affiche le sous-menu de gestion des ports et renvoie le choix."""
    _console.print()
    _console.print("1. Vérifier un port")
    _console.print("2. Libérer un port")
    _console.print("3. Retour")
    return demander_choix(["1", "2", "3"])


def demander_port() -> str:
    """Demande un numéro de port à vérifier ou libérer."""
    return Prompt.ask("Entrez le numéro du port")


def demander_confirmation() -> bool:
    """Demande une confirmation oui/non avant un arrêt de processus."""
    _console.print()
    return Confirm.ask("Voulez-vous arrêter cette application ?", default=False)


def attendre_entree() -> None:
    """Attend que l'utilisateur appuie sur Entrée avant de continuer."""
    Prompt.ask("[dim]Appuyez sur Entrée pour continuer...[/dim]")


def _etat_francais(etat: str) -> str:
    """Traduit l'état psutil d'un processus en français lisible."""
    return _ETATS_FRANCAIS.get(etat, etat.capitalize())


def _afficher_details_processus(info: InfoPort) -> None:
    """Affiche les détails d'un processus (application, processus, PID, état)."""
    processus = info.processus
    if processus is None:
        return

    _console.print(f"Application : {processus.nom}")
    if processus.commande:
        _console.print(f"Processus   : {_tronquer(processus.commande)}")
    _console.print(f"PID          : {processus.pid}")
    _console.print(f"État         : {_etat_francais(processus.etat)}")


def _tronquer(texte: str, longueur: int = 80) -> str:
    """Raccourcit une chaîne sur une seule ligne avec des points de suspension."""
    texte = " ".join(texte.split())
    return texte if len(texte) <= longueur else texte[:longueur] + "…"
