"""Tests de la gestion Docker (V6) : parsing de `docker ps` et recherche."""

from youcaport.core.docker_manager import _parser_ports, _parser_ps


def test_parser_ports_extrait_ports_publics() -> None:
    champ = "0.0.0.0:5432->5432/tcp, 127.0.0.1:5433->5433/tcp"
    assert _parser_ports(champ) == frozenset({5432, 5433})


def test_parser_ports_ipv6_et_sans_mapping() -> None:
    champ = "[::]:8080->80/tcp, 6379/tcp"
    assert _parser_ports(champ) == frozenset({8080})


def test_parser_ports_invalide_ignoree() -> None:
    champ = "0.0.0.0:99999->80/tcp, 0.0.0.0:abc->22/tcp"
    assert _parser_ports(champ) == frozenset()


def test_parser_ps_cinq_colonnes() -> None:
    texte = (
        "abcd1234\tweb\tnginx:latest\tUp 4 minutes\t0.0.0.0:8080->80/tcp\n"
        "ef5678\tdb\tpostgres:16\tUp 2 hours\t0.0.0.0:5432->5432/tcp"
    )
    conteneurs = _parser_ps(texte)
    assert len(conteneurs) == 2
    assert conteneurs[0].nom == "web"
    assert conteneurs[0].ports == frozenset({8080})
    assert conteneurs[1].image == "postgres:16"


def test_parser_ps_ignore_lignes_malformees() -> None:
    assert _parser_ps("ligne incomplete") == []


def test_conteneur_pour_port_retourne_le_bon_conteneur() -> None:
    conteneurs = _parser_ps("aa\tweb\tnginx\tUp\t0.0.0.0:8080->80/tcp")
    assert conteneurs[0].nom == "web"
    assert next((c for c in conteneurs if 8080 in c.ports), None) is not None
    assert next((c for c in conteneurs if 8081 in c.ports), None) is None
