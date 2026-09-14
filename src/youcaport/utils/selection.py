"""Sélection interactive par clavier et souris dans un terminal (stdlib).

Principe : un bloc d'options est rendu en langage ANSI ; l'utilisateur navigue
avec les flèches ↑/↓ (ou le numéro), valide avec Entrée, clique à la souris
(protocole X10/SGR, terminaux compatibles) ou annule avec q/Échap.
Sur terminal non interactif, un fallback simple (Prompt) reste disponible à
l'appelant — voir `utils/terminal.demander_choix`.

Aucune dépendance externe : lecture brute via `termios`/`select` (POSIX) ou
`msvcrt` (Windows), rendu en séquences d'échappement standard.
"""

from __future__ import annotations

import os
import re
import select
import sys
from collections.abc import Iterator
from contextlib import contextmanager

_ECHAP = "\x1b"
_reste = bytearray()


def _ecrire(texte: str) -> None:
    """Écrit sur la sortie standard et vide le tampon."""
    sys.stdout.write(texte)
    sys.stdout.flush()


@contextmanager
def _mode_saisie() -> Iterator[None]:
    """Mode saisie brute : pas d'écho, pas de canonique ; signaux conservés."""
    if os.name == "nt":
        yield
        return
    import termios
    import tty

    descripteur = sys.stdin.fileno()
    ancien = termios.tcgetattr(descripteur)
    try:
        tty.setcbreak(descripteur)
        yield
    finally:
        termios.tcsetattr(descripteur, termios.TCSADRAIN, ancien)


def _lire_octet(temporisation: float | None = None) -> int | None:
    """Lit un octet de l'entrée standard, None si la temporisation expire.

    Les octets mis en attente par ``_position_curseur`` (frappes tapées pendant
    la sonde DSR) sont rejoués en priorité afin de ne perdre aucune saisie.
    """
    if _reste:
        return _reste.pop(0)
    if os.name == "nt":
        import msvcrt

        if msvcrt.kbhit():
            return ord(msvcrt.getwch())
        return None
    if select.select([sys.stdin], [], [], temporisation or 0)[0]:
        octet = sys.stdin.buffer.read(1)
        return octet[0] if octet else None
    return None


_SOURIS_SGR = re.compile(rb"\x1b\[<([0-9]+);([0-9]+);([0-9]+)([Mm])$")
_FLECHES = {
    b"\x1b[A": ("haut", None),
    b"\x1b[B": ("bas", None),
    b"\x1b[C": ("droite", None),
    b"\x1b[D": ("gauche", None),
}


def decoder_sequence(octets: bytes) -> tuple[str, tuple[int, int] | str | int | None] | None:
    """Décode une séquence de touches ; None si incomplète, sinon (action, valeur)."""
    if octets == b"\x1b":
        return ("annuler", None)
    if octets in _FLECHES:
        return _FLECHES[octets]
    if octets in (b"\r", b"\n"):
        return ("entree", None)
    if octets in (b"q", b"Q"):
        return ("annuler", None)
    if len(octets) == 1 and bytes.isdigit(octets):
        return ("numero", octets.decode())

    correspondance = _SOURIS_SGR.match(octets)
    if correspondance:
        boutons, colonne, ligne, fin = correspondance.groups()
        if fin == b"m":
            return ("inconnu", None)
        if int(boutons) % 64 in (0, 1, 2):
            return ("souris", (int(colonne), int(ligne)))
        return ("inconnu", None)

    # Séquences incomplètes des structures connues (il manque des octets).
    if octets.startswith(b"\x1b[<") and correspondance is None:
        return None
    if octets.startswith(b"\x1b[M") and len(octets) < 6:
        return None
    if octets == b"\x1b[":
        return None

    if len(octets) == 6 and octets[:3] == b"\x1b[M":
        boutons = octets[3] - 32
        colonne = octets[4] - 32
        ligne = octets[5] - 32
        if boutons % 64 in (0, 1, 2):
            return ("souris", (colonne, ligne))
        return ("inconnu", None)

    return ("inconnu", None)


def _lire_action(
    temporisation: float = 0.1,
) -> tuple[str, tuple[int, int] | str | int | None] | None:
    """Attend une action complète : flèche, numéro, clic souris, annulation."""
    octets = bytearray()
    attente = temporisation
    while True:
        octet = _lire_octet(attente)
        if octet is None:
            if octets:
                return decoder_sequence(bytes(octets))
            return None
        octets.append(octet)
        if len(octets) == 1 and octets[0] == 0x1B:
            attente = 0.03
            continue
        if len(octets) > 16:
            return ("inconnu", None)
        decode = decoder_sequence(bytes(octets))
        if decode is not None:
            return decode


def _lire_action_windows(
    temporisation: float = 0.1,
) -> tuple[str, tuple[int, int] | str | int | None] | None:
    """Attend une action sur Windows (clavier via msvcrt ; souris non prise en charge)."""
    import msvcrt
    import time

    if not msvcrt.kbhit():
        time.sleep(min(temporisation, 0.1))
        return None
    touche = msvcrt.getwch()
    if touche in ("\x00", "\xe0"):
        code = msvcrt.getwch().lower()
        if code == "h":
            return ("haut", None)
        if code == "p":
            return ("bas", None)
        if code == "k":
            return ("gauche", None)
        if code == "m":
            return ("droite", None)
        return ("inconnu", None)
    if touche in ("\r", "\n"):
        return ("entree", None)
    if touche.lower() == "q":
        return ("annuler", None)
    if touche.isdigit():
        return ("numero", touche)
    return ("inconnu", touche)


