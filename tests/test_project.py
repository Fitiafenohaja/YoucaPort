"""Tests unitaires de la détection de ports par projet (project_manager)."""

from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from youcaport.core import port_manager, process_manager
from youcaport.core.project_manager import ProjetIntrouvableError, lister_ports_projet


def _port_libre() -> int:
    ecoute = socket.socket()
    ecoute.bind(("127.0.0.1", 0))
    port = ecoute.getsockname()[1]
    ecoute.close()
    return port


def _attendre_port_occupe(port: int, delai_max: float = 5.0) -> None:
    debut = time.monotonic()
    while time.monotonic() - debut < delai_max:
        if process_manager.port_en_ecoute(port):
            return
        time.sleep(0.05)
    raise AssertionError(f"Le port {port} n'est jamais devenu occupé.")


def test_dossier_introuvable() -> None:
    with pytest.raises(ProjetIntrouvableError):
        lister_ports_projet("/chemin/qui/n/existe/pas/12345")


@pytest.mark.usefixtures("processus_identifiables")
def test_detecte_port_du_projet(tmp_path: Path) -> None:
    port = _port_libre()
    code = (
        "import socket, time; "
        f"s = socket.socket(); s.bind(('127.0.0.1', {port})); s.listen(); "
        "time.sleep(30)"
    )
    enfant = subprocess.Popen([sys.executable, "-c", code], cwd=str(tmp_path))
    try:
        _attendre_port_occupe(port)

        ports = [info.port for info in lister_ports_projet(str(tmp_path))]
        assert port in ports
        assert all(isinstance(info.port, int) for info in port_manager.lister_ports_utilises())
    finally:
        if enfant.poll() is None:
            enfant.kill()
