"""Small local GM workbench. No player or remote access surface yet."""

import html
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .core import DomainError
from .store import add_observation, add_source, campaign_view, connect, create_campaign, establish_fact


def esc(value):
    return html.escape(str(value), quote=True)


CSS = """
:root{font-family:ui-sans-serif,system-ui,sans-serif;color:#19251f;background:#f5f5ef}
*{box-sizing:border-box}body{margin:0}header{background:#173a2d;color:#fff;padding:20px max(24px,calc((100vw - 1120px)/2))}
header a{color:#fff;text-decoration:none;font-weight:700;letter-spacing:.03em}main{max-width:1120px;margin:36px auto;padding:0 24px}
h1{font-family:Georgia,serif;font-size:clamp(2rem,4vw,3.2rem);font-weight:500;margin:0 0 8px}h2{font-size:1.15rem;margin:0 0 18px}
p{line-height:1.5}.muted,small{color:#64736a}.lead{font-size:1.08rem;color:#47574c;margin:0 0 30px}
.grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(300px,.85fr);gap:26px;align-items:start}.stack{display:grid;gap:22px;align-content:start}
section{background:white;border:1px solid #dbe3d8;border-radius:12px;padding:24px;min-width:0}
label{display:block;font-size:.91rem;font-weight:650;margin:12px 0 6px}input,textarea,select{font:inherit;width:100%;padding:10px 12px;border:1px solid #aebbb0;border-radius:6px;background:#fff;color:#19251f}textarea{min-height:84px;resize:vertical}
button{font:inherit;font-weight:650;border:0;border-radius:6px;background:#206448;color:white;padding:10px 15px;cursor:pointer;margin-top:14px}button:hover{background:#154b36}button:focus-visible,input:focus-visible,textarea:focus-visible,select:focus-visible,a:focus-visible{outline:3px solid #e5a54a;outline-offset:2px}
.row{border-top:1px solid #e4e9e1;padding:14px 0}.row:first-of-type{border-top:0}.row p{margin:6px 0}.tag{display:inline-block;font-size:.76rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:#31664d}
.fact{border-left:3px solid #3d8060;padding-left:14px}.error{padding:13px 16px;background:#ffede8;color:#8a311d;border-radius:7px;margin-bottom:22px}
a{color:#176344}.search{display:flex;gap:8px;align-items:end}.search input{flex:1}.search button{margin:0}
@media(max-width:760px){.grid{grid-template-columns:1fr}main{margin:22px auto}section{padding:18px}.search{align-items:stretch;flex-direction:column}}
"""


