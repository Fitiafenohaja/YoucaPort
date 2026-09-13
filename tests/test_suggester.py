"""Tests unitaires de la suggestion de ports libres (suggester)."""

from __future__ import annotations

import socket

import pytest

from youcaport.core import process_manager, suggester
from youcaport.core.validator import PortInvalideError


def test_suggerer_ports_libres() -> None:
    suggestions = suggester.suggerer_ports_libres(3000, nombre=5)

    assert len(suggestions) == 5
    assert suggestions == sorted(suggestions)
    occupe = {port for port, _ in process_manager.lister_connexions_ecoute()}
    assert not set(suggestions) & occupe


def test_suggerer_apres_port_occupe() -> None:
    ecoute = socket.socket()
    ecoute.bind(("127.0.0.1", 0))
    ecoute.listen()
    port = ecoute.getsockname()[1]
    try:
        suggestions = suggester.suggerer_ports_libres(port, nombre=2)
        assert suggestions
        assert all(p > port for p in suggestions)
    finally:
        ecoute.close()


def test_port_invalide_rejete() -> None:
    with pytest.raises(PortInvalideError):
        suggester.suggerer_ports_libres("abc")


def test_nombre_minim_force_a_un() -> None:
    assert len(suggester.suggerer_ports_libres(3000, nombre=0)) == 1
