"""Validation des numéros de port."""

from __future__ import annotations

PORT_MIN = 1
PORT_MAX = 65535

MESSAGE_PORT_INVALIDE = "Numéro de port invalide. Veuillez entrer un port compris entre 1 et 65535."


class YoucaPortError(Exception):
    """Erreur de base commune a toutes les erreurs de YoucaPort."""


class PortInvalideError(YoucaPortError):
    """Le numéro de port fourni est hors des limites autorisées (1-65535)."""


def valider_port(port: int | str) -> int:
    """Convertit et valide un numéro de port, renvoie un entier.

    Lève PortInvalideError lorsque la valeur n'est pas un entier entre 1 et 65535.
    """
    try:
        if isinstance(port, bool) or not isinstance(port, (int, str)):
            raise ValueError
        valeur = int(port)
    except (TypeError, ValueError) as exc:
        raise PortInvalideError(MESSAGE_PORT_INVALIDE) from exc

    if valeur < PORT_MIN or valeur > PORT_MAX:
        raise PortInvalideError(MESSAGE_PORT_INVALIDE)

    return valeur