def _position_curseur() -> tuple[int, int] | None:
    """Interroge la position du curseur (DSR 6) et renvoie (ligne, colonne).

    Les frappes qui arrivent pendant la sonde sont conservées dans ``_reste``
    pour être rejouées par la boucle de saisie principale.
    """
    _ecrire(f"{_ECHAP}[6n")
    reponse = b""
    while len(reponse) < 32:
        octet = _lire_octet(0.2)
        if octet is None:
            break
        reponse += bytes([octet])
        if reponse.endswith(b"R"):
            break
    correspondance = re.search(rb"(\d+);(\d+)R", reponse)
    if not correspondance:
        _reste.extend(reponse)
        return None
    _reste.extend(reponse[correspondance.end() :])
    return int(correspondance.group(1)), int(correspondance.group(2))


def _activer_souris() -> None:
    """Active le suivi de la souris (X10 + coordonnées SGR) si pris en charge."""
    if os.name != "nt":
        _ecrire(f"{_ECHAP}[?1000h{_ECHAP}[?1006h")


def _desactiver_souris() -> None:
    """Désactive le suivi de la souris."""
    if os.name != "nt":
        _ecrire(f"{_ECHAP}[?1006l{_ECHAP}[?1000l")


def _rendre_entete(titre: str) -> None:
    """Affiche le titre du menu en cyan."""
    _ecrire(f"{_ECHAP}[36;1m{titre} :{_ECHAP}[0m\n")


def _rendre_ligne_suivante(lignes: int) -> None:
    """Remonte de ``lignes`` lignes pour revenir au haut du bloc."""
    if lignes > 0:
        _ecrire(f"{_ECHAP}[{lignes}A")


def _rendre_liste(
    options: list[tuple[str, str]],
    selection: int,
    premier: bool = False,
) -> None:
    """Redessine le bloc d'options par déplacement relatif (aucun saut absolu).

    Le curseur se trouve toujours sur la ligne d'aide située sous le bloc au
    début et à la fin de l'affichage. Un rendu qui n'est pas ``premier`` en
    repart donc en remontant de ``len(options)`` lignes.
    """
    if not premier:
        _rendre_ligne_suivante(len(options))
    largeur = max(len(libelle) for _, libelle in options)
    for index, (_code, libelle) in enumerate(options):
        if index == selection:
            style = f"{_ECHAP}[44;1m{_ECHAP}[97m"
            curseur = f"{_ECHAP}[36;1m›{_ECHAP}[97m"
        else:
            style = _ECHAP + "[90m"
            curseur = " "
        _ecrire(
            _ECHAP
            + "[2K"
            + style
            + f" {curseur} {libelle.ljust(largeur)}  [{index + 1}]"
            + _ECHAP
            + "[0m\r\n"
        )
    _ecrire(
        _ECHAP + "[2K" + _ECHAP + "[37;90m"
        "⏵ Flèches ↑/↓ ou numéro · Entrée valide · clic souris · q/Échap annule" + _ECHAP + "[0m"
    )


def _effacer_bloc_relatif(lignes: int) -> None:
    """Efface le bloc (options + aide) et replace le curseur en haut du bloc."""
    _rendre_ligne_suivante(lignes)
    for index in range(lignes + 1):
        _ecrire(_ECHAP + "[2K")
        if index < lignes:
            _ecrire("\r\n")
    _rendre_ligne_suivante(lignes)


def menu_interactif(
    options: list[tuple[str, str]],
    titre: str = "Faites votre choix",
) -> str | None:
    """Affiche une liste pilotable par flèches, numéro ou clic souris.

    Renvoie le code de l'option choisie, ou None en cas d'annulation.
    """
    if not options:
        return None

    _rendre_entete(titre)
    selection = 0
    choix_final: tuple[str, str] | None = None

    try:
        _activer_souris()
        with _mode_saisie():
            _reste.clear()
            position = _position_curseur()
            ligne_debut = position[0] if position else None
            _rendre_liste(options, selection, premier=True)
            while True:
                action = _lire_action_windows() if os.name == "nt" else _lire_action()
                if action is None:
                    continue
                nom, valeur = action
                if nom in ("haut", "bas"):
                    pas = -1 if nom == "haut" else 1
                    selection = (selection + pas) % len(options)
                    _rendre_liste(options, selection)
                elif nom == "entree":
                    choix_final = options[selection]
                    return choix_final[0]
                elif nom == "numero" and isinstance(valeur, str):
                    numero = int(valeur) - 1
                    if 0 <= numero < len(options):
                        choix_final = options[numero]
                        return choix_final[0]
                elif nom == "souris" and isinstance(valeur, tuple) and ligne_debut:
                    _colonne, ligne = valeur
                    if ligne_debut <= ligne < ligne_debut + len(options):
                        choix_final = options[ligne - ligne_debut]
                        return choix_final[0]
                elif nom == "annuler":
                    return None
    except KeyboardInterrupt:
        return None
    finally:
        _desactiver_souris()
        _effacer_bloc_relatif(len(options))
        if choix_final is not None:
            code, libelle = choix_final
            _ecrire(f"{_ECHAP}[1mChoix : {code}. {libelle}{_ECHAP}[0m\n")
