"""Tests unitaires des profils de projets (profiles)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from youcaport.core import profiles
from youcaport.core.profiles import ProfilInexistantError, ProfilInvalideError
from youcaport.core.validator import PortInvalideError


def test_chemin_profils_windows(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", "C:\\Users\\Test\\AppData\\Local")

    chemin = str(profiles.chemin_fichier_profils())

    for composant in ["AppData", "Local", "youcaport", "profiles.json"]:
        assert composant in chemin


def test_chemin_profils_linux_nix() -> None:
    chemin = profiles.chemin_fichier_profils()

    assert "youcaport" in chemin.parts
    assert chemin.name == "profiles.json"


def test_ajouter_et_lister(tmp_path: Path) -> None:
    fichier = tmp_path / "profiles.json"
    profiles.ajouter_profil("frontend", 3000, fichier=fichier)
    profiles.ajouter_profil("backend", 8000, fichier=fichier)

    assert profiles.lister_profils(fichier=fichier) == {
        "backend": [8000],
        "frontend": [3000],
    }


def test_plusieurs_ports_tries(tmp_path: Path) -> None:
    fichier = tmp_path / "profiles.json"
    profiles.ajouter_profil("api", 8000, fichier=fichier)
    profiles.ajouter_profil("api", 8001, fichier=fichier)
    profiles.ajouter_profil("api", 8000, fichier=fichier)  # doublon ignoré

    assert profiles.lister_profils(fichier=fichier)["api"] == [8000, 8001]


def test_supprimer_profil(tmp_path: Path) -> None:
    fichier = tmp_path / "profiles.json"
    profiles.ajouter_profil("frontend", 3000, fichier=fichier)
    profiles.supprimer_profil("frontend", fichier=fichier)

    assert profiles.lister_profils(fichier=fichier) == {}


def test_supprimer_profil_inexistant(tmp_path: Path) -> None:
    with pytest.raises(ProfilInexistantError):
        profiles.supprimer_profil("inconnu", fichier=tmp_path / "profiles.json")


def test_port_invalide_rejete(tmp_path: Path) -> None:
    with pytest.raises(PortInvalideError):
        profiles.ajouter_profil("frontend", 70000, fichier=tmp_path / "profiles.json")


def test_nom_vide_rejete(tmp_path: Path) -> None:
    with pytest.raises(ProfilInvalideError):
        profiles.ajouter_profil("  ", 3000, fichier=tmp_path / "profiles.json")


def test_fichier_corrompu(tmp_path: Path) -> None:
    fichier = tmp_path / "profiles.json"
    fichier.write_text("{pas du json", encoding="utf-8")

    with pytest.raises(ProfilInvalideError):
        profiles.lister_profils(fichier=fichier)
