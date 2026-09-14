"""Points d'entrée CLI de YoucaPort (Typer)."""

from __future__ import annotations

from typing import NoReturn

import typer

from youcaport import __version__
from youcaport import dashboard as module_dashboard
from youcaport.core import (
    port_manager,
    privileges,
    process_manager,
    profiles,
    project_manager,
    suggester,
)
from youcaport.core.port_manager import LIBRE, OCCUPE, InfoPort, PortSansProcessusError
from youcaport.core.process_manager import Processus, ProcessusIntrouvableError
from youcaport.core.profiles import ProfilInexistantError
from youcaport.core.validator import valider_port
from youcaport.menu import lancer_menu
from youcaport.utils import terminal

app = typer.Typer(
    add_completion=False,
    help="YoucaPort : lister, vérifier et libérer les ports utilisés localement.",
    no_args_is_help=False,
)

app_profile = typer.Typer(help="Gère les profils de projets (association ports ↔ projets).")
app.add_typer(app_profile, name="profile")


def _callback_version(valeur: bool) -> None:
    """Affiche la version puis quitte lorsque --version est fourni."""
    if valeur:
        typer.echo(f"youcaport {__version__}")
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
    """YoucaPort : gestion simple des ports réseau locaux."""
    if ctx.invoked_subcommand is None:
        try:
            lancer_menu()
        except KeyboardInterrupt:
            terminal.afficher_information("À bientôt !")


@app.command()
def status(
    sudo: bool = typer.Option(
        False,
        "--sudo",
        help="Identifie aussi les ports protégés (root/docker). Mot de passe demandé si besoin.",
    ),
) -> None:
    """Affiche les ports actuellement utilisés."""
    try:
        infos = port_manager.lister_ports_utilises()
        if sudo:
            infos = _enrichir_sudo(infos)
    except Exception as exc:
        _sortie_erreur(exc)

    if not infos:
        terminal.afficher_information("Aucun port en écoute actuellement.")
        return

    terminal.afficher_ports(infos)


@app.command()
def check(
    port: str,
    sudo: bool = typer.Option(
        False,
        "--sudo",
        help="Identifie le processus même s'il est protégé (root/docker).",
    ),
) -> None:
    """Vérifie si un port est libre ou occupé."""
    try:
        info = port_manager.verifier_port(port)
        if sudo:
            infos = _enrichir_sudo([info])
            info = infos[0]
    except Exception as exc:
        _sortie_erreur(exc)

    if info.etat == LIBRE:
        terminal.afficher_port_libre(info)
    else:
        terminal.afficher_port_occupe(info)
        terminal.afficher_suggestions(suggester.suggerer_ports_libres(info.port))


@app.command()
def free(
    port: str,
    sudo: bool = typer.Option(
        False,
        "--sudo",
        help="Autorise l'arrêt des processus protégés (root/docker) via sudo.",
    ),
) -> None:
    """Libère un port en arrêtant le processus qui l'occupe."""
    try:
        info = port_manager.verifier_port(port)
    except Exception as exc:
        _sortie_erreur(exc)

    if info.etat == LIBRE:
        terminal.afficher_erreur(f"Aucun processus trouvé sur le port {info.port}.")
        raise typer.Exit(code=1)

    mapping: dict[int, dict] = {}
    if info.processus is None:
        if not sudo:
            _sortie_erreur(
                PortSansProcessusError(
                    f"Le port {info.port} est occupé mais aucun processus n'y est associé."
                )
            )
        try:
            mapping = privileges.connexions_privilegiees(interactif=True)
        except privileges.SudoNonDisponibleError as exc:
            _sortie_erreur(exc)
        donnees = mapping.get(info.port)
        if donnees is None:
            _sortie_erreur(
                PortSansProcessusError(
                    f"Le port {info.port} est occupé mais aucun processus n'y est associé."
                )
            )
        info = InfoPort(
            port=info.port,
            processus=Processus(
                pid=donnees["pid"],
                nom=donnees["nom"],
                executable="",
                commande=donnees["nom"],
                etat=donnees["etat"],
            ),
            etat=OCCUPE,
        )

    terminal.afficher_resume_processus(info)
    if mapping:
        terminal.afficher_information(
            "Ce processus est protégé (root/docker) : il sera arrêté via sudo."
        )
    _prevenir_arret_immediat()
    if not terminal.demander_confirmation():
        terminal.afficher_information("Arrêt annulé, aucun processus arrêté.")
        return

    terminal.afficher_information("Arrêt du processus...")
    try:
        if mapping:
            port_manager.liberer_port_privilegie(info.port, mapping)
        else:
            port_manager.liberer_port(info.port)
    except Exception as exc:
        _sortie_erreur(exc)

    terminal.afficher_succes("Processus arrêté.")
    terminal.afficher_succes(f"Port {info.port} libéré.")


def _prevenir_arret_immediat() -> None:
    """Prévient que l'arrêt est immédiat sur Windows (pas de fermeture gracieuse)."""
    if not process_manager.ARRET_DOUX:
        terminal.afficher_information(
            "Remarque : sur Windows, l'arrêt du processus est immédiat "
            "(aucune fermeture gracieuse n'est possible)."
        )


def _enrichir_sudo(infos: list[InfoPort]) -> list[InfoPort]:
    """Tente d'enrichir les ports non identifiés avec les données privilégiées."""
    try:
        mapping = privileges.connexions_privilegiees(interactif=True)
    except privileges.SudoNonDisponibleError as exc:
        terminal.afficher_information(str(exc))
        return infos
    return port_manager.enrichir_privilegies(infos, mapping)


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
    no_browser: bool = typer.Option(
        False,
        "--no-browser",
        help="N'ouvre pas automatiquement le navigateur.",
    ),
    sudo: bool = typer.Option(
        False,
        "--sudo",
        help="Identifie les ports protégés (uniquement si sudo est déjà authentifié).",
    ),
) -> None:
    """Démarre une interface web locale pour visualiser les ports."""
    try:
        valider_port(port)
        module_dashboard.lancer_dashboard(port, ouvrir_navigateur=not no_browser, avec_sudo=sudo)
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
