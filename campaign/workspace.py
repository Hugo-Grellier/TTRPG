"""Campaign conversation and document review workspace."""

import html
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import quote as url_quote

from .agent_cli import draft_diff, draft_file_review
from .campaign_file_drafts import campaign_file_draft_review
from .core import DomainError
from .dossier_files import backlinks, bible_element_texts, document_title, dossier_document, dossier_documents, dossier_root, linked_markdown, visual_file
from .i18n import locale, t
from .library import library_document, library_documents, library_page, library_search
from .markdown import render_blocks, render_markdown, visible_text
from .prep_drafts import preparation_draft_review
from .scenario import dossier_stats
from .skills import available_skills
from .store import (COMMENT_TARGETS, PRODUCT_DOCS, agent_turns, bible_comments, campaign_view,
                    comments_for, journey_view, product_doc)


def esc(value):
    return html.escape(str(value), quote=True)


def campaign_bible(db, campaign_id):
    """Optional private, editable presentation of a proposed scenario state."""
    path = dossier_root(db, campaign_id) / "bible.json"
    if not path.is_file():
        return None
    try:
        bible = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return bible if isinstance(bible, dict) and "title" in bible and "lead" in bible else None


def bible_html(db, campaign_id, bible, established_facts, comment_counts, language):
    paths = {row["path"]: row["id"] for row in dossier_documents(db, campaign_id)}
    element_texts = bible_element_texts(db, campaign_id)
    tx = lambda key: esc(t(key, language))
    def target(key):
        return (f'data-bible-key="{esc(key)}" data-bible-quote="{esc(element_texts.get(key, ""))}" '
                f'data-comment-count="{comment_counts.get(key, 0)}"')
    def href(path):
        item = paths.get(path)
        return f"/workspace/{campaign_id}?doc=campaign_files:{item}" if item else "#"
    def visual(name):
        try:
            visual_file(db, campaign_id, name)
        except DomainError:
            return ""
        return f"/campaign/{campaign_id}/visual/{name}"
    def card(item, kind):
        picture = visual(item.get("image", ""))
        mask = visual(item.get("image", "").removesuffix(".png") + "-mask.png") if picture else ""
        style = f' style="mask-image:url({esc(mask)});mask-mode:luminance;mask-size:contain;mask-position:center bottom;mask-repeat:no-repeat"' if mask else ""
        img = f'<img loading="lazy" src="{esc(picture)}" alt="{esc(item.get("alt", ""))}"{style}>' if picture else ""
        return (f'<a class="bible-card {kind}" {target(f"people:{item.get("file", "")}")} href="{esc(href(item.get("file", "")))}">{img}'
                f'<span class="bible-card-copy"><small>{esc(item.get("tag", ""))}</small>'
                f'<strong>{esc(item["title"])}</strong><span>{esc(item.get("summary", ""))}</span></span></a>')
    map_src = visual(bible.get("map", ""))
    hero_image = f'<img src="{esc(map_src)}" alt="{esc(bible.get("map_alt", t("bible.map_alt", language)))}">' if map_src else ""
    map_html = (f'<a class="bible-map" {target(f"map:{bible.get("map_file", "")}")} href="{esc(href(bible.get("map_file", "")))}"><img src="{esc(map_src)}" '
                f'alt="{esc(bible.get("map_alt", t("bible.map_alt", language)))}"><span>{tx("bible.explore")}</span></a>') if map_src else ""
    state_rows = ''.join(f'<li {target(f"state:{fact["label"]}")}><span>{esc(fact["label"])}</span><strong>{esc(fact["text"])}</strong></li>' for fact in bible.get("state", []))
    if established_facts:
        established_rows = ''.join(f'<li {target(f"fact:{fact["id"]}")}><span>{tx("bible.fact")}</span><strong>{esc(fact["text"])}</strong></li>'
                                   for fact in established_facts[:4])
        state_rows = established_rows + state_rows
        truth = t("bible.truth_facts", language, count=len(established_facts))
    else:
        truth = t("bible.truth_empty", language)
    stakes = ''.join(f'<a class="bible-stake {esc(item.get("tone", ""))}" {target(f"stakes:{item.get("file", "")}")} href="{esc(href(item.get("file", "")))}">'
                     f'<small>{esc(item.get("tag", t("bible.stake_tag", language)))}</small><strong>{esc(item["title"])}</strong>'
                     f'<span>{esc(item.get("summary", ""))}</span></a>' for item in bible.get("stakes", []))
    steps = ''.join(f'<a {target(f"scenes:{item.get("file", "")}")} href="{esc(href(item.get("file", "")))}"><i>{index:02d}</i><span><strong>{esc(item["title"])}</strong>'
                    f'<small>{esc(item.get("summary", ""))}</small></span></a>' for index, item in enumerate(bible.get("scenes", []), 1))
    people = ''.join(card(item, "person") for item in bible.get("people", []))
    nodes = bible.get("relations", {}).get("nodes", [])
    edges = bible.get("relations", {}).get("edges", [])
    positions = [(80, 55), (300, 45), (530, 55), (110, 170), (350, 170), (590, 170)]
    edge_svg = ''.join(f'<line x1="{positions[a][0]}" y1="{positions[a][1]}" x2="{positions[b][0]}" y2="{positions[b][1]}"/>'
                       for a, b in edges if 0 <= a < len(nodes) and 0 <= b < len(nodes) and a < len(positions) and b < len(positions))
    node_svg = ''.join(f'<a {target(f"relation:{node.get("file", "")}")} href="{esc(href(node.get("file", "")))}"><circle cx="{positions[i][0]}" cy="{positions[i][1]}" r="36"/>'
                       f'<text x="{positions[i][0]}" y="{positions[i][1] + 3}" text-anchor="middle">{esc(node["label"])}</text></a>'
                       for i, node in enumerate(nodes[:6]))
    graph_html = (f'<section class="bible-relations"><div class="bible-section-title"><small>{tx("bible.section_network")}</small><h2>{tx("bible.network")}</h2>'
                  f'<a href="{esc(href("02-Relations.md"))}">{tx("bible.network_full")}</a></div>'
                  f'<svg viewBox="0 0 680 225" role="img" aria-label="{tx("bible.network_alt")}">'
                  f'<g class="relation-lines">{edge_svg}</g><g class="relation-nodes">{node_svg}</g></svg>'
                  f'<p>{esc(bible.get("relations", {}).get("caption", ""))}</p></section>') if nodes else ""
    return (f'<div class="bible"><header class="bible-hero"><div {target("hero")}><p class="bible-eyebrow">{tx("bible.hero_label")} <span>·</span> {tx("bible.mixed" if established_facts else "bible.proposed")}</p>'
            f'<h1>{esc(bible["title"])}</h1><p>{esc(bible["lead"])}</p><div class="bible-hero-links">'
            f'<a href="{esc(href("02-Relations.md"))}">{tx("bible.relations")}</a>'
            f'<a href="{esc(href("04-Chronologie.md"))}">{tx("bible.timeline")}</a></div></div>'
            f'<div class="bible-hero-art">{hero_image}</div></header>'
            f'<div class="bible-truth">{esc(truth)}</div>'
            f'<div class="bible-columns"><section class="bible-state"><div class="bible-section-title"><small>{tx("bible.section_now")}</small>'
            f'<h2>{tx("bible.situation")}</h2></div><ul>{state_rows}</ul></section>'
            f'<section class="bible-stakes"><div class="bible-section-title"><small>{tx("bible.section_stakes")}</small><h2>{tx("bible.stakes")}</h2></div>{stakes}</section></div>'
            f'<section class="bible-scenes"><div class="bible-section-title"><small>{tx("bible.section_play")}</small><h2>{tx("bible.path")}</h2>'
            f'<a href="{esc(href("03-Parcours.md"))}">{tx("bible.path_full")}</a></div><div class="bible-scene-list">{steps}</div></section>'
            f'{graph_html}<div class="bible-columns bible-lower"><section><div class="bible-section-title"><small>{tx("bible.section_terrain")}</small><h2>{tx("bible.citadel")}</h2></div>'
            f'{map_html}</section><section><div class="bible-section-title"><small>{tx("bible.section_people")}</small><h2>{tx("bible.people")}</h2></div>'
            f'<div class="bible-people">{people}</div></section></div>'
            f'<p class="bible-footnote">{tx("bible.footnote")}</p></div>')


