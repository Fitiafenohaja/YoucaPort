"""Points d'entrée CLI de PortKeeper (Typer)."""

from __future__ import annotations

from typing import NoReturn

import typer

from portkeeper import __version__
from portkeeper.core import port_manager
from portkeeper.core.port_manager import LIBRE
from portkeeper.core.process_manager import ProcessusIntrouvableError
from portkeeper.menu import lancer_menu
from portkeeper.utils import terminal

app = typer.Typer(
    add_completion=False,
    help="PortKeeper : lister, vérifier et libérer les ports utilisés localement.",
    no_args_is_help=False,
)


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


def _sortie_erreur(exc: Exception) -> NoReturn:
    """Affiche une erreur compréhensible puis quitte proprement (code 1)."""
    terminal.afficher_exception(exc)
    code = 0 if isinstance(exc, ProcessusIntrouvableError) else 1
    raise typer.Exit(code=code)


if __name__ == "__main__":
    app()
