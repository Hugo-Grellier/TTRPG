"""Small local GM workbench. No player or remote access surface yet."""

import html
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .core import DomainError
from .i18n import locale, t
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


def page(body, title=None, language="en"):
    title = title or t("app.title", language)
    return f"""<!doctype html><html lang="{locale(language)}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><style>{CSS}</style></head><body><header><a href="/">{esc(t('app.title', language))}</a></header><main>{body}</main></body></html>"""


def render_home(db, language="en"):
    language = locale(language)
    tr = lambda key: esc(t(key, language))
    campaigns = db.execute("SELECT * FROM campaigns ORDER BY id DESC").fetchall()
    rows = "".join(f'<div class="row"><a href="/campaign/{c["id"]}">{esc(c["name"])}</a> <small>· {esc(c["language"])}</small></div>' for c in campaigns)
    switch = f'<a href="/?lang=fr">{tr("home.switch_fr")}</a>' if language == "en" else f'<a href="/?lang=en">{tr("home.switch_en")}</a>'
    return page(f"""<p>{switch}</p><h1>{tr('home.title')}</h1><p class="lead">{tr('home.lead')}</p><div class="grid"><section><h2>{tr('home.campaigns')}</h2>{rows or f'<p class="muted">{tr("home.empty")}</p>'}</section><section><h2>{tr('home.new')}</h2><form method="post" action="/campaign"><label for="name">{tr('field.name')}</label><input id="name" name="name" maxlength="100" required><label for="language">{tr('field.language')}</label><input id="language" name="language" value="{esc(language)}" maxlength="16" required><button>{tr('action.create')}</button></form></section></div>""", language=language)


