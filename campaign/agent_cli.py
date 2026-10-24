"""CLI conversation bridge using an isolated draft checkout per campaign."""

import json
import shutil
import subprocess
from pathlib import Path

from .core import DomainError
from .paths import data_dir


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


def run_cli(provider, prompt, previous_session=None, campaign_id=1):
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
        command = [executable, "-p", "--output-format", "json", "--restricted", "--permission-mode", "acceptEdits",
                   "--tools=Read,Grep,Glob,Edit,Write,Skill"]
        if previous_session:
            command += ["--resume", previous_session]
        command += [prompt]
        parser = parse_claude
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
