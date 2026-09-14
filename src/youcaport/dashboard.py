"""Interface web locale de YoucaPort (V5).

Le calcul des données reste dans core/ : ce module ne fait que servir du HTML/JSON.
"""

from __future__ import annotations

import contextlib
import json
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from youcaport.core import port_manager, privileges
from youcaport.core.port_manager import InfoPort
from youcaport.utils import terminal
from youcaport.utils.terminal import etat_francais

_DUREE_CACHE_PRIVILEGES = 20.0
_cache_privileges_age: float = 0.0
_cache_privileges_mapping: dict[int, dict] | None = None


def lancer_dashboard(
    port: int = 8421,
    ouvrir_navigateur: bool = True,
    avec_sudo: bool = False,
) -> None:
    """Démarre le serveur web local jusqu'à interruption (Ctrl+C)."""
    serveur = ThreadingHTTPServer(("127.0.0.1", port), _Gestionnaire)
    serveur.avec_sudo = avec_sudo
    adresse = f"http://127.0.0.1:{port}"
    terminal.afficher_information(f"Dashboard YoucaPort : {adresse}")
    terminal.afficher_information("Appuyez sur Ctrl+C pour arrêter le serveur.")

    if ouvrir_navigateur:
        threading.Timer(1.0, _ouvrir_navigateur, args=(adresse,)).start()

    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        terminal.afficher_information("Serveur arrêté.")
    finally:
        serveur.server_close()


def _ouvrir_navigateur(adresse: str) -> None:
    """Ouvre le navigateur par défaut, sans faire planter le serveur si absent."""
    with contextlib.suppress(Exception):
        webbrowser.open(adresse)


