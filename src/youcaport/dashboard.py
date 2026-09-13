"""Interface web locale de YoucaPort (V5).

Le calcul des données reste dans core/ : ce module ne fait que servir du HTML/JSON.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from youcaport.core import port_manager
from youcaport.core.port_manager import InfoPort
from youcaport.utils import terminal


def lancer_dashboard(port: int = 8421) -> None:
    """Démarre le serveur web local jusqu'à interruption (Ctrl+C)."""
    serveur = ThreadingHTTPServer(("127.0.0.1", port), _Gestionnaire)
    terminal.afficher_information(f"Dashboard YoucaPort : http://127.0.0.1:{port}")
    terminal.afficher_information("Appuyez sur Ctrl+C pour arrêter le serveur.")

    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        terminal.afficher_information("Serveur arrêté.")
    finally:
        serveur.server_close()


class _Gestionnaire(BaseHTTPRequestHandler):
    """Sert la page HTML et l'API JSON des ports utilisés."""

    def do_GET(self) -> None:
        chemin = urlparse(self.path).path
        try:
            if chemin in ("/", "/index.html"):
                corps = _page_html(port_manager.lister_ports_utilises())
                self._repondre(200, "text/html; charset=utf-8", corps.encode("utf-8"))
            elif chemin == "/api/ports":
                corps = json.dumps(
                    _ports_dictionnaires(port_manager.lister_ports_utilises()),
                    ensure_ascii=False,
                )
                self._repondre(200, "application/json; charset=utf-8", corps.encode("utf-8"))
            else:
                self._repondre(404, "text/plain; charset=utf-8", b"Page introuvable")
        except Exception as exc:
            terminal.afficher_exception(exc)
            self._repondre(500, "text/plain; charset=utf-8", str(exc).encode("utf-8"))

    def log_message(self, _format: str, *args: object) -> None:
        """Silencieux : aucune trace de requête HTTP en console."""

    def _repondre(self, statut: int, type_contenu: str, corps: bytes) -> None:
        self.send_response(statut)
        self.send_header("Content-Type", type_contenu)
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)


def _ports_dictionnaires(infos: list[InfoPort]) -> list[dict]:
    """Convertit les InfoPort en dictionnaires sérialisables en JSON."""
    return [
        {
            "port": info.port,
            "application": info.processus.nom if info.processus else "inconnu",
            "pid": info.processus.pid if info.processus else None,
            "etat": info.processus.etat.upper() if info.processus else "INCONNU",
        }
        for info in infos
    ]


def _page_html(infos: list[InfoPort]) -> str:
    """Génère la page HTML simple affichant les ports (auto-rechargement)."""
    lignes = "".join(_ligne_html(donnees) for donnees in _ports_dictionnaires(infos))
    total = len(infos)

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="5">
<title>YoucaPort — Ports utilisés</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #0f172a; color: #e2e8f0; }}
  h1 {{ color: #22d3ee; }}
  table {{ border-collapse: collapse; width: 100%; max-width: 640px; }}
  th, td {{ border: 1px solid #334155; padding: 0.5rem 0.75rem; text-align: left; }}
  th {{ background: #1e293b; color: #22d3ee; }}
  .note {{ color: #94a3b8; margin-top: 1rem; }}
</style>
</head>
<body>
<h1>YoucaPort</h1>
<p>Ports utilisés : <strong>{total}</strong></p>
<table>
<tr><th>PORT</th><th>APPLICATION</th><th>PID</th><th>STATUS</th></tr>
{lignes}
</table>
<p class="note">Page auto-rechargée toutes les 5 secondes.</p>
</body>
</html>"""


def _ligne_html(donnees: dict) -> str:
    """Convertit une donnée de port en ligne <tr> HTML."""
    pid = "-" if donnees["pid"] is None else donnees["pid"]
    return (
        f"<tr><td>{donnees['port']}</td><td>{donnees['application']}</td>"
        f"<td>{pid}</td><td>{donnees['etat']}</td></tr>"
    )