def page(body, title="Atelier de campagne"):
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><style>{CSS}</style></head><body><header><a href="/">Atelier de campagne</a></header><main>{body}</main></body></html>"""


def render_home(db):
    campaigns = db.execute("SELECT * FROM campaigns ORDER BY id DESC").fetchall()
    rows = "".join(f'<div class="row"><a href="/campaign/{c["id"]}">{esc(c["name"])}</a> <small>· {esc(c["language"])}</small></div>' for c in campaigns)
    return page(f"""<h1>Vos campagnes</h1><p class="lead">Un espace local pour établir ce qui fait foi à votre table.</p><div class="grid"><section><h2>Campagnes</h2>{rows or '<p class="muted">Aucune campagne pour le moment.</p>'}</section><section><h2>Nouvelle campagne</h2><form method="post" action="/campaign"><label for="name">Nom</label><input id="name" name="name" maxlength="100" required><label for="language">Langue</label><input id="language" name="language" value="fr" maxlength="16" required><button>Créer</button></form></section></div>""")


def render_campaign(db, campaign_id, query=""):
    campaign, sources, observations, facts = campaign_view(db, campaign_id, query)
    sid = esc(campaign_id)
    source_options = "".join(f'<option value="{s["id"]}">{esc(s["title"])} · {esc(s["locator"])}</option>' for s in sources)
    obs_options = "".join(f'<option value="{o["id"]}">#{o["id"]} · {esc(o["text"][:75])}</option>' for o in observations)
    fact_rows = "".join(f'<div class="row fact"><span class="tag">Fait établi · MJ seulement</span><p>{esc(f["text"])}</p><small>Décision : {esc(f["instruction"])}<br>Observation : {esc(f["observation"])}<br>Source : {esc(f["source_title"])} · {esc(f["locator"])}</small></div>' for f in facts)
    obs_rows = "".join(f'<div class="row"><span class="tag">Observation {"simulée" if o["kind"] == "simulated_play" else "de note"} · non canonique</span><p>#{o["id"]} · {esc(o["text"])}</p><small>{esc(o["source_title"])} · {esc(o["locator"])}</small></div>' for o in observations)
    source_rows = "".join(f'<div class="row"><strong>{esc(s["title"])}</strong><p>{esc(s["note"])}</p><small>Repère : {esc(s["locator"])}</small></div>' for s in sources)
    return page(f"""
      <h1>{esc(campaign['name'])}</h1><p class="lead">Langue : {esc(campaign['language'])} · Espace privé du MJ · démonstration locale</p>
      <div class="grid"><div class="stack">
        <section><h2>Faits établis</h2><form method="get" action="/campaign/{sid}" class="search"><div style="flex:1"><label for="q">Rechercher un fait</label><input id="q" name="q" value="{esc(query)}"></div><button>Chercher</button></form>{fact_rows or '<p class="muted">Aucun fait correspondant.</p>'}</section>
        <section><h2>Observations</h2>{obs_rows or '<p class="muted">Ajoutez une source puis une observation.</p>'}</section>
        <section><h2>Sources</h2>{source_rows or '<p class="muted">Aucune source.</p>'}</section>
      </div><div class="stack">
        <section><h2>1 · Ajouter une source</h2><form method="post" action="/campaign/{sid}/source"><label for="title">Titre</label><input id="title" name="title" maxlength="200" required><label for="locator">Repère vérifiable</label><input id="locator" name="locator" placeholder="Page, section ou note fictive" maxlength="200" required><label for="note">Description</label><textarea id="note" name="note" maxlength="2000" required></textarea><button>Enregistrer la source</button></form></section>
        <section><h2>2 · Relever un événement</h2><form method="post" action="/campaign/{sid}/observation"><label for="source_id">Source</label><select id="source_id" name="source_id" required>{source_options}</select><label for="observation">Ce qui a été observé</label><textarea id="observation" name="text" maxlength="2000" required></textarea><label for="kind">Nature</label><select id="kind" name="kind"><option value="note">Note</option><option value="simulated_play">Jeu simulé</option></select><button {'' if sources else 'disabled'}>Ajouter l'observation</button></form></section>
        <section><h2>3 · Décider ce qui fait foi</h2><form method="post" action="/campaign/{sid}/fact"><label for="observation_id">Observation à examiner</label><select id="observation_id" name="observation_id" required>{obs_options}</select><label for="instruction">Décision du MJ</label><input id="instruction" name="instruction" maxlength="1000" placeholder="Ex. Retenir cet événement, corriger le nom" required><label for="fact">Formulation canonique</label><textarea id="fact" name="fact" maxlength="2000" required></textarea><button {'' if observations else 'disabled'}>Établir le fait</button></form></section>
      </div></div>""", campaign['name'])


def make_handler(db_path):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status, body, location=None):
            data = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'")
            if location:
                self.send_header("Location", location)
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if not self._local_host():
                return
            parsed = urlparse(self.path)
            try:
                with closing(connect(db_path)) as db:
                    if parsed.path == "/":
                        body = render_home(db)
                    elif parsed.path.startswith("/campaign/"):
                        body = render_campaign(db, int(parsed.path.split("/")[2]), parse_qs(parsed.query).get("q", [""])[0][:200])
                    else:
                        self._send(404, page("<h1>Page introuvable</h1>"))
                        return
                self._send(200, body)
            except (DomainError, ValueError, IndexError) as exc:
                self._send(400, page(f'<div class="error">{esc(exc)}</div>'))

        def do_POST(self):
            if not self._local_host():
                return
            origin = self.headers.get("Origin")
            host = self.headers.get("Host", "")
            if origin and origin != f"http://{host}":
                self._send(403, page('<div class="error">Origine refusée.</div>'))
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 16000:
                    raise DomainError("Formulaire trop volumineux ou vide.")
                fields = parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True)
                val = lambda key: fields.get(key, [""])[0]
                parts = urlparse(self.path).path.strip("/").split("/")
                with closing(connect(db_path)) as db:
                    if parts == ["campaign"]:
                        campaign_id = create_campaign(db, val("name"), val("language"))
                    elif len(parts) == 3 and parts[0] == "campaign":
                        campaign_id = int(parts[1])
                        if parts[2] == "source":
                            add_source(db, campaign_id, val("title"), val("locator"), val("note"))
                        elif parts[2] == "observation":
                            add_observation(db, campaign_id, int(val("source_id")), val("text"), val("kind"))
                        elif parts[2] == "fact":
                            establish_fact(db, campaign_id, int(val("observation_id")), val("instruction"), val("fact"))
                        else:
                            raise DomainError("Action inconnue.")
                    else:
                        raise DomainError("Action inconnue.")
                self._send(303, "", f"/campaign/{campaign_id}")
            except (DomainError, ValueError, IndexError, UnicodeError) as exc:
                self._send(400, page(f'<div class="error">{esc(exc)}</div><p><a href="/">Retour aux campagnes</a></p>'))

        def _local_host(self):
            port = self.server.server_port
            if self.headers.get("Host") not in (f"127.0.0.1:{port}", f"localhost:{port}"):
                self._send(403, page('<div class="error">Hôte refusé.</div>'))
                return False
            return True

    return Handler


def serve(db_path, port=8899):
    with ThreadingHTTPServer(("127.0.0.1", port), make_handler(db_path)) as server:
        print(f"Atelier local : http://127.0.0.1:{port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("Atelier arrêté.")
