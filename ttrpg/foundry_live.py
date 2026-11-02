"""Bring a running Foundry world up to date with the campaign notes.

The notes are the desired state. Every world document the sync owns carries
`flags.ttrpg` with a hash of its data and the same deterministic id as the
journal pack `export-foundry` builds, so links between pages keep working. The
sync never touches a document without that flag.

It talks to the foundry-mcp backend (the fork with the `sync-world` tool) as a
second client of its control channel, JSON lines on 127.0.0.1:31414, beside
the instance Claude Code runs; the GM's browser must be connected to it.
"""

import hashlib
import json
import socket

from . import vault
from .foundry_export import Exporter, foundry_id
from .foundry_sync import new_report, pull_page
from .vault import body_hash

HOST, PORT = "127.0.0.1", 31414
# Bytes per apply call: the bridge's WebRTC channel takes 64 KB a message and each query 10 s.
BATCH = 40_000
TYPES = ["Folder", "JournalEntry", "JournalEntryPage"]


class Backend:
    """A client of the foundry-mcp backend's control channel."""

    def __init__(self, host=HOST, port=PORT, timeout=60):
        try:
            self.socket = socket.create_connection((host, port), timeout=timeout)
        except OSError as error:
            raise SystemExit(f"foundry-mcp backend not reachable on {host}:{port} ({error}): "
                             "start Claude Code with the foundry-mcp server, and connect the GM's browser") from None
        self.stream = self.socket.makefile("rwb")
        self.count = 0

    def sync(self, **args):
        self.count += 1
        request = {"id": str(self.count), "method": "call_tool", "params": {"name": "sync-world", "args": args}}
        self.stream.write((json.dumps(request, ensure_ascii=False) + "\n").encode())
        self.stream.flush()
        reply = json.loads(self.stream.readline())
        if "error" in reply:
            raise SystemExit(f"foundry-mcp: {reply['error'].get('message')}")
        text = reply["result"]["content"][-1]["text"]
        if reply["result"].get("isError"):
            raise SystemExit(f"foundry-mcp: {text}")
        result = json.loads(text)
        if isinstance(result, dict) and result.get("error"):
            raise SystemExit(f"foundry-mcp: {result['error']} (is the connected user a GM, writes allowed in the bridge settings?)")
        return result


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def managed(document_name, _id, data, parent=None):
    """A desired document: its data carries flags.ttrpg.hash, the hash of everything else."""
    data = json.loads(json.dumps(data))
    data.pop("_key", None)
    data.setdefault("flags", {}).setdefault("ttrpg", {})
    data["flags"]["ttrpg"]["hash"] = digest(data)
    document = {"documentName": document_name, "_id": _id, "data": data}
    if parent:
        document["parent"] = parent
    return document


def desired(exporter):
    """The world documents the notes describe: one folder, a journal per category, a page per note."""
    name = exporter.config.get("name", "Campagne")
    folder = foundry_id(exporter.module_id, "folder", "journal")
    documents = [managed("Folder", folder, {"name": name, "type": "JournalEntry", "sorting": "m"})]
    for entry in exporter.entries():
        pages = entry.pop("pages")
        documents.append(managed("JournalEntry", entry["_id"], {**entry, "folder": folder}))
        documents += [managed("JournalEntryPage", page["_id"], page, f"JournalEntry.{entry['_id']}") for page in pages]
    return documents


def key(document):
    return document["documentName"], document["_id"]


def plan(documents, world):
    """create / update / delete lists, and the pages edited in Foundry since the last sync."""
    want = {key(document): document for document in documents}
    have = {key(document): document for document in world}
    create = [document for k, document in want.items() if k not in have]
    update = [document for k, document in want.items()
              if k in have and (have[k].get("flags") or {}).get("hash") != document["data"]["flags"]["ttrpg"]["hash"]]
    gone = {k for k in have if k not in want}
    # Deleting an entry deletes its pages.
    delete = [{k: v for k, v in document.items() if k != "markdown"} for k, document in have.items()
              if k in gone and not (document.get("parent") and tuple(document["parent"].split(".")) in gone)]
    edited = []
    for k, document in have.items():
        if k[0] != "JournalEntryPage" or "markdown" not in document:
            continue
        current = body_hash(document["markdown"])
        target = want.get(k, {}).get("data", {}).get("flags", {}).get("ttrpg", {}).get("exported")
        if current != (document.get("flags") or {}).get("exported") and current != target:
            edited.append(document)
    order = {name: index for index, name in enumerate(TYPES)}
    create.sort(key=lambda document: order[document["documentName"]])
    delete.sort(key=lambda document: -order[document["documentName"]])
    return {"create": create, "update": update, "delete": delete, "edited": edited}


def batches(action, documents):
    """Consecutive calls of at most BATCH bytes, keeping the given order."""
    batch, size = [], 0
    for document in documents:
        length = len(json.dumps(document, ensure_ascii=False).encode())
        if batch and size + length > BATCH:
            yield {action: batch}
            batch, size = [], 0
        batch.append(document)
        size += length
    if batch:
        yield {action: batch}


def label(document):
    """What a planned document is, for the GM: its note path when it has one."""
    flags = document["data"]["flags"]["ttrpg"] if "data" in document else (document.get("flags") or {})
    name = document.get("data", {}).get("name")
    return flags.get("path") or name or f"{document['documentName']} {document['_id']}"


def sync(root, backend, apply=False, force=False):
    exporter = Exporter(vault.load(root))
    world = backend.sync(op="inventory", types=TYPES, text=True)["documents"]
    steps = plan(desired(exporter), world)
    if apply and steps["edited"] and not force:
        return steps, None
    done = None
    if apply:
        done = {"created": 0, "updated": 0, "deleted": 0}
        for action in ("create", "update", "delete"):
            for call in batches(action, steps[action]):
                for name, count in backend.sync(op="apply", **call).items():
                    done[name] += count
    return steps, done


def pull(root, backend):
    exporter = Exporter(vault.load(root))
    report = new_report()
    for document in backend.sync(op="inventory", types=["JournalEntryPage"], text=True)["documents"]:
        page = {"_id": document["_id"], "flags": {"ttrpg": document.get("flags")},
                "text": {"format": 2, "markdown": document.get("markdown", "")}}
        pull_page(exporter, document["parent"].split(".")[1], page, report)
    return report
