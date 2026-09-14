"""Tests du mode privilégié (sudo) : parsing de `ss` et enrichissement."""

from youcaport.core import port_manager, privileges
from youcaport.core.port_manager import OCCUPE, InfoPort


def test_parser_connexions_ss_ipv4() -> None:
    texte = 'LISTEN 0 4096 0.0.0.0:9101 0.0.0.0:* users:(("docker-proxy",pid=2711,fd=8))'
    assert privileges._parser_connexions_ss(texte) == {
        9101: {"pid": 2711, "nom": "docker-proxy", "etat": "LISTEN"}
    }


def test_parser_connexions_ss_ipv6_et_multiple() -> None:
    texte = (
        'LISTEN 0 4096 [::]:6380 [::]:* users:(("docker-proxy",pid=2466,fd=8))\n'
        'LISTEN 0 4096 127.0.0.53:53 0.0.0.0:* users:(("systemd-resolve",pid=829,fd=15))'
    )
    resultats = privileges._parser_connexions_ss(texte)
    assert resultats[6380]["nom"] == "docker-proxy"
    assert resultats[6380]["pid"] == 2466
    assert resultats[53]["nom"] == "systemd-resolve"


def test_parser_ignore_lignes_sans_processus_ou_hors_listen() -> None:
    texte = (
        "LISTEN 0 4096 0.0.0.0:8080 0.0.0.0:*\n"
        'ESTAB 0 0 127.0.0.1:9000 127.0.0.2:80 users:(("chrome",pid=9999,fd=3))'
    )
    assert privileges._parser_connexions_ss(texte) == {}


def test_parser_ignore_valeur_port_invalide() -> None:
    texte = 'LISTEN 0 4096 0.0.0.0:revelation 0.0.0.0:* users:(("x",pid=1,fd=3))'
    assert privileges._parser_connexions_ss(texte) == {}


def test_enrichir_privilegies_augmente_port_inconnu() -> None:
    infos = [InfoPort(port=8080, processus=None, etat=OCCUPE)]
    mapping = {8080: {"pid": 2969, "nom": "docker-proxy", "etat": "LISTEN"}}

    enrichis = port_manager.enrichir_privilegies(infos, mapping)

    assert enrichis[0].processus is not None
    assert enrichis[0].processus.pid == 2969
    assert enrichis[0].processus.nom == "docker-proxy"
    assert enrichis[0].etat == OCCUPE


def test_enrichir_privilegies_conserve_inconnus_sans_mapping() -> None:
    infos = [InfoPort(port=53, processus=None, etat=OCCUPE)]
    enrichis = port_manager.enrichir_privilegies(infos, {})
    assert enrichis[0].processus is None


def test_enrichir_privilegies_conserve_processus_connus() -> None:
    infos = [(InfoPort(port=3000, processus=None, etat=OCCUPE))]
    enrichis = port_manager.enrichir_privilegies(
        infos, {3000: {"pid": 1, "nom": "x", "etat": "LISTEN"}}
    )
    assert enrichis[0].processus is not None
