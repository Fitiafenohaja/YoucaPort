"""Tests unitaires du validateur de ports."""

from __future__ import annotations

import pytest

from youcaport.core.validator import PortInvalideError, valider_port


@pytest.mark.parametrize(
    "valeur",
    [1, 80, 3000, 5432, 65535, "80", "65535", " 3000 "],
)
def test_port_valide(valeur: int | str) -> None:
    assert isinstance(valider_port(valeur), int)


@pytest.mark.parametrize("valeur", [0, -1, 65536, 100_000])
def test_port_hors_limites(valeur: int) -> None:
    with pytest.raises(PortInvalideError):
        valider_port(valeur)


@pytest.mark.parametrize("valeur", ["abc", "", "80,5", "12a", None, 12.5])
def test_port_non_entier(valeur: int | str | None) -> None:
    with pytest.raises(PortInvalideError):
        valider_port(valeur)  # type: ignore[arg-type]


def test_erreur_port_contient_message() -> None:
    with pytest.raises(PortInvalideError, match="Numéro de port invalide"):
        valider_port("n'importe quoi")
