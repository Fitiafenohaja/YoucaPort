"""Profils de projets : association de noms de projets à des ports (V2)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from portkeeper.core.validator import PortKeeperError, valider_port

_DOSSIER_CONFIG = "portkeeper"
_FICHIER_PROFILS = "profiles.json"


class ProfilInvalideError(PortKeeperError):
    """Nom de profil ou données de profil invalides."""


class ProfilInexistantError(PortKeeperError):
    """Le profil demandé n'existe pas."""


def chemin_fichier_profils() -> Path:
    """Chemin du fichier de profils (XDG_CONFIG_HOME, sinon ~/.config)."""
    racine = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return racine / _DOSSIER_CONFIG / _FICHIER_PROFILS


def lister_profils(fichier: Path | None = None) -> dict[str, list[int]]:
    """Renvoie les profils {nom: [ports]} triés par nom de projet."""
    chemin = fichier if fichier is not None else chemin_fichier_profils()
    return dict(sorted(_charger(chemin).items()))


def ajouter_profil(nom: str, port: int | str, fichier: Path | None = None) -> None:
    """Associe un port valide à un profil, en créant le profil si nécessaire."""
    numero = valider_port(port)
    if not nom.strip():
        raise ProfilInvalideError("Le nom du projet est requis.")

    chemin = fichier if fichier is not None else chemin_fichier_profils()
    donnees = _charger(chemin)
    ports = donnees.setdefault(nom, [])
    if numero not in ports:
        donnees[nom] = sorted([*ports, numero])
        _enregistrer(chemin, donnees)


def supprimer_profil(nom: str, fichier: Path | None = None) -> None:
    """Supprime un profil complet."""
    chemin = fichier if fichier is not None else chemin_fichier_profils()
    donnees = _charger(chemin)
    if nom not in donnees:
        raise ProfilInexistantError(f"Le profil '{nom}' n'existe pas.")
    del donnees[nom]
    _enregistrer(chemin, donnees)


def _charger(fichier: Path) -> dict[str, list[int]]:
    if not fichier.exists():
        return {}

    try:
        brut = json.loads(fichier.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProfilInvalideError(f"Fichier de profils illisible : {fichier}") from exc

    if not isinstance(brut, dict):
        raise ProfilInvalideError(f"Fichier de profils invalide : {fichier}")

    return {
        str(nom): sorted({int(valeur) for valeur in valeurs if str(valeur).isdigit()})
        for nom, valeurs in brut.items()
        if isinstance(nom, str) and isinstance(valeurs, list)
    }


def _enregistrer(fichier: Path, donnees: dict[str, list[int]]) -> None:
    fichier.parent.mkdir(parents=True, exist_ok=True)
    fichier.write_text(
        json.dumps(donnees, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