def record_blocks(value, offset, marked):
    return "".join(
        f'<div class="doc-line commentable-block {"has-comments" if any(start <= line <= end for line in marked) else ""}" data-line-start="{start}" data-line-end="{end}">'
        f'<button class="line-number" type="button" data-line="{start}" aria-label="Line {start}">{start}</button>'
        f'<div class="block-content">{rendered}</div></div>'
        for first, last, rendered in render_blocks(str(value))
        for start, end in ((offset + first, offset + last),)
    )


def dossier_blocks(source, marked, scene=False, campaign_id=None, db=None):
    pieces = []
    opened = False
    for first, last, rendered in render_blocks(source):
        if campaign_id and db:
            def masked(match):
                mask_name = match[2].removesuffix(".png") + "-mask.png"
                try:
                    visual_file(db, campaign_id, mask_name)
                except DomainError:
                    return match[0]
                return match[0][:-1].rstrip(' /') + f' style="mask-image:url(/campaign/{campaign_id}/visual/{mask_name});mask-mode:luminance;mask-size:contain;mask-position:center bottom;mask-repeat:no-repeat">'
            rendered = re.sub(r'<img\s+[^>]*src="(/campaign/\d+/visual/([a-zA-Z0-9_-]+\.png))"[^>]*>', masked, rendered)
        line = source.splitlines()[first - 1].strip()
        if scene and line.startswith("## "):
            if opened:
                pieces.append('</section>')
            heading = line[3:].lower()
            tone = ("danger" if any(word in heading for word in ("horloge", "enjeu", "conflit", "alerte"))
                    else "outcome" if any(word in heading for word in ("sortie", "secret", "révélation", "choix"))
                    else "clue" if any(word in heading for word in ("poser", "piste", "information", "découvr", "fouille"))
                    else "ready" if any(word in heading for word in ("prépar", "rôle", "objectif", "usage", "montrer"))
                    else "situation")
            pieces.append(f'<section class="scene-panel tone-{tone}">')
            opened = True
        pieces.append(f'<div class="markdown-block commentable-block {"has-comments" if any(first <= line_no <= last for line_no in marked) else ""}" '
                      f'data-line-start="{first}" data-line-end="{last}">{rendered}</div>')
    if opened:
        pieces.append('</section>')
    return ''.join(pieces)


