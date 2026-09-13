"""Suggestion de ports libres à proximité d'un port occupé (V4)."""

from __future__ import annotations

from youcaport.core import process_manager
from youcaport.core.validator import PORT_MAX, valider_port


def suggerer_ports_libres(port: int | str, nombre: int = 3) -> list[int]:
    """Renvoie les 'nombre' premiers ports libres supérieurs au port donné.

    Se base sur un instantané unique des connexions pour rester rapide.
    """
    numero = valider_port(port)
    if nombre < 1:
        nombre = 1

    occupe = {port_ecoute for port_ecoute, _ in process_manager.lister_connexions_ecoute()}
    suggestions: list[int] = []
    suivant = numero + 1

    while suivant <= PORT_MAX and len(suggestions) < nombre:
        if suivant not in occupe:
            suggestions.append(suivant)
        suivant += 1

    return suggestions
