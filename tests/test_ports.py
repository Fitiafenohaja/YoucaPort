"""Tests unitaires du coordinateur de ports (port_manager)."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time

import pytest

from youcaport.core import port_manager, process_manager
from youcaport.core.port_manager import (
    LIBRE,
    OCCUPE,
    InfoPort,
    PortNonOccupeError,
    PortSansProcessusError,
)
from youcaport.core.process_manager import ProcessusIntrouvableError
from youcaport.core.validator import PortInvalideError


def _port_libre() -> int:
    """Renvoie un port libre en réservant puis relâchant un socket."""
    ecoute = socket.socket()
    ecoute.bind(("127.0.0.1", 0))
    port = ecoute.getsockname()[1]
    ecoute.close()
    return port


@pytest.fixture()
def socket_ecoute() -> socket.socket:
    """Socket en écoute sur un port libre, fermé en fin de test."""
    ecoute = socket.socket()
    ecoute.bind(("127.0.0.1", 0))
    ecoute.listen()
    yield ecoute
    ecoute.close()


def test_verifier_port_invalide() -> None:
    for valeur in [0, 65536, "abc", -3]:
        with pytest.raises(PortInvalideError):
            port_manager.verifier_port(valeur)


def test_verifier_port_libre() -> None:
    port = _port_libre()
    resultat = port_manager.verifier_port(port)

    assert isinstance(resultat, InfoPort)
    assert resultat.etat == LIBRE
    assert resultat.processus is None


def test_verifier_port_occupe(socket_ecoute: socket.socket) -> None:
    port = socket_ecoute.getsockname()[1]
    resultat = port_manager.verifier_port(port)

    assert resultat.etat == OCCUPE
    assert resultat.processus is not None
    assert resultat.processus.pid == os.getpid()


def test_lister_ports_utilises(socket_ecoute: socket.socket) -> None:
    port = socket_ecoute.getsockname()[1]
    ports = [info.port for info in port_manager.lister_ports_utilises()]

    assert port in ports
    assert all(info.etat == OCCUPE for info in port_manager.lister_ports_utilises())


def test_liberer_port_deja_libre() -> None:
    port = _port_libre()
    with pytest.raises(PortNonOccupeError, match="Aucun processus trouvé"):
        port_manager.liberer_port(port)


def test_liberer_port_occupe() -> None:
    port = _port_libre()
    code = (
        "import socket, time; "
        f"s = socket.socket(); s.bind(('127.0.0.1', {port})); s.listen(); "
        "time.sleep(30)"
    )
    enfant = subprocess.Popen([sys.executable, "-c", code])
    try:
        _attendre_port_occupe(port)
        avant = port_manager.verifier_port(port)
        assert avant.etat == OCCUPE

        apres = port_manager.liberer_port(port)

        assert apres.etat == LIBRE
        assert enfant.poll() is not None
    finally:
        if enfant.poll() is None:
            enfant.kill()


def test_liberer_port_processus_deja_arrete(socket_ecoute: socket.socket, monkeypatch) -> None:
    port = socket_ecoute.getsockname()[1]

    def arret_fantome(_pid: int) -> None:
        raise ProcessusIntrouvableError("Le processus 999 n'est plus actif.")

    monkeypatch.setattr(process_manager, "arreter_processus", arret_fantome)
    with pytest.raises(ProcessusIntrouvableError):
        port_manager.liberer_port(port)


def test_verifier_port_occupe_sans_processus(monkeypatch) -> None:
    port = _port_libre()
    monkeypatch.setattr(process_manager, "lister_connexions_ecoute", lambda: [(port, -1)])

    resultat = port_manager.verifier_port(port)

    assert resultat.etat == OCCUPE
    assert resultat.processus is None


def test_liberer_port_occupe_sans_processus(monkeypatch) -> None:
    port = _port_libre()
    monkeypatch.setattr(process_manager, "lister_connexions_ecoute", lambda: [(port, -1)])

    with pytest.raises(PortSansProcessusError, match="aucun processus"):
        port_manager.liberer_port(port)


def _attendre_port_occupe(port: int, delai_max: float = 5.0) -> None:
    """Attend que le port soit en écoute, sinon échoue le test."""
    debut = time.monotonic()
    while time.monotonic() - debut < delai_max:
        if process_manager.rechercher_premier_processus(port) is not None:
            return
        time.sleep(0.05)
    raise AssertionError(f"Le port {port} n'est jamais devenu occupé.")