class _Gestionnaire(BaseHTTPRequestHandler):
    """Sert la page HTML et l'API JSON des ports utilisés."""

    def do_GET(self) -> None:
        chemin = urlparse(self.path).path
        try:
            if chemin in ("/", "/index.html"):
                corps = _PAGE_HTML
                self._repondre(200, "text/html; charset=utf-8", corps.encode("utf-8"))
            elif chemin == "/api/ports":
                infos = _infos_avec_privileges(bool(getattr(self.server, "avec_sudo", False)))
                corps = json.dumps(
                    _ports_dictionnaires(infos),
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


def _infos_avec_privileges(avec_sudo: bool) -> list[InfoPort]:
    """Ports utilisés, enrichis des données privilégiées si demandé et disponible."""
    infos = port_manager.lister_ports_utilises()
    mapping = _charger_privileges(avec_sudo)
    if mapping:
        infos = port_manager.enrichir_privilegies(infos, mapping)
    return infos


def _charger_privileges(avec_sudo: bool) -> dict[int, dict] | None:
    """Mapping privilégié en cache (jamais de prompt : sudo déjà authentifié)."""
    global _cache_privileges_age, _cache_privileges_mapping
    if not avec_sudo:
        return None
    if time.monotonic() - _cache_privileges_age < _DUREE_CACHE_PRIVILEGES:
        return _cache_privileges_mapping
    try:
        _cache_privileges_mapping = privileges.connexions_privilegiees(interactif=False)
    except privileges.SudoNonDisponibleError:
        _cache_privileges_mapping = None
    _cache_privileges_age = time.monotonic()
    return _cache_privileges_mapping


def _ports_dictionnaires(infos: list[InfoPort]) -> list[dict]:
    """Convertit les InfoPort en dictionnaires sérialisables en JSON."""
    return [
        {
            "port": info.port,
            "application": info.processus.nom if info.processus else "inconnu",
            "pid": info.processus.pid if info.processus else None,
            "etat": etat_francais(info.processus.etat) if info.processus else "-",
        }
        for info in infos
    ]


_PAGE_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>YoucaPort — Ports utilisés</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Crect width='24' height='24' rx='6' fill='%23022c22'/%3E%3Ccircle cx='12' cy='12' r='5' fill='none' stroke='%2334d399' stroke-width='2'/%3E%3Ccircle cx='12' cy='12' r='1.6' fill='%2334d399'/%3E%3C/svg%3E">
<style>
  :root {
    --bg: #0b1220; --panel: #111a2e; --panel2: #0f172a; --line: #1e293b;
    --fg: #e2e8f0; --muted: #94a3b8; --accent: #22d3ee; --ok: #34d399;
    --warn: #fbbf24; --bad: #f87171;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    background: radial-gradient(1200px 500px at 80% -10%, #16233f 0%, var(--bg) 55%);
    color: var(--fg); min-height: 100vh;
  }
  .wrap { max-width: 980px; margin: 0 auto; padding: 2rem 1.25rem 4rem; }
  header { display: flex; align-items: center; justify-content: space-between; gap: 1rem; flex-wrap: wrap; }
  .brand { display: flex; align-items: center; gap: .75rem; }
  .brand .dot { width: 12px; height: 12px; border-radius: 50%; background: var(--ok);
    box-shadow: 0 0 0 0 rgba(52,211,153,.5); animation: pulse 2s infinite; }
  @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(52,211,153,.45); }
    70% { box-shadow: 0 0 0 9px rgba(52,211,153,0); } 100% { box-shadow: 0 0 0 0 rgba(52,211,153,0); } }
  h1 { margin: 0; font-size: 1.35rem; letter-spacing: .02em; }
  h1 span { color: var(--accent); }
  .meta { color: var(--muted); font-size: .82rem; text-align: right; }
  .meta .countdown { font-variant-numeric: tabular-nums; }
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: .9rem; margin: 1.6rem 0; }
  .card { background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: 1rem 1.1rem; }
  .card .v { font-size: 1.7rem; font-weight: 700; font-variant-numeric: tabular-nums; }
  .card .k { color: var(--muted); font-size: .8rem; margin-top: .15rem; }
  .card.acc .v { color: var(--accent); } .card.ok .v { color: var(--ok); }
  .card.warn .v { color: var(--warn); } .card.mut .v { color: var(--muted); }
  .toolbar { display: flex; gap: .75rem; flex-wrap: wrap; align-items: center; margin-bottom: 1rem; }
  input[type=search] {
    flex: 1; min-width: 220px; background: var(--panel); color: var(--fg);
    border: 1px solid var(--line); border-radius: 10px; padding: .6rem .9rem; font-size: .95rem; outline: none;
  }
  input[type=search]:focus { border-color: var(--accent); }
  button {
    background: var(--panel); color: var(--accent); border: 1px solid var(--line);
    border-radius: 10px; padding: .6rem 1rem; font-size: .9rem; cursor: pointer;
  }
  button:hover { border-color: var(--accent); }
  table { width: 100%; border-collapse: collapse; background: var(--panel);
    border: 1px solid var(--line); border-radius: 14px; overflow: hidden; }
  th, td { padding: .7rem .9rem; text-align: left; }
  thead th {
    background: var(--panel2); color: var(--muted); font-size: .78rem; letter-spacing: .06em;
    text-transform: uppercase; cursor: pointer; user-select: none; white-space: nowrap;
  }
  thead th:hover { color: var(--accent); }
  thead th .arr { color: var(--accent); }
  tbody tr { border-top: 1px solid var(--line); }
  tbody tr:hover { background: rgba(34,211,238,.05); }
  td.port { font-weight: 600; font-variant-numeric: tabular-nums; }
  td.pid { font-variant-numeric: tabular-nums; color: var(--muted); }
  .badge { display: inline-block; padding: .15rem .55rem; border-radius: 999px;
    font-size: .75rem; border: 1px solid var(--line); }
  .badge.ok { color: var(--ok); border-color: rgba(52,211,153,.4); }
  .badge.warn { color: var(--warn); border-color: rgba(251,191,36,.4); }
  .unknown { color: var(--muted); font-style: italic; }
  .empty { text-align: center; color: var(--muted); padding: 2.5rem 0; }
  .note { color: var(--muted); font-size: .82rem; margin-top: 1.4rem; line-height: 1.5; }
  .note code { background: var(--panel2); border: 1px solid var(--line); padding: .1rem .4rem; border-radius: 6px; }
  ::selection { background: rgba(34,211,238,.3); }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="brand">
      <div class="dot"></div>
      <h1>YoucaPort <span>— Ports utilisés</span></h1>
    </div>
    <div class="meta">
      <span id="status">Connexion…</span> ·
      <span class="countdown">Prochaine mise à jour dans <b id="cd">5</b> s</span>
    </div>
  </header>

  <section class="stats" id="stats"></section>

  <div class="toolbar">
    <input type="search" id="q" placeholder="Filtrer par port, application ou PID…" autocomplete="off">
    <button id="refresh" title="Actualiser maintenant">Actualiser</button>
  </div>

  <table>
    <thead>
      <tr>
        <th data-key="port">Port <span class="arr"></span></th>
        <th data-key="application">Application <span class="arr"></span></th>
        <th data-key="pid">PID <span class="arr"></span></th>
        <th data-key="etat">État <span class="arr"></span></th>
      </tr>
    </thead>
    <tbody id="rows"></tbody>
  </table>

  <div class="note">
    Les ports affichés «&nbsp;<em>non identifié</em>&nbsp;» sont réellement en écoute mais leur
    processus n'est pas visible depuis cette session (service système, autre utilisateur, root).
    Pour les identifier sous Linux : <code>sudo ss -ltnp</code>. La page se rechargent toutes les
    5&nbsp;secondes ; l'arrêt d'un processus se fait côté CLI : <code>youcaport free &lt;port&gt;</code>.
  </div>
