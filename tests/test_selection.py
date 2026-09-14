"""Tests unitaires du décodage de touches et de souris (utils/selection)."""

from __future__ import annotations

from youcaport.utils.selection import decoder_sequence


def test_decode_fleches() -> None:
    assert decoder_sequence(b"\x1b[A") == ("haut", None)
    assert decoder_sequence(b"\x1b[B") == ("bas", None)


def test_decode_validation_et_annulation() -> None:
    assert decoder_sequence(b"\r") == ("entree", None)
    assert decoder_sequence(b"\n") == ("entree", None)
    assert decoder_sequence(b"q") == ("annuler", None)
    assert decoder_sequence(b"\x1b") == ("annuler", None)


def test_decode_numero() -> None:
    assert decoder_sequence(b"3") == ("numero", "3")


def test_decode_sequence_incomplete() -> None:
    assert decoder_sequence(b"\x1b[A") is not None
    assert decoder_sequence(b"\x1b") is not None
    assert decoder_sequence(b"\x1b[") is None
    assert decoder_sequence(b"\x1b[<0;12;3") is None


def test_decode_click_souris_sgr() -> None:
    assert decoder_sequence(b"\x1b[<0;15;12M") == ("souris", (15, 12))
    assert decoder_sequence(b"\x1b[<1;10;3M") == ("souris", (10, 3))


def test_decode_relachement_souris_ignore() -> None:
    assert decoder_sequence(b"\x1b[<0;15;12m") == ("inconnu", None)


def test_decode_click_souris_legacy_x10() -> None:
    boutons, colonne, ligne = 0, 10, 4
    sequence = b"\x1b[M" + bytes([boutons + 32, colonne + 32, ligne + 32])
    assert decoder_sequence(sequence) == ("souris", (10, 4))


def test_decode_inconnu() -> None:
    assert decoder_sequence(b"z") == ("inconnu", None)
    assert decoder_sequence(b"\x1bOM") == ("inconnu", None)


_OPTIONS = [("1", "Ports utilisés"), ("2", "Vérifier un port"), ("4", "Quitter")]


def _piloter(
    monkeypatch,
    octets_entree: list[int],
) -> str | None:
    import io
    from contextlib import nullcontext

    from youcaport.utils import selection

    sortie = io.StringIO()
    monkeypatch.setattr(selection.os, "name", "posix")
    monkeypatch.setattr(selection.sys, "stdout", sortie)
    monkeypatch.setattr(selection, "_position_curseur", lambda: (3, 1))
    monkeypatch.setattr(selection, "_mode_saisie", nullcontext)
    courant = iter(octets_entree)

    def _octet(_temporisation: float | None = None) -> int | None:
        return next(courant, None)

    monkeypatch.setattr(selection, "_lire_octet", _octet)
    return selection.menu_interactif(_OPTIONS)


def test_menu_entree_valide_premier_choix(monkeypatch) -> None:
    assert _piloter(monkeypatch, [ord("\r")]) == "1"


def test_menu_fleche_bas_puis_entree(monkeypatch) -> None:
    sequence = [0x1B, ord("["), ord("B"), ord("\r")]
    assert _piloter(monkeypatch, sequence) == "2"


def test_menu_fleche_haut_enroule(monkeypatch) -> None:
    sequence = [0x1B, ord("["), ord("A"), ord("\r")]
    assert _piloter(monkeypatch, sequence) == "4"


def test_menu_numero_rapide(monkeypatch) -> None:
    assert _piloter(monkeypatch, [ord("3")]) == "4"


def test_menu_click_souris(monkeypatch) -> None:
    sequence = [
        0x1B,
        ord("["),
        ord("<"),
        ord("0"),
        ord(";"),
        ord("5"),
        ord(";"),
        ord("3"),
        ord("M"),
    ]
    assert _piloter(monkeypatch, sequence) == "1"


def test_menu_annulation_echap(monkeypatch) -> None:
    assert _piloter(monkeypatch, [0x1B]) is None


def test_menu_annulation_touche_q(monkeypatch) -> None:
    assert _piloter(monkeypatch, [ord("q")]) is None
