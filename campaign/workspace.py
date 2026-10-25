"""Campaign conversation and document review workspace."""

import html
from pathlib import Path

from .agent_cli import draft_diff, draft_file_review
from .i18n import locale, t
from .markdown import render_blocks, visible_text
from .prep_drafts import preparation_draft_review
from .skills import available_skills
from .store import (COMMENT_TARGETS, PRODUCT_DOCS, agent_turns, campaign_view,
                    comments_for, journey_view, product_doc)


def esc(value):
    return html.escape(str(value), quote=True)


def record_blocks(value, offset, marked):
    return "".join(
        f'<div class="doc-line commentable-block {"has-comments" if any(start <= line <= end for line in marked) else ""}" data-line-start="{start}" data-line-end="{end}">'
        f'<button class="line-number" type="button" data-line="{start}" aria-label="Line {start}">{start}</button>'
        f'<div class="block-content">{rendered}</div></div>'
        for first, last, rendered in render_blocks(str(value))
        for start, end in ((offset + first, offset + last),)
    )


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


def render_workspace(db, campaign_id, selected=""):
    campaign, sources, observations, facts = campaign_view(db, campaign_id)
    proposals, preparations, events, corrections = journey_view(db, campaign_id)
    language = campaign["language"]
    tr = lambda key: esc(t(key, language))
    documents = []
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
    campaign_default = next((doc for doc in campaign_docs if doc[0] == "preparations"), campaign_docs[0] if campaign_docs else None)
    choice = next((doc for doc in documents if f"{doc[0]}:{doc[1]}" == selected), None) or campaign_default
    product_view = choice is not None and choice[0] == "product_docs"
    groups = [("preparations", "workspace.preparation"), ("facts", "workspace.fact"),
              ("proposals", "workspace.proposal"), ("sources", "workspace.source"),
              ("simulated_events", "workspace.simulation")]
    def doc_link(doc):
        title = Path(doc[3]).name if doc[0] == "product_docs" else doc[3]
        return f'<a class="doc-link {"active" if choice == doc else ""}" href="/workspace/{campaign_id}?doc={doc[0]}:{doc[1]}" title="{esc(doc[3])}"><span class="doc-name">{esc(title)}</span></a>'
    if product_view:
        sidebar = '<p class="tree-intro">' + tr("workspace.product_explain") + '</p>' + ''.join(doc_link(doc) for doc in documents if doc[0] == "product_docs")
    else:
        sidebar = "".join(
            f'<details class="tree-group" {"open" if choice and choice[0] == kind else ""}><summary>{tr(label)} <span>{sum(doc[0] == kind for doc in campaign_docs)}</span></summary>'
            + "".join(doc_link(doc) for doc in campaign_docs if doc[0] == kind) + '</details>'
            for kind, label in groups if any(doc[0] == kind for doc in campaign_docs)
        )
    campaign_tab = f'/workspace/{campaign_id}' + (f'?doc={campaign_default[0]}:{campaign_default[1]}' if campaign_default else '')
    tabs = (f'<div class="sidebar-tabs"><a class="{"active" if not product_view else ""}" href="{campaign_tab}">{tr("workspace.campaign_area")}</a>'
            f'<a class="{"active" if product_view else ""}" href="/workspace/{campaign_id}?doc=product_docs:1">{tr("workspace.product_area")}</a></div>')
    if choice:
        kind, item_id, label, title, sections = choice
        comments = comments_for(db, campaign_id, kind, item_id)
        marked = {number for row in comments if row["line_start"] for number in range(row["line_start"], row["line_end"] + 1)}
        if kind == "product_docs":
            section_html = '<div class="markdown-rendered">' + ''.join(
                f'<div class="markdown-block commentable-block {"has-comments" if any(first <= line <= last for line in marked) else ""}" data-line-start="{first}" data-line-end="{last}">{rendered}</div>'
                for first, last, rendered in render_blocks(sections)
            ) + '</div>'
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
        if kind == "product_docs":
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
        doc_html = f'<div class="document-top"><span>{esc(label)} #{item_id}</span><span>{tr("workspace.private")}</span></div><article class="document" id="document"><h2>{esc(title)}</h2><div class="document-storage">{storage}</div>{draft_review_html}{section_html}</article>'
        def comment_row(row):
            anchor = f'L{row["line_start"]}' + (f'–{row["line_end"]}' if row["line_end"] != row["line_start"] else '') if row['line_start'] else ''
            quote = f'<blockquote data-quote="{esc(row["quote"])}" data-line="{row["line_start"] or ""}" data-offset="{row["char_offset"] if row["char_offset"] is not None else ""}" tabindex="0" title="{tr("workspace.locate_quote")}">{esc(row["quote"])}</blockquote>' if row['quote'] else ''
            source_quote = ' '.join(row['quote'].split())
            stale = f'<p class="muted">{tr("workspace.stale_quote")}</p>' if kind == 'product_docs' and row['quote'] and source_quote not in ' '.join(sections.split()) and source_quote not in visible_text(sections) else ''
            return f'<div class="comment"><small>#{row["id"]} · {esc(anchor)} · {esc(row["created_at"])}</small>{quote}{stale}<p>{esc(row["body"])}</p></div>'
        comment_html = "".join(comment_row(row) for row in comments)
        review_html = f'''<p class="muted">{tr("workspace.select_lines")}</p><div class="comments-list">{comment_html or f'<p class="muted">{tr("workspace.no_comments")}</p>'}</div>'''
        form_html = f'''<form method="post" action="/campaign/{campaign_id}/comment" id="comment-form" hidden>
            <input type="hidden" name="target_kind" value="{kind}"><input type="hidden" name="target_id" value="{item_id}">
            <input type="hidden" name="line_start" id="line-start"><input type="hidden" name="line_end" id="line-end"><input type="hidden" name="char_offset" id="char-offset">
            <input type="hidden" name="quote" id="quote"><strong id="selected-lines"></strong><blockquote id="selected-quote"></blockquote>
            <label for="comment">{tr('field.comment')}</label><textarea id="comment" name="body" maxlength="2000" rows="4" required></textarea>
            <button>{tr('action.add_comment')}</button>
          </form>'''
        selected_key = f"{kind}:{item_id}"
    else:
        doc_html = f'<div class="empty-document"><h2>{tr("workspace.no_documents")}</h2><p>{tr("workspace.create_hint")}</p></div>'
        review_html = f'<p class="muted">{tr("workspace.no_document_comment")}</p>'
        form_html = ""
        selected_key = ""
    turns = agent_turns(db, campaign_id)
    diff = draft_diff(campaign_id)
    draft_html = f'<details class="draft-diff"><summary>{tr("workspace.draft_changes")}</summary><pre>{esc(diff)}</pre></details>' if diff else ''
    messages = "".join(f'<div class="message"><div class="message-head">{tr("workspace.you")} <small>{esc(row["created_at"])}</small></div><p>{esc(row["prompt"])}</p></div><div class="message assistant {"failed" if row["status"] == "error" else ""}"><div class="message-head">{esc("Claude Code" if row["provider"] == "claude" else "Codex")} <small>{tr("workspace.status_" + row["status"])}</small></div><p>{esc(row["response"] or t("workspace.running", language))}</p></div>' for row in turns)
    if not messages:
        messages = f'<div class="empty-chat"><h2>{tr("workspace.chat_start")}</h2><p>{tr("workspace.chat_hint")}</p></div>'
    pending = bool(turns and turns[-1]["status"] == "running")
    pending_message = (f'<p class="pending-message" role="status">{tr("workspace.running")} '
                       f'<a href="/workspace/{campaign_id}?doc={esc(selected_key)}">{tr("workspace.refresh_status")}</a></p>') if pending else ''
    provider = "codex"
    provider_options = "".join(f'<option value="{name}" {"selected" if name == provider else ""}>{esc(label)}</option>' for name, label in (("codex", "Codex"), ("claude", "Claude Code")))
    playbooks = ("explore", "revise", "prepare", "conflict")
    playbook_options = "".join(f'<option value="{name}" data-prompt="{tr("workspace.playbook_" + name + "_prompt")}">{tr("workspace.playbook_" + name)}</option>' for name in playbooks)
    skills = available_skills()
    skill_options = "".join(f'<option value="{esc(name)}" data-description="{esc(description)}" label="{esc(origin)} · {esc(description[:70])}"></option>' for name, description, origin in skills)
    terminal = (f'{turns[-1]["provider"]} · {t("workspace.status_" + turns[-1]["status"], language)} · session {turns[-1]["session_id"] or "—"}' if turns else t("workspace.cli_idle", language))
    return f'''<!doctype html><html lang="{locale(language)}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(campaign['name'])} · {tr('workspace.title')}</title><link rel="stylesheet" href="/assets/workspace.css"></head>
      <body><div class="app-shell">
        <aside class="sidebar"><div class="brand"><a href="/">{tr('app.title')}</a><strong>{esc(campaign['name'])}</strong><span>{tr('workspace.private')}</span></div>
          {tabs}<nav aria-label="{tr('workspace.documents')}">{sidebar or f'<p class="sidebar-empty">{tr("workspace.no_documents")}</p>'}</nav>
          <a class="advanced-link" href="/campaign/{campaign_id}">{tr('workspace.records')}</a>
        </aside>
        <section class="conversation"><div class="panel-head"><h1>{tr('workspace.conversation')}</h1><span>{tr('workspace.cli_draft')}</span></div>
          <div class="messages" id="messages">{messages}{draft_html}</div>
          <form class="composer" method="post" action="/campaign/{campaign_id}/chat" id="chat-form" data-pending="{int(pending)}" data-status-url="/campaign/{campaign_id}/chat-status">
            {pending_message}
            <input type="hidden" name="doc" value="{esc(selected_key)}">
            <label for="playbook">{tr('workspace.playbook')}</label><select id="playbook"><option value="">{tr('workspace.playbook_none')}</option>{playbook_options}</select>
            <details class="skill-picker" data-instruction="{tr('workspace.skill_instruction')}"><summary>{tr('workspace.skills')} ({len(skills)})</summary><label for="skill-search">{tr('workspace.skill_search')}</label><input id="skill-search" list="skill-options" autocomplete="off" placeholder="{tr('workspace.skill_placeholder')}"><datalist id="skill-options">{skill_options}</datalist><p id="skill-description" class="composer-note">{tr('workspace.skill_hint')}</p><button type="button" id="add-skill">{tr('workspace.add_skill')}</button></details>
            <label for="prompt">{tr('field.message')}</label><textarea id="prompt" name="prompt" rows="3" maxlength="4000" required placeholder="{tr('workspace.prompt_hint')}"></textarea>
            <div class="composer-actions"><select name="provider" aria-label="{tr('workspace.provider')}">{provider_options}</select><button>{tr('workspace.send')}</button></div>
            <p class="composer-note">{tr('workspace.send_notice')}</p>
          </form>
        </section>
        <section class="document-panel"><div class="panel-head"><h1>{tr('workspace.documents')}</h1><span>{tr('workspace.review')}</span></div><div class="document-layout"><div class="document-scroll">{doc_html}{form_html}</div><aside class="review"><h2>{tr('workspace.comments')}</h2>{review_html}</aside></div></section>
        <footer class="terminal"><span>{tr('workspace.terminal')}</span><code>{esc(terminal)}</code></footer>
      </div><script src="/assets/workspace.js" defer></script></body></html>'''


def document_context(db, campaign_id, selected):
    try:
        kind, raw_id = selected.split(":", 1)
        item_id = int(raw_id)
        if kind == "product_docs":
            relative, _ = product_doc(item_id)
            comments = comments_for(db, campaign_id, kind, item_id)
            review = "\n".join(f"Comment on lines {comment['line_start']}-{comment['line_end']} '{comment['quote']}': {comment['body']}" for comment in comments)
            return f"Selected product document: {relative}. Read it from the repository if needed.\nReview comments:\n{review or 'None'}\n\n"
        columns = COMMENT_TARGETS[kind]
    except (ValueError, KeyError):
        return ""
    comments = comments_for(db, campaign_id, kind, item_id)
    row = db.execute(f"SELECT {', '.join(columns)} FROM {kind} WHERE id=? AND campaign_id=?", (item_id, campaign_id)).fetchone()
    content = "\n".join(f"{name}: {row[name]}" for name in columns)
    review = "\n".join(f"Comment on lines {comment['line_start']}-{comment['line_end']} '{comment['quote']}': {comment['body']}" for comment in comments)
    return f"Selected document ({kind} #{item_id}):\n{content}\nReview comments:\n{review or 'None'}\n\n"