</div>

<script>
  const $ = (s) => document.querySelector(s);
  let donnees = [], tri = { cle: "port", sens: 1 }, filtre = "", delais = 5;

  const ETATS = {
    "en cours d'exécution": "ok", "en sommeil": "ok", "en écoute": "ok",
    "inactif": "ok",
    "en attente disque": "warn", "zombie": "warn", "arrêté": "warn", "-": "warn"
  };

  function echappe(t) {
    return String(t ?? "").replace(/[&<>"']/g,
      (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  async function charger() {
    try {
      const rep = await fetch("/api/ports", { cache: "no-store" });
      donnees = await rep.json();
      $('#status').textContent = "À jour";
      $('#status').style.color = "var(--ok)";
    } catch (_) {
      $('#status').textContent = "Erreur de connexion";
      $('#status').style.color = "var(--bad)";
    }
    rendre();
  }

  function stats() {
    const connus = donnees.filter((d) => d.pid !== null);
    const applications = new Set(connus.map((d) => d.application)).size;
    return [
      { v: donnees.length, k: "Ports en écoute", cls: "acc" },
      { v: connus.length, k: "Processus identifiés", cls: "ok" },
      { v: donnees.length - connus.length, k: "Non identifiés", cls: "mut" },
      { v: applications, k: "Applications distinctes", cls: "warn" }
    ];
  }

  function rendre() {
    $('#stats').innerHTML = stats().map((c) =>
      `<div class="card ${c.cls}"><div class="v">${c.v}</div><div class="k">${c.k}</div></div>`).join("");

    const vu = donnees
      .filter((d) => {
        const flux = `${d.port} ${d.application} ${d.pid}`.toLowerCase();
        return !filtre || flux.includes(filtre);
      })
      .sort((a, b) => {
        const va = a[tri.cle] ?? ""; const vb = b[tri.cle] ?? "";
        const cmp = typeof va === "number" ? va - vb : String(va).localeCompare(String(vb));
        return cmp * tri.sens;
      });

    const corps = vu.map((d) => {
      const inconnu = d.pid === null;
      const nom = inconnu ? "non identifié" : d.application;
      const pid = inconnu ? "-" : d.pid;
      const badge = ETATS[String(d.etat).toLowerCase()] || "warn";
      return `<tr>
        <td class="port">${d.port}</td>
        <td class="${inconnu ? "unknown" : ""}">${echappe(nom)}</td>
        <td class="pid">${pid}</td>
        <td><span class="badge ${badge}">${echappe(d.etat)}</span></td>
      </tr>`;
    }).join("");

    $('#rows').innerHTML = corps || `<tr><td colspan="4" class="empty">Aucun port ne correspond au filtre.</td></tr>`;
  }

  document.querySelectorAll("thead th").forEach((th) => {
    th.addEventListener("click", () => {
      const cle = th.dataset.key;
      if (tri.cle === cle) { tri.sens *= -1; } else { tri.cle = cle; tri.sens = 1; }
      document.querySelectorAll("thead th").forEach((t) => { t.querySelector(".arr").textContent = ""; });
      th.querySelector(".arr").textContent = tri.sens === 1 ? "▲" : "▼";
      rendre();
    });
  });

  $('#q').addEventListener("input", (e) => { filtre = e.target.value.trim().toLowerCase(); rendre(); });
  $('#refresh').addEventListener("click", charger);

  setInterval(() => {
    delais -= 1;
    if (delais <= 0) { delais = 5; charger(); } else { $('#cd').textContent = delais; }
  }, 1000);

  charger();
</script>
</body>
</html>
"""
