"""Tests unitaires du gestionnaire de processus (process_manager)."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time

import psutil
import pytest

from youcaport.core import process_manager
from youcaport.core.process_manager import (
    PermissionSystemeError,
    ProcessusIntrouvableError,
)

_PID_INEXISTANT = 9_999_999_99


def test_port_lsof_formats() -> None:
    assert process_manager._port_lsof("127.0.0.1:3000") == 3000
    assert process_manager._port_lsof("*:8080") == 8080
    assert process_manager._port_lsof("[::1]:7000") == 7000
    assert process_manager._port_lsof("no-port") is None
    assert process_manager._port_lsof("*:99999") is None
    assert process_manager._port_lsof(None) is None


def test_lister_connexions_macos_parse_lsof() -> None:
    sortie = (
        "COMMAND  PID USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME\n"
        "python3  777 tino   3u  IPv4 0xe  0t0    TCP 127.0.0.1:3000 (LISTEN)\n"
        "node     -  root   3u  IPv4 0xf  0t0    TCP *:8080 (LISTEN)\n"
    )
    connexions = process_manager._lister_connexions_macos_from(sortie)
    assert (3000, 777) in connexions
    assert (8080, -1) in connexions


def test_lister_connexions_macos_parse_netstat() -> None:
    sortie = (
        "Proto Recv-Q Send-Q  Local Address          Foreign Address        (state)\n"
        "tcp4       0      0  *.5540                 *.*                    LISTEN\n"
        "tcp46      0      0  127.0.0.1.631          *.*                    LISTEN\n"
        "tcp4       0      0  *.5540                 *.*                    ESTABLISHED\n"
    )
    connexions = process_manager._lister_connexions_macos_netstat(sortie)
    assert (5540, -1) in connexions
    assert (631, -1) in connexions


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


def test_construire_processus_courant() -> None:
    processus = process_manager.construire_processus(os.getpid())
    assert processus is not None
    assert processus.pid == os.getpid()
    assert processus.nom


def test_construire_processus_pid_inexistant() -> None:
    assert process_manager.construire_processus(_PID_INEXISTANT) is None


def test_construire_processus_pid_invalide() -> None:
    assert process_manager.construire_processus(-1) is None


@pytest.mark.usefixtures("processus_identifiables")
def test_lister_connexions_contient_notre_socket(socket_ecoute: socket.socket) -> None:
    port = socket_ecoute.getsockname()[1]
    connexions = process_manager.lister_connexions_ecoute()
    assert (port, os.getpid()) in connexions


@pytest.mark.usefixtures("processus_identifiables")
def test_rechercher_processus_par_port(socket_ecoute: socket.socket) -> None:
    port = socket_ecoute.getsockname()[1]
    processus = process_manager.rechercher_premier_processus(port)
    assert processus is not None
    assert processus.pid == os.getpid()


def test_rechercher_processus_port_libre() -> None:
    port = _port_libre()
    assert process_manager.rechercher_premier_processus(port) is None


@pytest.mark.usefixtures("processus_identifiables")
def test_arreter_processus_grace() -> None:
    port = _port_libre()
    code = (
        "import socket, time; "
        f"s = socket.socket(); s.bind(('127.0.0.1', {port})); s.listen(); "
        "time.sleep(30)"
    )
    enfant = subprocess.Popen([sys.executable, "-c", code])
    try:
        _attendre_port_occupe(port)

        process_manager.arreter_processus(enfant.pid)

        assert enfant.wait(timeout=process_manager.TEMPS_ATTENTE_ARRET) is not None
    finally:
        if enfant.poll() is None:
            enfant.kill()


def test_arreter_processus_deja_arrete() -> None:
    with pytest.raises(ProcessusIntrouvableError):
        process_manager.arreter_processus(_PID_INEXISTANT)


def test_arreter_processus_permission_refusee(monkeypatch) -> None:
    class ProcessusFactice:
        def __init__(self, pid: int) -> None:
            self.pid = pid

        def is_running(self) -> bool:
            return True

        def terminate(self) -> None:
            raise psutil.AccessDenied(self.pid)

    monkeypatch.setattr(process_manager.psutil, "Process", ProcessusFactice, raising=False)

    with pytest.raises(PermissionSystemeError):
        process_manager.arreter_processus(4242)


def _attendre_port_occupe(port: int, delai_max: float = 5.0) -> None:
    """Attend que le port soit en écoute, sinon échoue le test."""
    debut = time.monotonic()
    while time.monotonic() - debut < delai_max:
        if process_manager.port_en_ecoute(port):
            return
        time.sleep(0.05)
    raise AssertionError(f"Le port {port} n'est jamais devenu occupé.")
