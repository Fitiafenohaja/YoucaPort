"""Aides d'affichage Rich pour l'interface en ligne de commande."""

from __future__ import annotations

import sys

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from youcaport.core.docker_manager import Conteneur
from youcaport.core.port_manager import InfoPort
from youcaport.core.process_manager import ProcessusIntrouvableError
from youcaport.core.validator import YoucaPortError
from youcaport.utils import selection

_console = Console()

_ETATS_FRANCAIS = {
    "running": "En cours d'exécution",
    "sleeping": "En sommeil",
    "idle": "Inactif",
    "stopped": "Arrêté",
    "zombie": "Zombie",
    "dead": "Mort",
    "disk-sleep": "En attente disque",
    "LISTEN": "En écoute",
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
        etat = etat_francais(info.processus.etat) if info.processus else "-"
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


def afficher_conteneurs(conteneurs: list[Conteneur]) -> None:
    """Affiche un tableau des conteneurs Docker et de leurs ports hôtes."""
    tableau = Table(title="Conteneurs Docker", header_style="bold cyan")
    tableau.add_column("NOM")
    tableau.add_column("ID")
    tableau.add_column("IMAGE")
    tableau.add_column("STATUT")
    tableau.add_column("PORTS HÔTE")

    for conteneur in conteneurs:
        ports = ", ".join(str(port) for port in sorted(conteneur.ports)) or "-"
        tableau.add_row(
            conteneur.nom,
            conteneur.identifiant,
            conteneur.image,
            conteneur.statut,
            ports,
        )

    _console.print(tableau)


def afficher_conteneur(conteneur: Conteneur, port: int) -> None:
    """Affiche les détails d'un conteneur publiant un port hôte."""
    _console.print(f"[bold cyan]Port {port} → conteneur Docker[/bold cyan]")
    _console.print(f"Nom    : {conteneur.nom}")
    _console.print(f"ID     : {conteneur.identifiant}")
    _console.print(f"Image  : {conteneur.image}")
    _console.print(f"Statut : {conteneur.statut}")


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
    elif isinstance(exc, YoucaPortError):
        afficher_erreur(str(exc))
    else:
        afficher_erreur(f"Erreur inattendue : {type(exc).__name__} — {exc}")


def afficher_resume_ports(infos: list[InfoPort]) -> None:
    """Affiche un résumé synthétique après le tableau des ports."""
    identifiés = sum(1 for info in infos if info.processus is not None)
    inconnus = len(infos) - identifiés
    message = f"{len(infos)} port(s) en écoute — {identifiés} processus identifiés"
    if inconnus:
        message += f", {inconnus} non identifiés (root/docker)"
    _console.print(f"[dim]{message}[/dim]")


def afficher_menu(version: str = "") -> None:
    """Affiche l'encadré du menu principal et son astuce."""
    sous_titre = "Gestionnaire de ports"
    if version:
        sous_titre += f" — v{version}"
    _console.print(Panel(f"[bold]YOUCAPORT[/bold]\n{sous_titre}", border_style="cyan"))
    _console.print()
    _console.print(
        "[dim]Astuce : sous Linux, `free 3000 --sudo` libère aussi les ports "
        "protégés (root/docker).[/dim]"
    )
    _console.print()


def demander_choix(
    codes: list[str] | None = None,
    libelles: list[str] | None = None,
) -> str | None:
    """Demande un choix de menu, interchangeable au clavier (flèches/numéro) et à la souris."""
    codes = codes or ["1", "2", "3", "4"]
    libelles = libelles or [
        "Ports utilisés",
        "Vérifier un port",
        "Libérer un port",
        "Quitter",
    ]
    options = list(zip(codes, libelles, strict=True))

    if sys.stdin.isatty() and sys.stdout.isatty():
        return selection.menu_interactif(options)
    for code, libelle in options:
        _console.print(f"{code}. {libelle}")
    try:
        return Prompt.ask("Choix", choices=codes, show_choices=False)
    except KeyboardInterrupt:
        return None


def demander_sous_menu() -> str | None:
    """Affiche le sous-menu de gestion des ports et renvoie le choix."""
    _console.print()
    return demander_choix(["1", "2", "3"], ["Vérifier un port", "Libérer un port", "Retour"])


def demander_port() -> str:
    """Demande un numéro de port à vérifier ou libérer."""
    return Prompt.ask("Entrez le numéro du port")


def demander_confirmation(question: str = "Voulez-vous arrêter cette application ?") -> bool:
    """Demande une confirmation oui/non avant une action sensible."""
    _console.print()
    return Confirm.ask(question, default=False)


def attendre_entree() -> None:
    """Attend que l'utilisateur appuie sur Entrée avant de continuer."""
    Prompt.ask("[dim]Appuyez sur Entrée pour continuer...[/dim]")


def etat_francais(etat: str) -> str:
    """Traduit l'état psutil d'un processus en français lisible."""
    return _ETATS_FRANCAIS.get(etat, etat.capitalize())


def _afficher_details_processus(info: InfoPort) -> None:
    """Affiche les détails d'un processus (application, processus, PID, état)."""
    processus = info.processus
    if processus is None:
        _console.print("Application : inconnu (processus non identifiable)")
        return

    _console.print(f"Application : {processus.nom}")
    if processus.commande:
        _console.print(f"Processus   : {_tronquer(processus.commande)}")
    _console.print(f"PID          : {processus.pid}")
    _console.print(f"État         : {etat_francais(processus.etat)}")


def _tronquer(texte: str, longueur: int = 80) -> str:
    """Raccourcit une chaîne sur une seule ligne avec des points de suspension."""
    texte = " ".join(texte.split())
    return texte if len(texte) <= longueur else texte[:longueur] + "…"
