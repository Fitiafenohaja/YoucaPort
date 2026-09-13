"""Points d'entrée CLI de PortKeeper (Typer)."""

from __future__ import annotations

from typing import NoReturn

import typer

from portkeeper import __version__
from portkeeper import dashboard as module_dashboard
from portkeeper.core import port_manager, profiles, project_manager, suggester
from portkeeper.core.port_manager import LIBRE
from portkeeper.core.process_manager import ProcessusIntrouvableError
from portkeeper.core.profiles import ProfilInexistantError
from portkeeper.core.validator import valider_port
from portkeeper.menu import lancer_menu
from portkeeper.utils import terminal

app = typer.Typer(
    add_completion=False,
    help="PortKeeper : lister, vérifier et libérer les ports utilisés localement.",
    no_args_is_help=False,
)

app_profile = typer.Typer(help="Gère les profils de projets (association ports ↔ projets).")
app.add_typer(app_profile, name="profile")


def _callback_version(valeur: bool) -> None:
    """Affiche la version puis quitte lorsque --version est fourni."""
    if valeur:
        typer.echo(f"portkeeper {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def principal(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Affiche la version et quitte.",
        is_eager=True,
        callback=_callback_version,
    ),
) -> None:
    """PortKeeper : gestion simple des ports réseau locaux."""
    if ctx.invoked_subcommand is None:
        try:
            lancer_menu()
        except KeyboardInterrupt:
            terminal.afficher_information("À bientôt !")


@app.command()
def status() -> None:
    """Affiche les ports actuellement utilisés."""
    try:
        infos = port_manager.lister_ports_utilises()
    except Exception as exc:
        _sortie_erreur(exc)

    if not infos:
        terminal.afficher_information("Aucun port en écoute actuellement.")
        return

    terminal.afficher_ports(infos)


@app.command()
def check(port: str) -> None:
    """Vérifie si un port est libre ou occupé."""
    try:
        info = port_manager.verifier_port(port)
    except Exception as exc:
        _sortie_erreur(exc)

    if info.etat == LIBRE:
        terminal.afficher_port_libre(info)
    else:
        terminal.afficher_port_occupe(info)
        terminal.afficher_suggestions(suggester.suggerer_ports_libres(info.port))


@app.command()
def free(port: str) -> None:
    """Libère un port en arrêtant le processus qui l'occupe."""
    try:
        info = port_manager.verifier_port(port)
    except Exception as exc:
        _sortie_erreur(exc)

    if info.etat == LIBRE:
        terminal.afficher_erreur(f"Aucun processus trouvé sur le port {info.port}.")
        raise typer.Exit(code=1)

    terminal.afficher_resume_processus(info)
    if not terminal.demander_confirmation():
        terminal.afficher_information("Arrêt annulé, aucun processus arrêté.")
        return

    terminal.afficher_information("Arrêt du processus...")
    try:
        port_manager.liberer_port(info.port)
    except Exception as exc:
        _sortie_erreur(exc)

    terminal.afficher_succes("Processus arrêté.")
    terminal.afficher_succes(f"Port {info.port} libéré.")


@app.command()
def suggest(
    port: str,
    count: int = typer.Option(
        3,
        "--count",
        min=1,
        max=10,
        help="Nombre de ports libres à suggérer (1-10).",
    ),
) -> None:
    """Suggère des ports libres proches d'un port donné (Auto Port)."""
    try:
        candidats = suggester.suggerer_ports_libres(port, count)
    except Exception as exc:
        _sortie_erreur(exc)

    if not candidats:
        terminal.afficher_information("Aucun port libre trouvé après ce port.")
        return

    terminal.afficher_suggestions(candidats)


@app.command()
def project(
    chemin: str = typer.Argument(".", help="Dossier du projet à analyser."),
) -> None:
    """Affiche les ports utilisés par un projet."""
    try:
        infos = project_manager.lister_ports_projet(chemin)
    except Exception as exc:
        _sortie_erreur(exc)

    if not infos:
        terminal.afficher_information("Aucun port en écoute détecté pour ce projet.")
        return

    terminal.afficher_ports(infos)


@app.command()
def dashboard(
    port: int = typer.Option(
        8421,
        "--port",
        help="Port sur lequel écoute l'interface web locale.",
    ),
) -> None:
    """Démarre une interface web locale pour visualiser les ports."""
    try:
        valider_port(port)
        module_dashboard.lancer_dashboard(port)
    except Exception as exc:
        _sortie_erreur(exc)


@app_profile.command("list")
def profile_liste() -> None:
    """Liste les profils enregistrés."""
    try:
        profils = profiles.lister_profils()
    except Exception as exc:
        _sortie_erreur(exc)

    if not profils:
        terminal.afficher_information("Aucun profil enregistré.")
        return

    terminal.afficher_profils(profils)


@app_profile.command("add")
def profile_ajout(nom: str, port: str) -> None:
    """Associe un port à un profil de projet."""
    try:
        profiles.ajouter_profil(nom, port)
        profils = profiles.lister_profils()
    except Exception as exc:
        _sortie_erreur(exc)

    terminal.afficher_succes(f"Profil '{nom}' : ports {', '.join(map(str, profils[nom]))}.")


@app_profile.command("show")
def profile_affichage(nom: str) -> None:
    """Affiche l'état des ports d'un profil."""
    try:
        profils = profiles.lister_profils()
    except Exception as exc:
        _sortie_erreur(exc)

    if nom not in profils:
        _sortie_erreur(ProfilInexistantError(f"Le profil '{nom}' n'existe pas."))

    try:
        infos = [port_manager.verifier_port(numero) for numero in profils[nom]]
    except Exception as exc:
        _sortie_erreur(exc)

    terminal.afficher_ports(infos)


@app_profile.command("remove")
def profile_suppression(nom: str) -> None:
    """Supprime un profil complet."""
    try:
        profiles.supprimer_profil(nom)
    except Exception as exc:
        _sortie_erreur(exc)

    terminal.afficher_succes(f"Profil '{nom}' supprimé.")


def _sortie_erreur(exc: Exception) -> NoReturn:
    """Affiche une erreur compréhensible puis quitte proprement (code 1)."""
    terminal.afficher_exception(exc)
    code = 0 if isinstance(exc, ProcessusIntrouvableError) else 1
    raise typer.Exit(code=code)


if __name__ == "__main__":
    app()