def preparation_markdown(db, campaign_id, preparation_id):
    campaign = db.execute("SELECT language FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
    if campaign is None:
        raise ValueError("Unknown campaign")
    preparation = next((row for row in journey_view(db, campaign_id)[1] if row["id"] == preparation_id), None)
    if preparation is None:
        raise ValueError("Unknown preparation")
    lang = campaign["language"]
    return (f'# {t("prep.tag", lang)} #{preparation_id}\n\n'
            f'## {t("field.situation", lang)}\n\n{preparation["situation"]}\n\n'
            f'## {t("field.alternatives", lang)}\n\n{preparation["alternatives"]}\n\n'
            f'## {t("prep.based_on", lang)} #{preparation["fact_id"]}\n\n{preparation["fact"]}\n\n'
            f'## {t("proposal.tag", lang)} #{preparation["proposal_id"]}\n\n{preparation["proposal"]}\n')


def scenario_dossier_html(db, campaign_id, document_id):
    stats = dossier_stats(db, campaign_id, document_id)
    document = library_document(db, campaign_id, document_id)
    authored_count = db.execute("SELECT COUNT(*) FROM scenario_elements WHERE campaign_id=? AND document_id=?",
                                (campaign_id, document_id)).fetchone()[0]
    sections = db.execute("SELECT * FROM scenario_sections WHERE campaign_id=? AND document_id=? ORDER BY start_page",
                          (campaign_id, document_id)).fetchall()
    chapters = [row for row in sections if row["title"].startswith("CHAPITRE ")]
    summarized = sum(row["summary_status"] == "proposed" for row in chapters)
    source = f"/workspace/{campaign_id}?doc=library_documents:{document_id}"
    output = (f'<div class="dossier-status"><strong>{stats["pages"]}/{document["page_count"]} pages indexées</strong>'
              f'<span>{authored_count} fiches rédigées par l’agent · {stats["selected"]} repères extraits · {stats["pending"]} à revoir · {summarized}/{len(chapters)} chapitres synthétisés</span>'
              '<p>Fiches et repères proposés à partir du PDF privé. Rien ici n’est canonique. '
              'Les catégories et synthèses doivent être relues ; chaque lien ouvre la page et la ligne du texte source.</p></div>'
              f'<nav class="dossier-source"><a href="{source}&amp;page=1">Ouvrir le PDF source</a></nav>')
    labels = {"scene": "Scènes", "event": "Événements", "encounter": "Rencontres", "person": "Personnages", "place": "Lieux", "faction": "Factions", "item": "Objets", "creature": "Créatures", "heading": "Autres rubriques", "clue": "Indices et découvertes", "choice": "Choix et embranchements", "secret": "Secrets", "hook": "Accroches", "rule": "Règles"}
    for section in sections:
        counts = {row["status"]: row["n"] for row in db.execute(
            "SELECT status, COUNT(*) AS n FROM scenario_candidates WHERE section_id=? GROUP BY status", (section["id"],))}
        entries = db.execute("SELECT * FROM scenario_candidates WHERE section_id=? AND status='selected' ORDER BY pdf_page,line_number",
                             (section["id"],)).fetchall()
        authored = db.execute("SELECT * FROM scenario_elements WHERE section_id=? ORDER BY pdf_page,line_number,id",
                              (section["id"],)).fetchall()
        authored_cards = ''.join(
            f'<li><a href="{source}&amp;page={row["pdf_page"]}#L{row["line_number"]}">'
            f'<small>{esc(labels.get(row["kind"], row["kind"]))} · PDF p. {row["pdf_page"]}, ligne {row["line_number"]}</small>'
            f'<strong>{esc(row["title"])}</strong><span>{esc(row["body"])}</span>'
            f'<q>{esc(row["quote"])}</q></a></li>' for row in authored if row["kind"] != "scene")
        authored_scenes = {(row["pdf_page"], row["line_number"]): row for row in authored if row["kind"] == "scene"}
        scene_cards = ''
        for position, scene in enumerate(entries):
            if scene["kind"] != "scene":
                continue
            related = []
            for following in entries[position + 1:]:
                if following["kind"] == "scene":
                    break
                related.append(following)
            related_html = ''.join(
                f'<li><a href="{source}&amp;page={row["pdf_page"]}#L{row["line_number"]}">'
                f'<small>{esc(labels.get(row["category"] or row["kind"], row["kind"]))} · p. {row["pdf_page"]}</small>'
                f'<span>{esc(row["name"])}</span></a></li>' for row in related)
            authored_scene = authored_scenes.get((scene["pdf_page"], scene["line_number"]))
            scene_body = authored_scene["body"] if authored_scene else scene["evidence"]
            scene_cards += (f'<details class="dossier-scene"><summary>{esc(scene["name"])}'
                            f'<small>PDF p. {scene["pdf_page"]} · {len(related)} éléments liés</small></summary>'
                            f'<p class="dossier-note">{esc(scene["note"])}</p>'
                            f'<p>{esc(scene_body)}</p>'
                            f'<a class="dossier-scene-source" href="{source}&amp;page={scene["pdf_page"]}#L{scene["line_number"]}">Voir le passage source</a>'
                            f'<ul>{related_html}</ul></details>')
        groups = ''
        for kind, label in labels.items():
            if kind == "scene" and scene_cards:
                continue
            items = [row for row in entries if (row["kind"] == "heading" and row["category"] == kind)
                     or (row["kind"] == kind and (kind != "heading" or not row["category"]))]
            if not items:
                continue
            cards = ''.join(f'<li><a href="{source}&amp;page={row["pdf_page"]}#L{row["line_number"]}">'
                            f'<strong>{esc(row["name"])}</strong>'
                            f'<span class="dossier-note">{esc(row["note"])}</span>'
                            f'<span>{esc(row["evidence"])}</span>'
                            f'<small>PDF p. {row["pdf_page"]} · ligne {row["line_number"]}</small></a></li>'
                            for row in items)
            groups += f'<section class="dossier-kind"><h4>{label} <span>{len(items)}</span></h4><ul>{cards}</ul></section>'
        overview = (f'<div class="dossier-overview"><small>Synthèse proposée par l’agent · à vérifier dans les sources</small>'
                    f'<p>{esc(section["summary"])}</p></div>') if section["summary_status"] == "proposed" else ''
        if scene_cards:
            groups = f'<section class="dossier-kind"><h4>Parcours par scène</h4>{scene_cards}</section>' + groups
        if authored_cards:
            groups = f'<section class="dossier-kind dossier-authored"><h4>Fiches rédigées dans le chat <span>{sum(row["kind"] != "scene" for row in authored)}</span></h4><ul>{authored_cards}</ul></section>' + groups
        output += (f'<details class="dossier-section" {"open" if section["title"].startswith("CHAPITRE 1") else ""}>'
                   f'<summary><strong>{esc(section["title"])}</strong><span>p. {section["start_page"]}–{section["end_page"]} · '
                   f'{counts.get("selected", 0)} retenus · {counts.get("pending", 0)} en attente</span></summary>'
                   f'{overview}'
                   f'{groups or "<p>Aucun élément retenu à ce stade.</p>"}</details>')
    gaps = db.execute("SELECT pdf_page,quality FROM library_pages WHERE campaign_id=? AND document_id=? AND quality!='text' ORDER BY pdf_page",
                      (campaign_id, document_id)).fetchall()
    if gaps:
        links = ' · '.join(f'<a href="{source}&amp;page={row["pdf_page"]}">p. {row["pdf_page"]} ({esc(row["quality"])})</a>' for row in gaps)
        output += f'<p class="dossier-gaps">Extraction à vérifier : {links}</p>'
    return output


def render_workspace(db, campaign_id, selected="", page=1, library_query="", comment_mode=False, focus=""):
    campaign, sources, observations, facts = campaign_view(db, campaign_id)
    bible = campaign_bible(db, campaign_id)
    bible_rows = bible_comments(db, campaign_id) if bible else []
    bible_counts = Counter(row["target_key"] for row in bible_rows)
    proposals, preparations, events, corrections = journey_view(db, campaign_id)
    language = campaign["language"]
    tr = lambda key: esc(t(key, language))
    turns = agent_turns(db, campaign_id)
    pending = bool(turns and turns[-1]["status"] == "running")
    documents = []
    for item in dossier_documents(db, campaign_id):
        _, content, _ = dossier_document(db, campaign_id, item["id"])
        documents.append(("campaign_files", item["id"], t("workspace.campaign_docs", language),
                          document_title(item["path"], content), content))
    for item in library_documents(db, campaign_id):
        if db.execute("SELECT 1 FROM scenario_sections WHERE campaign_id=? AND document_id=? LIMIT 1", (campaign_id, item["id"])).fetchone():
            documents.append(("scenario_dossiers", item["id"], "Dossier", item["title"], []))
        documents.append(("library_documents", item["id"], t("workspace.library", language), item["title"], None))
    for file_id, relative in enumerate(PRODUCT_DOCS, 1):
        _, content = product_doc(file_id)
        documents.append(("product_docs", file_id, t("workspace.product_docs", language), relative, content))
    for item in preparations:
        documents.append(("preparations", item["id"], t("workspace.preparation", language), item["situation"],
                          [("field.situation", item["situation"], True), ("field.alternatives", item["alternatives"], True),
                           ("prep.based_on", item["fact"], False), ("proposal.tag", item["proposal"], False)]))
    for item in facts:
        documents.append(("facts", item["id"], t("workspace.fact", language), item["text"],
                          [("field.canonical_fact", item["text"], True), ("label.decision", item["instruction"], False),
                           ("label.observation", item["observation"], False),
                           ("label.source", f"{item['source_title']} · {item['locator']}", False)]))
    for item in proposals:
        documents.append(("proposals", item["id"], t("workspace.proposal", language), item["text"],
                          [("field.proposal", item["text"], True),
                           ("label.source", f"{item['source_title']} · {item['locator']}", False)]))
    for item in sources:
        documents.append(("sources", item["id"], t("workspace.source", language), item["title"],
                          [("field.description", item["note"], True), ("label.locator", item["locator"], True)]))
    for item in events:
        documents.append(("simulated_events", item["id"], t("workspace.simulation", language), item["player_action"],
                          [("field.player_action", item["player_action"], True), ("field.ruling", item["ruling"], True),
                           ("event.consequence", item["consequence"] or t("event.pending", language), False)]))
    campaign_docs = [doc for doc in documents if doc[0] != "product_docs"]
    campaign_default = next((doc for doc in campaign_docs if doc[0] == "campaign_files"), next((doc for doc in campaign_docs if doc[0] == "scenario_dossiers"), next((doc for doc in campaign_docs if doc[0] == "preparations"), campaign_docs[0] if campaign_docs else None)))
    choice = (next((doc for doc in documents if f"{doc[0]}:{doc[1]}" == selected), None)
              if selected or bible else campaign_default)
    product_view = choice is not None and choice[0] == "product_docs"
    groups = [("campaign_files", "workspace.campaign_docs"), ("scenario_dossiers", "workspace.dossier"), ("library_documents", "workspace.library"), ("preparations", "workspace.preparation"), ("facts", "workspace.fact"),
              ("proposals", "workspace.proposal"), ("sources", "workspace.source"),
              ("simulated_events", "workspace.simulation")]
    def doc_link(doc):
        title = Path(doc[3]).name if doc[0] == "product_docs" else doc[3]
        return f'<a class="doc-link {"active" if choice == doc else ""}" href="/workspace/{campaign_id}?doc={doc[0]}:{doc[1]}" title="{esc(doc[3])}"><span class="doc-name">{esc(title)}</span></a>'
    def folder_label(folder):
        key = "workspace.folder_" + folder
        label = t(key, language)
        return esc(folder.replace("-", " ").title() if label == key else label)
    if product_view:
        sidebar = '<p class="tree-intro">' + tr("workspace.product_explain") + '</p>' + ''.join(doc_link(doc) for doc in documents if doc[0] == "product_docs")
    else:
        sidebar = (f'<a class="bible-nav {"active" if not selected else ""}" href="/workspace/{campaign_id}">'
                   f'<span>◈</span> {tr("bible.nav")}</a>') if bible else ""
        for kind, label in groups:
            matching = [doc for doc in campaign_docs if doc[0] == kind]
            if not matching:
                continue
            if kind == "campaign_files":
                paths = {row["id"]: row["path"] for row in dossier_documents(db, campaign_id)}
                folders = sorted({Path(paths[doc[1]]).parent.as_posix() for doc in matching if "/" in paths[doc[1]]})
                links = "".join(doc_link(doc) for doc in matching if "/" not in paths[doc[1]])
                links += "".join(
                    f'<details class="tree-subgroup" {"open" if choice and choice[0] == kind and Path(paths[choice[1]]).parent.as_posix() == folder else ""}>'
                    f'<summary>{folder_label(folder)} <span>{sum(Path(paths[doc[1]]).parent.as_posix() == folder for doc in matching)}</span></summary>'
                    + "".join(doc_link(doc) for doc in matching if Path(paths[doc[1]]).parent.as_posix() == folder)
                    + '</details>' for folder in folders)
            else:
                links = "".join(doc_link(doc) for doc in matching)
            sidebar += f'<details class="tree-group" {"open" if choice and choice[0] == kind else ""}><summary>{tr(label)} <span>{len(matching)}</span></summary>{links}</details>'
        sidebar += (f'<details class="library-import"><summary>{tr("workspace.import_pdf")}</summary>'
                    f'<form method="post" action="/campaign/{campaign_id}/import-pdf">'
                    f'<label for="pdf-path">{tr("workspace.pdf_path")}</label>'
                    f'<input id="pdf-path" name="path" required maxlength="1000" placeholder="/…/scenario.pdf">'
                    f'<label for="pdf-title">{tr("field.title")}</label><input id="pdf-title" name="title" maxlength="200">'
                    f'<p>{tr("workspace.library_private_note")}</p><button>{tr("workspace.import_pdf")}</button></form></details>')
    campaign_tab = f'/workspace/{campaign_id}' + (f'?doc={campaign_default[0]}:{campaign_default[1]}' if campaign_default and not bible else '')
    tabs = (f'<div class="sidebar-tabs"><a class="{"active" if not product_view else ""}" href="{campaign_tab}">{tr("workspace.campaign_area")}</a>'
            f'<a class="{"active" if product_view else ""}" href="/workspace/{campaign_id}?doc=product_docs:1">{tr("workspace.product_area")}</a></div>')
    pdf_page = None
    if choice:
        kind, item_id, label, title, sections = choice
        pdf_page = library_page(db, campaign_id, item_id, page) if kind == "library_documents" else None
        comment_kind = "library_pages" if pdf_page else kind
        comment_target_id = pdf_page["id"] if pdf_page else item_id
        comments = [] if kind == "scenario_dossiers" else comments_for(db, campaign_id, comment_kind, comment_target_id)
        marked = {number for row in comments if row["line_start"] for number in range(row["line_start"], row["line_end"] + 1)}
        if pdf_page:
            section_html = "".join(
                f'<div id="L{number}" class="doc-line commentable-block {"has-comments" if number in marked else ""}" data-line-start="{number}" data-line-end="{number}">'
                f'<button class="line-number" type="button" data-line="{number}" aria-label="{tr("workspace.extracted_line")} {number}">{number}</button>'
                f'<div class="block-content">{esc(line)}</div></div>'
                for number, line in enumerate(pdf_page["text"].splitlines() or [""], 1)
            )
            section_html = f'<div class="pdf-page-text">{section_html}</div>'
        elif kind in ("product_docs", "campaign_files"):
            rendered_source = linked_markdown(db, campaign_id, item_id, sections) if kind == "campaign_files" else sections
            section_html = '<div class="markdown-rendered">' + dossier_blocks(rendered_source, marked, kind == "campaign_files", campaign_id if kind == "campaign_files" else None, db) + '</div>'
            if kind == "campaign_files":
                related = backlinks(db, campaign_id, item_id)
                section_html += (f'<section class="dossier-backlinks"><h3>{tr("workspace.linked_from")}</h3>'
                                 + (''.join(f'<a href="/workspace/{campaign_id}?doc=campaign_files:{other}">{esc(name)}</a>' for other, name in related)
                                    or f'<p>{tr("workspace.no_backlinks")}</p>') + '</section>')
        else:
            section_html, number = "", 1
            for key, value, selectable in sections:
                if selectable:
                    lines = str(value).splitlines() or [""]
                    content = f'<div class="record-source">{record_blocks(value, number - 1, marked)}</div>'
                    number += len(lines)
                else:
                    content = f'<p>{esc(value)}</p>'
                section_html += f'<section class="doc-section"><h3>{tr(key)}</h3>{content}</section>'
        database_file = Path(db.execute("PRAGMA database_list").fetchone()["file"])
        short_path = str(database_file).replace(str(Path.home()), "~", 1)
        if pdf_page:
            document = library_document(db, campaign_id, item_id)
            counts = {row["quality"]: row["count"] for row in db.execute(
                "SELECT quality, count(*) AS count FROM library_pages WHERE campaign_id=? AND document_id=? GROUP BY quality",
                (campaign_id, item_id))}
            base = f"/workspace/{campaign_id}?doc=library_documents:{item_id}"
            search_suffix = f"&q={url_quote(library_query)}" if library_query else ""
            previous = f'<a href="{base}&page={page - 1}{search_suffix}">{tr("workspace.previous_page")}</a>' if page > 1 else ""
            following = f'<a href="{base}&page={page + 1}{search_suffix}">{tr("workspace.next_page")}</a>' if page < document["page_count"] else ""
            pager = (f'<nav class="pdf-pager" aria-label="{tr("workspace.pdf_pages")}">{previous}'
                     f'<strong>{tr("workspace.pdf_page")} {page} / {document["page_count"]}</strong>{following}</nav>')
            results = ""
            if library_query:
                count, matches = library_search(db, campaign_id, item_id, library_query)
                links = "".join(f'<a href="{base}&page={number}{search_suffix}"><strong>{tr("workspace.pdf_page")} {number}</strong><span>{esc(excerpt)}</span></a>'
                                for number, excerpt in matches)
                results = (f'<div class="pdf-results"><strong>{esc(t("workspace.search_results", language, count=count))}</strong>'
                           f'{links or f"<p>{tr("workspace.no_search_results")}</p>"}</div>')
            search = (f'<form class="pdf-search" method="get" action="/workspace/{campaign_id}">'
                      f'<input type="hidden" name="doc" value="library_documents:{item_id}">'
                      f'<label for="pdf-query">{tr("workspace.library_search")}</label>'
                      f'<div><input id="pdf-query" name="q" value="{esc(library_query)}" maxlength="100">'
                      f'<button>{tr("action.search")}</button></div></form>')
            section_html = search + results + pager + section_html + pager
            storage = (f'<details class="source-path"><summary>{tr("workspace.source_not_canon")} · {tr("workspace.source_file")}</summary>'
                       f'<code>{esc(document["source_path"])}</code></details>'
                       f'<span>{tr("workspace.extraction_quality")}: {counts.get("text", 0)} / {document["page_count"]} '
                       f'· {tr("workspace.extraction_" + pdf_page["quality"])} · pdftotext</span>')
            draft_review_html = ""
        elif kind == "product_docs":
            storage = f'<span>{tr("workspace.product_file")}: {esc(title)}</span>'
            review = draft_file_review(campaign_id, item_id)
            if review:
                action = (f'<form method="post" action="/campaign/{campaign_id}/apply-draft"><input type="hidden" name="file_id" value="{item_id}">'
                          f'<button>{tr("workspace.apply_draft")}</button></form>') if review["status"] == "ready" else ''
                draft_review_html = (f'<details class="file-review" open><summary>{tr("workspace.file_review")} · {esc(review["relative"])}</summary>'
                                     f'<p>{tr("workspace.draft_" + review["status"])}</p><pre>{esc(review["diff"])}</pre>{action}</details>')
            else:
                draft_review_html = ""
        else:
            if kind == "preparations":
                prep_review = preparation_draft_review(db, campaign_id, item_id)
                if prep_review is None:
                    draft_review_html = (f'<form class="prep-draft-start" method="post" action="/campaign/{campaign_id}/start-preparation-draft">'
                                         f'<input type="hidden" name="preparation_id" value="{item_id}"><button>{tr("workspace.start_prep_draft")}</button></form>')
                else:
                    action = (f'<form method="post" action="/campaign/{campaign_id}/apply-preparation-draft">'
                              f'<input type="hidden" name="preparation_id" value="{item_id}"><button>{tr("workspace.apply_prep_draft")}</button></form>') if prep_review["status"] == "ready" else ''
                    if prep_review["status"] == "applied":
                        action = (f'<form method="post" action="/campaign/{campaign_id}/restart-preparation-draft">'
                                  f'<input type="hidden" name="preparation_id" value="{item_id}"><button>{tr("workspace.restart_prep_draft")}</button></form>')
                    prep_diff_html = f'<pre>{esc(prep_review["diff"])}</pre>' if prep_review["diff"] else ''
                    draft_review_html = (f'<details class="file-review prep-review" open><summary>{tr("workspace.prep_draft_review")}</summary>'
                                         f'<p>{tr("workspace.draft_" + prep_review["status"])}</p>'
                                         f'<code>{esc(prep_review["path"])}</code>'
                                         f'{prep_diff_html}{action}</details>')
            else:
                draft_review_html = ""
            export = (f'<span class="export-actions"><a href="/campaign/{campaign_id}/preparation/{item_id}.md" download="preparation-{item_id}.md">{tr("workspace.export_md")}</a>'
                      f'<small>{tr("workspace.export_copy")}</small></span>') if kind == "preparations" else ''
            storage = f'<span>{tr("workspace.campaign_storage")}: <code title="{esc(database_file)}">{esc(short_path)}</code></span>{export}'
        if kind == "campaign_files":
            file_row, _, file_path = dossier_document(db, campaign_id, item_id)
            sheet_review = campaign_file_draft_review(db, campaign_id, item_id)
            if sheet_review is None:
                draft_review_html = (f'<form class="sheet-draft-start" method="post" action="/campaign/{campaign_id}/start-campaign-file-draft">'
                                     f'<input type="hidden" name="file_id" value="{item_id}"><button>{tr("workspace.start_sheet_draft")}</button></form>')
            else:
                action = (f'<form method="post" action="/campaign/{campaign_id}/apply-campaign-file-draft">'
                          f'<input type="hidden" name="file_id" value="{item_id}"><button>{tr("workspace.apply_sheet_draft")}</button></form>') if sheet_review["status"] == "ready" else ""
                if sheet_review["status"] == "applied":
                    action = (f'<form method="post" action="/campaign/{campaign_id}/restart-campaign-file-draft">'
                              f'<input type="hidden" name="file_id" value="{item_id}"><button>{tr("workspace.restart_sheet_draft")}</button></form>')
                problems = "".join(f'<li>{esc(problem)}</li>' for problem in sheet_review["problems"])
                status_label = "workspace.sheet_draft_invalid" if sheet_review["status"] == "invalid" else "workspace.draft_" + sheet_review["status"]
                draft_review_html = (f'<details class="file-review sheet-draft-review" {"open" if sheet_review["status"] != "unchanged" else ""}>'
                                     f'<summary>{tr("workspace.sheet_draft_review")} · {tr(status_label)}</summary>'
                                     f'<p>{tr("workspace.sheet_draft_hint")}</p><code>{esc(sheet_review["path"])}</code>'
                                     f'{f"<ul>{problems}</ul>" if problems else ""}'
                                     f'{f"<pre>{esc(sheet_review["diff"])}</pre>" if sheet_review["diff"] else ""}{action}</details>')
            sheet_type = file_row["path"].split("/", 1)[0] if "/" in file_row["path"] else "overview"
            labels = {"personnages": "sheet.person", "people": "sheet.person", "lieux": "sheet.place",
                      "places": "sheet.place", "factions": "sheet.faction", "scenes": "sheet.scene", "overview": "sheet.overview"}
            sheet_label = tr(labels.get(sheet_type, "sheet.other"))
            storage = (f'<details class="sheet-storage"><summary>{tr("sheet.storage")}</summary>'
                       f'<code>{esc(file_path)}</code></details>')
        if kind == "scenario_dossiers":
            section_html = scenario_dossier_html(db, campaign_id, item_id)
            storage = f'<span>Dossier de travail · source privée · {tr("workspace.campaign_storage")}: {esc(short_path)}</span>'
        heading = '' if kind == 'campaign_files' else f'<h2>{esc(title)}</h2>'
        kicker = f'<div class="sheet-kicker"><span>{sheet_label}</span><span>{tr("sheet.proposal")}</span></div>' if kind == "campaign_files" else ""
        css_type = {"people": "personnages", "places": "lieux"}.get(sheet_type, sheet_type) if kind == "campaign_files" else ""
        sheet_class = (f'campaign-file sheet-{css_type} '
                       f'{"sheet-timeline" if file_row["path"] == "04-Chronologie.md" else ""}'
                       if kind == "campaign_files" else "")
        body = (f'{kicker}{draft_review_html}{section_html}<div class="document-storage">{storage}</div>'
                if kind == "campaign_files" else f'{heading}<div class="document-storage">{storage}</div>{draft_review_html}{section_html}')
        doc_html = f'<div class="document-top"><span>{esc(label)} #{item_id}</span><span>{tr("workspace.private")}</span></div><article class="document {sheet_class}" id="document">{body}</article>'
        def comment_row(row):
            anchor = f'L{row["line_start"]}' + (f'–{row["line_end"]}' if row["line_end"] != row["line_start"] else '') if row['line_start'] else ''
            quote = f'<blockquote data-quote="{esc(row["quote"])}" data-line="{row["line_start"] or ""}" data-offset="{row["char_offset"] if row["char_offset"] is not None else ""}" tabindex="0" title="{tr("workspace.locate_quote")}">{esc(row["quote"])}</blockquote>' if row['quote'] else ''
            source_quote = ' '.join(row['quote'].split())
            stale = f'<p class="muted">{tr("workspace.stale_quote")}</p>' if kind in ('product_docs', 'campaign_files') and row['quote'] and source_quote not in ' '.join(sections.split()) and source_quote not in visible_text(sections) else ''
            ask = (f'<button type="button" class="comment-to-chat" data-comment-id="{row["id"]}" '
                   f'data-quote="{esc(row["quote"])}" data-comment="{esc(row["body"])}" {"disabled" if pending else ""}>'
                   f'{tr("workspace.comment_to_chat")}</button>')
            return f'<div class="comment"><small>#{row["id"]} · {esc(anchor)} · {esc(row["created_at"])}</small>{quote}{stale}<p>{esc(row["body"])}</p>{ask}</div>'
        comment_html = "".join(comment_row(row) for row in comments)
        review_html = f'''<p class="muted">{tr("workspace.select_lines")}</p><div class="comments-list">{comment_html or f'<p class="muted">{tr("workspace.no_comments")}</p>'}</div>'''
        form_html = f'''<form method="post" action="/campaign/{campaign_id}/comment" id="comment-form" hidden>
            <input type="hidden" name="target_kind" value="{comment_kind}"><input type="hidden" name="target_id" value="{comment_target_id}">
            <input type="hidden" name="line_start" id="line-start"><input type="hidden" name="line_end" id="line-end"><input type="hidden" name="char_offset" id="char-offset">
            <input type="hidden" name="quote" id="quote"><strong id="selected-lines"></strong><blockquote id="selected-quote"></blockquote>
            <label for="comment">{tr('field.comment')}</label><textarea id="comment" name="body" maxlength="2000" rows="4" required></textarea>
            <button>{tr('action.add_comment')}</button>
          </form>'''
        if kind == "scenario_dossiers":
            form_html = ""
            review_html = '<p class="muted">Ouvrez une source liée pour commenter un passage exact.</p>'
        selected_key = f"{kind}:{item_id}"
    else:
        doc_html = bible_html(db, campaign_id, bible, facts, bible_counts, language) if bible else f'<div class="empty-document"><h2>{tr("workspace.no_documents")}</h2><p>{tr("workspace.create_hint")}</p></div>'
        if bible:
            current = bible_element_texts(db, campaign_id)
            notes = ""
            for row in bible_rows:
                stale = f'<p class="bible-stale">{tr("bible.changed")}</p>' if current.get(row["target_key"]) != row["quote"] else ""
                notes += (f'<div class="comment bible-comment"><button type="button" class="bible-comment-locate" data-bible-locate="{esc(row["target_key"])}">'
                          f'<small>#{row["id"]} · {esc(row["created_at"])}</small><strong>{esc(row["quote"])}</strong></button>'
                          f'{stale}<p>{esc(row["body"])}</p><button type="button" class="comment-to-chat" data-comment-id="{row["id"]}" '
                          f'data-quote="{esc(row["quote"])}" data-comment="{esc(row["body"])}">{tr("workspace.comment_to_chat")}</button></div>')
            form = (f'<form id="bible-comment-form" method="post" action="/campaign/{campaign_id}/bible-comment" data-focus="{esc(focus)}" data-selected-label="{tr("bible.selected")}" hidden>'
                    f'<input type="hidden" name="target_key" id="bible-target-key"><strong id="bible-target-label"></strong>'
                    f'<p id="bible-target-quote"></p><label for="bible-comment-body">{tr("field.comment")}</label>'
                    f'<textarea id="bible-comment-body" name="body" maxlength="2000" rows="5" required></textarea>'
                    f'<button>{tr("action.add_comment")}</button></form>')
            empty_notes = f'<p class="muted">{tr("bible.empty_comments")}</p>'
            review_html = (f'<p class="muted">{tr("bible.review_hint")}</p>'
                           f'{form}<div class="comments-list">{notes or empty_notes}</div>')
        else:
            review_html = f'<p class="muted">{tr("workspace.no_document_comment")}</p>'
        form_html = ""
        selected_key = ""
    diff = draft_diff(campaign_id)
    draft_html = f'<details class="draft-diff"><summary>{tr("workspace.draft_changes")}</summary><pre>{esc(diff)}</pre></details>' if diff else ''
    def turn_html(row):
        content = render_markdown(row["response"]) if row["response"] else f'<p>{tr("workspace.running")}</p>'
        reply = (f'<div class="markdown-response streaming-response" data-turn-id="{row["id"]}">{content}</div>'
                 if row["status"] == "running" else f'<div class="markdown-response">{content}</div>')
        provider_name = "Claude Code" if row["provider"] == "claude" else "Codex"
        return (f'<div class="message"><div class="message-head">{tr("workspace.you")} '
                f'<small>{esc(row["created_at"])}</small></div><p>{esc(row["prompt"])}</p></div>'
                f'<div class="message assistant {"failed" if row["status"] == "error" else ""}">'
                f'<div class="message-head">{esc(provider_name)} <small>{tr("workspace.status_" + row["status"])}</small></div>'
                f'{reply}</div>')
    messages = "".join(turn_html(row) for row in turns)
    if not messages:
        messages = f'<div class="empty-chat"><h2>{tr("workspace.chat_start")}</h2><p>{tr("workspace.chat_hint")}</p></div>'
    pending_message = (f'<div class="pending-message" role="status" data-started="{esc(turns[-1]["created_at"])}Z">'
                       f'<strong>{tr("workspace.running")}</strong><span>{tr("workspace.elapsed")} '
                       f'<time class="pending-elapsed" aria-live="off">0:00</time></span>'
                       f'<p>{tr("workspace.write_next")}</p></div>') if pending else ''
    provider = "codex"
    provider_options = "".join(f'<option value="{name}" {"selected" if name == provider else ""}>{esc(label)}</option>' for name, label in (("codex", "Codex"), ("claude", "Claude Code")))
    playbooks = ("explore", "revise", "prepare", "conflict")
    playbook_options = "".join(f'<option value="{name}" data-prompt="{tr("workspace.playbook_" + name + "_prompt")}">{tr("workspace.playbook_" + name)}</option>' for name in playbooks)
    skills = available_skills()
    skill_options = "".join(f'<option value="{esc(name)}" data-description="{esc(description)}" label="{esc(origin)} · {esc(description[:70])}"></option>' for name, description, origin in skills)
    share_private = bool(pdf_page or (choice and choice[0] in ("scenario_dossiers", "campaign_files")))
    share_label = ("workspace.include_sheet" if choice and choice[0] == "campaign_files" else
                   "workspace.include_dossier" if choice and choice[0] == "scenario_dossiers" else "workspace.include_pdf_page")
    pdf_share = (f'<label class="pdf-share"><input type="checkbox" name="include_page" value="yes">'
                 f'{tr(share_label)}</label>'
                 + (f'<small class="draft-access-note">{tr("workspace.sheet_draft_access")}</small>'
                    if choice and choice[0] == "campaign_files" and sheet_review is not None else "")) if share_private else ""
    terminal = (f'{turns[-1]["provider"]} · {t("workspace.status_" + turns[-1]["status"], language)} · session {turns[-1]["session_id"] or "—"}' if turns else t("workspace.cli_idle", language))
    if bible and not selected:
        document_control = (f'<a class="comment-mode-toggle" href="/workspace/{campaign_id}{"" if comment_mode else "?comment=1"}">'
                            f'{tr("bible.done" if comment_mode else "bible.review")} <span>{len(bible_rows)}</span></a>')
    elif choice and choice[0] == "campaign_files":
        document_control = (f'<button type="button" class="sheet-review-toggle" id="sheet-review-toggle" aria-expanded="false">'
                            f'{tr("workspace.comments")} <span>{len(comments)}</span></button>')
    else:
        document_control = f'<span>{tr("workspace.review")}</span>'
    return f'''<!doctype html><html lang="{locale(language)}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(campaign['name'])} · {tr('workspace.title')}</title><link rel="stylesheet" href="/assets/workspace.css"></head>
      <body><div class="app-shell {"bible-mode" if bible and not selected else ""} {"comment-mode" if bible and not selected and comment_mode else ""} {"sheet-mode" if choice and choice[0] == "campaign_files" else ""}">
        <aside class="sidebar"><div class="brand"><a href="/">{tr('app.title')}</a><strong>{esc(campaign['name'])}</strong><span>{tr('workspace.private')}</span></div>
          {tabs}<nav aria-label="{tr('workspace.documents')}">{sidebar or f'<p class="sidebar-empty">{tr("workspace.no_documents")}</p>'}</nav>
          <a class="advanced-link" href="/campaign/{campaign_id}">{tr('workspace.records')}</a>
        </aside>
        <section class="conversation" id="conversation"><div class="panel-head"><h1>{tr('workspace.conversation')}</h1><a class="mobile-jump" href="#document-panel">{tr('workspace.see_document')}</a><span>{tr('workspace.cli_draft')}</span></div>
          <div class="messages" id="messages">{messages}{draft_html}</div>
          <form class="composer" method="post" action="/campaign/{campaign_id}/chat" id="chat-form" data-pending="{int(pending)}" data-status-url="/campaign/{campaign_id}/chat-progress" data-turn-id="{turns[-1]["id"] if turns else ""}" data-comment-instruction="{tr('workspace.comment_prompt')}" data-too-long="{tr('workspace.prompt_too_long')}">
            {pending_message}
            <input type="hidden" name="doc" value="{esc(selected_key)}"><input type="hidden" name="page" value="{page if pdf_page else 1}">
            <label for="playbook">{tr('workspace.playbook')}</label><select id="playbook"><option value="">{tr('workspace.playbook_none')}</option>{playbook_options}</select>
            <details class="skill-picker" data-instruction="{tr('workspace.skill_instruction')}"><summary>{tr('workspace.skills')} ({len(skills)})</summary><label for="skill-search">{tr('workspace.skill_search')}</label><input id="skill-search" list="skill-options" autocomplete="off" placeholder="{tr('workspace.skill_placeholder')}"><datalist id="skill-options">{skill_options}</datalist><p id="skill-description" class="composer-note">{tr('workspace.skill_hint')}</p><button type="button" id="add-skill">{tr('workspace.add_skill')}</button></details>
            <label for="prompt">{tr('field.message')}</label><textarea id="prompt" name="prompt" rows="3" maxlength="4000" required placeholder="{tr('workspace.prompt_hint')}"></textarea>
            {pdf_share}
            <div class="composer-actions"><select name="provider" aria-label="{tr('workspace.provider')}">{provider_options}</select><button{" disabled" if pending else ""}>{tr('workspace.send')}</button></div>
            <p class="composer-note">{tr('workspace.send_notice')}</p>
          </form>
        </section>
        <section class="document-panel" id="document-panel"><div class="panel-head"><h1>{tr("bible.title") if bible and not selected else tr('workspace.documents')}</h1><a class="mobile-jump" href="#conversation">{tr('workspace.see_chat')}</a>{document_control}</div><div class="document-layout"><div class="document-scroll">{doc_html}{form_html}</div><aside class="review"><h2>{tr('workspace.comments')}</h2>{review_html}</aside></div></section>
        <footer class="terminal"><span>{tr('workspace.terminal')}</span><code>{esc(terminal)}</code></footer>
      </div><script src="/assets/workspace.js" defer></script></body></html>'''


def document_context(db, campaign_id, selected, page=1, include_text=True):
    try:
        kind, raw_id = selected.split(":", 1)
        item_id = int(raw_id)
        if kind == "scenario_dossiers":
            document = library_document(db, campaign_id, item_id)
            intro = f"Selected private scenario dossier: {document['title']}. Its contents are source-derived proposals, not canon. "
            if not include_text:
                return intro + "The dossier text was not shared.\n\n"
            sections = db.execute("SELECT title,summary FROM scenario_sections WHERE campaign_id=? AND document_id=? ORDER BY start_page",
                                  (campaign_id, item_id)).fetchall()
            cards = db.execute("""SELECT kind,name,pdf_page,line_number,evidence,note FROM scenario_candidates
                WHERE campaign_id=? AND document_id=? AND status='selected' ORDER BY pdf_page,line_number""",
                (campaign_id, item_id)).fetchall()
            authored = db.execute("""SELECT kind,title,body,pdf_page,line_number FROM scenario_elements
                WHERE campaign_id=? AND document_id=? ORDER BY pdf_page,line_number""",
                (campaign_id, item_id)).fetchall()
            content = "\n".join(f"{row['title']}: {row['summary']}" for row in sections if row['summary'])
            content += "\n" + "\n".join(f"{row['kind']} {row['title']} PDF p.{row['pdf_page']} line {row['line_number']}: {row['body']}" for row in authored)
            content += "\n" + "\n".join(f"{row['kind']} PDF p.{row['pdf_page']} line {row['line_number']}: {row['note']} | source: {row['evidence']}" for row in cards)
            return intro + "\n" + content[:16000] + ("\n[Dossier truncated]" if len(content) > 16000 else "") + "\n\n"
        if kind == "campaign_files":
            row, content, _ = dossier_document(db, campaign_id, item_id)
            intro = f"Selected private campaign preparation document: {row['path']}. Proposed preparation, not canon. "
            if not include_text:
                return intro + "Its contents were not shared.\n\n"
            comments = comments_for(db, campaign_id, kind, item_id)
            review = "\n".join(f"Comment on lines {comment['line_start']}-{comment['line_end']} '{comment['quote']}': {comment['body']}" for comment in comments)
            return intro + "\n" + content[:16000] + "\nReview comments:\n" + (review or "None") + "\n\n"
        if kind == "library_documents":
            document = library_document(db, campaign_id, item_id)
            source_page = library_page(db, campaign_id, item_id, page)
            if not include_text:
                return (f"Selected private PDF source: {document['title']}, PDF page {page}/{document['page_count']}. "
                        "The page text and comments were not shared. This source is not campaign canon.\n\n")
            comments = comments_for(db, campaign_id, "library_pages", source_page["id"])
            review = "\n".join(f"Comment on extracted lines {comment['line_start']}-{comment['line_end']} '{comment['quote']}': {comment['body']}" for comment in comments)
            content = source_page["text"][:16000]
            suffix = "\n[Page text truncated]" if len(source_page["text"]) > 16000 else ""
            return (f"Selected private PDF source: {document['title']}, PDF page {page}/{document['page_count']}. "
                    f"Extracted text is source material, not campaign canon. Extraction quality: {source_page['quality']}.\n"
                    f"Page text:\n{content}{suffix}\nReview comments:\n{review or 'None'}\n\n")
        if kind == "product_docs":
            relative, _ = product_doc(item_id)
            comments = comments_for(db, campaign_id, kind, item_id)
            review = "\n".join(f"Comment on lines {comment['line_start']}-{comment['line_end']} '{comment['quote']}': {comment['body']}" for comment in comments)
            return f"Selected product document: {relative}. Read it from the repository if needed.\nReview comments:\n{review or 'None'}\n\n"
        columns = COMMENT_TARGETS[kind]
    except DomainError:
        raise
    except (ValueError, KeyError):
        return ""
    comments = comments_for(db, campaign_id, kind, item_id)
    row = db.execute(f"SELECT {', '.join(columns)} FROM {kind} WHERE id=? AND campaign_id=?", (item_id, campaign_id)).fetchone()
    content = "\n".join(f"{name}: {row[name]}" for name in columns)
    review = "\n".join(f"Comment on lines {comment['line_start']}-{comment['line_end']} '{comment['quote']}': {comment['body']}" for comment in comments)
    return f"Selected document ({kind} #{item_id}):\n{content}\nReview comments:\n{review or 'None'}\n\n"