def render_campaign(db, campaign_id, query=""):
    campaign, sources, observations, facts = campaign_view(db, campaign_id, query)
    language = campaign["language"]
    tr = lambda key: esc(t(key, language))
    sid = esc(campaign_id)
    source_options = "".join(f'<option value="{s["id"]}">{esc(s["title"])} · {esc(s["locator"])}</option>' for s in sources)
    obs_options = "".join(f'<option value="{o["id"]}">#{o["id"]} · {esc(o["text"][:75])}</option>' for o in observations)
    fact_rows = "".join(f'<div class="row fact"><span class="tag">{tr("facts.tag")}</span><p>{esc(f["text"])}</p><small>{tr("label.decision")}: {esc(f["instruction"])}<br>{tr("label.observation")}: {esc(f["observation"])}<br>{tr("label.source")}: {esc(f["source_title"])} · {esc(f["locator"])}</small></div>' for f in facts)
    obs_rows = "".join(f'<div class="row"><span class="tag">{tr("observations.simulated" if o["kind"] == "simulated_play" else "observations.note")}</span><p>#{o["id"]} · {esc(o["text"])}</p><small>{esc(o["source_title"])} · {esc(o["locator"])}</small></div>' for o in observations)
    source_rows = "".join(f'<div class="row"><strong>{esc(s["title"])}</strong><p>{esc(s["note"])}</p><small>{tr("label.locator")}: {esc(s["locator"])}</small></div>' for s in sources)
    return page(f"""
      <h1>{esc(campaign['name'])}</h1><p class="lead">{esc(t('campaign.lead', language, campaign_language=language))}</p>
      <div class="grid"><div class="stack">
        <section><h2>{tr('facts.title')}</h2><form method="get" action="/campaign/{sid}" class="search"><div style="flex:1"><label for="q">{tr('facts.search')}</label><input id="q" name="q" value="{esc(query)}"></div><button>{tr('action.search')}</button></form>{fact_rows or f'<p class="muted">{tr("facts.empty")}</p>'}</section>
        <section><h2>{tr('observations.title')}</h2>{obs_rows or f'<p class="muted">{tr("observations.empty")}</p>'}</section>
        <section><h2>{tr('sources.title')}</h2>{source_rows or f'<p class="muted">{tr("sources.empty")}</p>'}</section>
      </div><div class="stack">
        <section><h2>{tr('source.add')}</h2><form method="post" action="/campaign/{sid}/source"><label for="title">{tr('field.title')}</label><input id="title" name="title" maxlength="200" required><label for="locator">{tr('field.locator')}</label><input id="locator" name="locator" placeholder="{tr('source.locator_hint')}" maxlength="200" required><label for="note">{tr('field.description')}</label><textarea id="note" name="note" maxlength="2000" required></textarea><button>{tr('action.save_source')}</button></form></section>
        <section><h2>{tr('observation.add')}</h2><form method="post" action="/campaign/{sid}/observation"><label for="source_id">{tr('label.source')}</label><select id="source_id" name="source_id" required>{source_options}</select><label for="observation">{tr('field.observed')}</label><textarea id="observation" name="text" maxlength="2000" required></textarea><label for="kind">{tr('field.kind')}</label><select id="kind" name="kind"><option value="note">{tr('kind.note')}</option><option value="simulated_play">{tr('kind.simulated')}</option></select><button {'' if sources else 'disabled'}>{tr('action.add_observation')}</button></form></section>
        <section><h2>{tr('fact.add')}</h2><form method="post" action="/campaign/{sid}/fact"><label for="observation_id">{tr('field.review_observation')}</label><select id="observation_id" name="observation_id" required>{obs_options}</select><label for="instruction">{tr('field.gm_decision')}</label><input id="instruction" name="instruction" maxlength="1000" placeholder="{tr('fact.decision_hint')}" required><label for="fact">{tr('field.canonical_fact')}</label><textarea id="fact" name="fact" maxlength="2000" required></textarea><button {'' if observations else 'disabled'}>{tr('action.establish_fact')}</button></form></section>
      </div></div>""", campaign['name'], language)


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
                        body = render_home(db, parse_qs(parsed.query).get("lang", ["en"])[0][:16])
                    elif parsed.path.startswith("/campaign/"):
                        body = render_campaign(db, int(parsed.path.split("/")[2]), parse_qs(parsed.query).get("q", [""])[0][:200])
                    else:
                        self._send(404, page(f"<h1>{esc(t('error.not_found_page'))}</h1>"))
                        return
                self._send(200, body)
            except (DomainError, ValueError, IndexError) as exc:
                message = exc.localized() if isinstance(exc, DomainError) else t("error.invalid_input")
                self._send(400, page(f'<div class="error">{esc(message)}</div>'))

        def do_POST(self):
            if not self._local_host():
                return
            origin = self.headers.get("Origin")
            host = self.headers.get("Host", "")
            if origin and origin != f"http://{host}":
                self._send(403, page(f'<div class="error">{esc(t("error.bad_origin"))}</div>'))
                return
            language = "en"
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 16000:
                    raise DomainError("error.form_size")
                fields = parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True)
                val = lambda key: fields.get(key, [""])[0]
                parts = urlparse(self.path).path.strip("/").split("/")
                if parts == ["campaign"]:
                    language = val("language") or "en"
                with closing(connect(db_path)) as db:
                    if parts == ["campaign"]:
                        campaign_id = create_campaign(db, val("name"), val("language"))
                    elif len(parts) == 3 and parts[0] == "campaign":
                        campaign_id = int(parts[1])
                        row = db.execute("SELECT language FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
                        if row:
                            language = row[0]
                        if parts[2] == "source":
                            add_source(db, campaign_id, val("title"), val("locator"), val("note"))
                        elif parts[2] == "observation":
                            add_observation(db, campaign_id, int(val("source_id")), val("text"), val("kind"))
                        elif parts[2] == "fact":
                            establish_fact(db, campaign_id, int(val("observation_id")), val("instruction"), val("fact"))
                        else:
                            raise DomainError("error.unknown_action")
                    else:
                        raise DomainError("error.unknown_action")
                self._send(303, "", f"/campaign/{campaign_id}")
            except (DomainError, ValueError, IndexError, UnicodeError) as exc:
                message = exc.localized(language) if isinstance(exc, DomainError) else t("error.invalid_input", language)
                self._send(400, page(f'<div class="error">{esc(message)}</div><p><a href="/">{esc(t("error.back", language))}</a></p>', language=language))

        def _local_host(self):
            port = self.server.server_port
            if self.headers.get("Host") not in (f"127.0.0.1:{port}", f"localhost:{port}"):
                self._send(403, page(f'<div class="error">{esc(t("error.bad_host"))}</div>'))
                return False
            return True

    return Handler


def serve(db_path, port=8899):
    with ThreadingHTTPServer(("127.0.0.1", port), make_handler(db_path)) as server:
        print(f"Local workbench: http://127.0.0.1:{port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("Workbench stopped.")
