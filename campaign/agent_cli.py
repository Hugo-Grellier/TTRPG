"""CLI conversation bridge using an isolated draft checkout per campaign."""

import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from .core import DomainError
from .paths import data_dir
from .store import PRODUCT_DOCS


ROOT = Path(__file__).resolve().parent.parent
CONTEXT = (
    "You are speaking with a GM in a private campaign workspace. "
    "Sources and proposals are not campaign canon; only an explicit GM decision establishes a fact. "
    "Treat document comments as review requests. You may edit repository files in this isolated draft checkout when asked. "
    "Never write durable campaign memory; only an explicit GM action establishes a fact. "
    "Explain any file changes in your reply. "
    "Respond in the campaign language.\n\n"
)


def parse_codex(output):
    session_id = None
    messages = []
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "thread.started":
            session_id = event.get("thread_id")
        item = event.get("item") or {}
        if event.get("type") == "item.completed" and item.get("type") == "agent_message":
            messages.append(item.get("text", ""))
    return "\n\n".join(messages).strip(), session_id


def parse_claude(output):
    try:
        event = json.loads(output)
    except json.JSONDecodeError:
        return "", None
    return str(event.get("result") or ""), event.get("session_id")


def draft_checkout(campaign_id):
    path = data_dir() / "drafts" / f"campaign-{campaign_id}"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "worktree", "add", "--detach", str(path), "HEAD"],
                       cwd=ROOT, capture_output=True, text=True, check=True)
    if subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=path,
                      capture_output=True, text=True, check=True).stdout.strip() != str(path):
        raise RuntimeError("Draft checkout path is not a Git worktree")
    return path


def draft_diff(campaign_id):
    path = data_dir() / "drafts" / f"campaign-{campaign_id}"
    if not path.exists():
        return ""
    result = subprocess.run(["git", "diff", "--no-ext-diff", "--"], cwd=path,
                            capture_output=True, text=True, check=True)
    return result.stdout[:30000]


def draft_file_review(campaign_id, file_id):
    if not 1 <= file_id <= len(PRODUCT_DOCS):
        raise DomainError("error.item_missing")
    relative = PRODUCT_DOCS[file_id - 1]
    draft = data_dir() / "drafts" / f"campaign-{campaign_id}"
    source = draft / relative
    if not draft.is_dir() or not source.is_file() or not source.resolve().is_relative_to(draft.resolve()):
        return None
    base = subprocess.run(["git", "show", f"HEAD:{relative}"], cwd=draft,
                          capture_output=True, check=True).stdout
    proposed = source.read_bytes()
    if proposed == base:
        return None
    current = (ROOT / relative).read_bytes()
    status = "ready" if current == base else "applied" if current == proposed else "conflict"
    diff = subprocess.run(["git", "diff", "--no-ext-diff", "--", relative], cwd=draft,
                          capture_output=True, text=True, check=True).stdout
    return {"relative": relative, "status": status, "diff": diff[:30000], "proposed": proposed, "base": base}


def apply_draft_file(campaign_id, file_id):
    review = draft_file_review(campaign_id, file_id)
    if review is None:
        raise DomainError("error.draft_missing")
    if review["status"] != "ready":
        raise DomainError("error.draft_conflict")
    target = ROOT / review["relative"]
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as temporary:
        temporary.write(review["proposed"])
        temporary_path = Path(temporary.name)
    try:
        temporary_path.chmod(target.stat().st_mode)
        if target.read_bytes() != review["base"]:
            raise DomainError("error.draft_conflict")
        os.replace(temporary_path, target)
    finally:
        temporary_path.unlink(missing_ok=True)


def _stream_cli(command, path, provider, on_update):
    parts, session_id, final, failed = [], None, "", False
    last_update = 0.0
    expired = threading.Event()
    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as errors:
        try:
            with subprocess.Popen(command, cwd=path, stdout=subprocess.PIPE, stderr=errors,
                                  text=True, encoding="utf-8", errors="replace", bufsize=1) as process:
                def timeout():
                    if process.poll() is None:
                        expired.set()
                        try:
                            process.kill()
                        except ProcessLookupError:
                            pass
                timer = threading.Timer(300, timeout)
                timer.start()
                try:
                    for line in process.stdout:
                        try:
                            event = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if provider == "codex":
                            if event.get("type") == "thread.started":
                                session_id = event.get("thread_id")
                            item = event.get("item") or {}
                            if event.get("type") == "item.completed" and item.get("type") == "agent_message" and item.get("text"):
                                parts.append(item["text"])
                        else:
                            if event.get("type") == "system" and event.get("session_id"):
                                session_id = event["session_id"]
                            inner = event.get("event") or {}
                            delta = inner.get("delta") or {}
                            if event.get("type") == "stream_event" and inner.get("type") == "content_block_delta" and delta.get("type") == "text_delta":
                                parts.append(delta.get("text", ""))
                            if event.get("type") == "result":
                                final = str(event.get("result") or "")
                                failed = bool(event.get("is_error"))
                                session_id = event.get("session_id") or session_id
                        preview = "\n\n".join(parts) if provider == "codex" else "".join(parts)
                        if preview and (provider == "codex" or time.monotonic() - last_update >= .2):
                            on_update(preview[:20000])
                            last_update = time.monotonic()
                    process.wait()
                finally:
                    timer.cancel()
            errors.seek(0)
            error_text = errors.read()[-1500:]
        except OSError as exc:
            return str(exc), session_id, False
    if expired.is_set():
        return "The CLI did not finish within five minutes. Check its local session before retrying.", session_id, False
    response = final or ("\n\n".join(parts) if provider == "codex" else "".join(parts))
    if process.returncode or failed or not response:
        return error_text or response[-1500:] or "The CLI returned no answer.", session_id, False
    return response, session_id, True


def run_cli(provider, prompt, previous_session=None, campaign_id=1, on_update=None):
    executable = shutil.which("codex" if provider == "codex" else "claude")
    if not executable:
        raise DomainError("error.provider_missing")
    try:
        path = draft_checkout(campaign_id)
    except (OSError, subprocess.CalledProcessError, RuntimeError) as exc:
        return f"Cannot prepare the draft checkout: {exc}", None, False
    if provider == "codex":
        command = [executable, "exec", "--json", "-s", "workspace-write", "-C", str(path)]
        command += ["resume", previous_session, prompt] if previous_session else [prompt]
        parser = parse_codex
    else:
        command = [executable, "-p", "--output-format", "stream-json" if on_update else "json", "--restricted", "--permission-mode", "acceptEdits",
                   "--tools=Read,Grep,Glob,Edit,Write,Skill"]
        if on_update:
            command.append("--include-partial-messages")
        if previous_session:
            command += ["--resume", previous_session]
        command += [prompt]
        parser = parse_claude
    if on_update:
        return _stream_cli(command, path, provider, on_update)
    try:
        result = subprocess.run(command, cwd=path, text=True, capture_output=True, timeout=300, check=False)
    except subprocess.TimeoutExpired:
        return "The CLI did not finish within five minutes. Check its local session before retrying.", None, False
    except OSError as exc:
        return str(exc), None, False
    response, session_id = parser(result.stdout)
    if result.returncode or not response:
        detail = (result.stderr or result.stdout).strip()[-1500:]
        return detail or "The CLI returned no answer.", session_id, False
    return response, session_id, True
