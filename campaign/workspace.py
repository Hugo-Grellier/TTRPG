"""Campaign conversation and document review workspace."""

import html

from .agent_cli import draft_diff
from .i18n import locale, t
from .markdown import render_blocks, visible_text
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
    choice = next((doc for doc in documents if f"{doc[0]}:{doc[1]}" == selected), None)
    if choice is None and documents:
        choice = next((doc for doc in documents if doc[0] == "preparations"), documents[0])
    groups = [("product_docs", "workspace.product_docs"),
              ("preparations", "workspace.preparation"), ("facts", "workspace.fact"),
              ("proposals", "workspace.proposal"), ("sources", "workspace.source"),
              ("simulated_events", "workspace.simulation")]
    sidebar = "".join(
        f'<div class="tree-group"><h2>{tr(label)}</h2>' + "".join(
            f'<a class="doc-link {"active" if choice == doc else ""}" href="/workspace/{campaign_id}?doc={doc[0]}:{doc[1]}"><span class="doc-icon">▤</span><span>{esc(doc[3])}</span></a>'
            for doc in documents if doc[0] == kind) + '</div>'
        for kind, label in groups if any(doc[0] == kind for doc in documents)
    )
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
        doc_html = f'<div class="document-top"><span>{esc(label)} #{item_id}</span><span>{tr("workspace.private")}</span></div><article class="document" id="document"><h2>{esc(title)}</h2>{section_html}</article>'
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
    draft_html = f'<details class="draft-diff" open><summary>{tr("workspace.draft_changes")}</summary><pre>{esc(diff)}</pre></details>' if diff else ''
    messages = "".join(f'<div class="message"><div class="message-head">{tr("workspace.you")} <small>{esc(row["created_at"])}</small></div><p>{esc(row["prompt"])}</p></div><div class="message assistant {"failed" if row["status"] == "error" else ""}"><div class="message-head">{esc("Claude Code" if row["provider"] == "claude" else "Codex")} <small>{tr("workspace.status_" + row["status"])}</small></div><p>{esc(row["response"] or t("workspace.running", language))}</p></div>' for row in turns)
    if not messages:
        messages = f'<div class="empty-chat"><h2>{tr("workspace.chat_start")}</h2><p>{tr("workspace.chat_hint")}</p></div>'
    provider = turns[-1]["provider"] if turns else "codex"
    provider_options = "".join(f'<option value="{name}" {"selected" if name == provider else ""}>{esc(label)}</option>' for name, label in (("codex", "Codex"), ("claude", "Claude Code")))
    playbooks = ("explore", "revise", "prepare", "conflict")
    playbook_options = "".join(f'<option value="{name}" data-prompt="{tr("workspace.playbook_" + name + "_prompt")}">{tr("workspace.playbook_" + name)}</option>' for name in playbooks)
    terminal = (f'{turns[-1]["provider"]} · {t("workspace.status_" + turns[-1]["status"], language)} · session {turns[-1]["session_id"] or "—"}' if turns else t("workspace.cli_idle", language))
    return f'''<!doctype html><html lang="{locale(language)}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(campaign['name'])} · {tr('workspace.title')}</title><link rel="stylesheet" href="/assets/workspace.css"></head>
      <body><div class="app-shell">
        <aside class="sidebar"><div class="brand"><a href="/">{tr('app.title')}</a><strong>{esc(campaign['name'])}</strong><span>{tr('workspace.private')}</span></div>
          <nav aria-label="{tr('workspace.documents')}">{sidebar or f'<p class="sidebar-empty">{tr("workspace.no_documents")}</p>'}</nav>
          <a class="advanced-link" href="/campaign/{campaign_id}">{tr('workspace.records')}</a>
        </aside>
        <section class="conversation"><div class="panel-head"><h1>{tr('workspace.conversation')}</h1><span>{tr('workspace.cli_draft')}</span></div>
          <div class="messages" id="messages">{messages}{draft_html}</div>
          <form class="composer" method="post" action="/campaign/{campaign_id}/chat" id="chat-form">
            <input type="hidden" name="doc" value="{esc(selected_key)}">
            <label for="playbook">{tr('workspace.playbook')}</label><select id="playbook"><option value="">{tr('workspace.playbook_none')}</option>{playbook_options}</select>
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
