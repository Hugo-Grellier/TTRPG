"""Read-only CLI conversation bridge. Campaign changes still pass through GM review."""

import json
import shutil
import subprocess
from pathlib import Path

from .core import DomainError


ROOT = Path(__file__).resolve().parent.parent
CONTEXT = (
    "You are speaking with a GM in a private campaign workspace. "
    "Sources and proposals are not campaign canon; only an explicit GM decision establishes a fact. "
    "Treat document comments as review requests. Suggest edits in the conversation, with provenance and uncertainty. "
    "This CLI connection is read-only: do not modify files or durable campaign memory. "
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


def run_cli(provider, prompt, previous_session=None):
    executable = shutil.which("codex" if provider == "codex" else "claude")
    if not executable:
        raise DomainError("error.provider_missing")
    if provider == "codex":
        command = [executable, "exec", "--json", "-s", "read-only", "-C", str(ROOT)]
        command += ["resume", previous_session, prompt] if previous_session else [prompt]
        parser = parse_codex
    else:
        command = [executable, "-p", "--output-format", "json", "--permission-mode", "dontAsk",
                   "--tools=Read,Grep,Glob,Skill"]
        if previous_session:
            command += ["--resume", previous_session]
        command += [prompt]
        parser = parse_claude
    try:
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=300, check=False)
    except subprocess.TimeoutExpired:
        return "The CLI did not finish within five minutes. Check its local session before retrying.", None, False
    except OSError as exc:
        return str(exc), None, False
    response, session_id = parser(result.stdout)
    if result.returncode or not response:
        detail = (result.stderr or result.stdout).strip()[-1500:]
        return detail or "The CLI returned no answer.", session_id, False
    return response, session_id, True
