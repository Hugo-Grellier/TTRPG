"""ttrpg: tools for campaign repositories. Run `ttrpg <command> --help`."""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

try:
    import markdown_it  # noqa: F401
    import yaml
except ImportError as error:
    _tools = Path(__file__).resolve().parent.parent
    raise SystemExit(f"{error}: install the tools' Python packages once with\n"
                     f"  python3 -m venv {_tools}/.venv && {_tools}/.venv/bin/pip install -r {_tools}/requirements.txt") from None

from . import check as checker
from .foundry_export import export
from .foundry_import import import_adventure, import_module, slug
from .foundry_sync import pull
from .rename import rename
from . import library, session

TOOLS = Path(__file__).resolve().parent.parent


def cmd_check(args):
    _, report = checker.check(args.root, fix=args.fix)
    if report.items:
        print(report)
    notes = len(checker.vault.load(args.root).notes)
    print(f"{notes} notes, {len(report.errors)} errors, {len(report.items) - len(report.errors)} warnings")
    return 1 if report.errors else 0


def cmd_export_foundry(args):
    result = export(args.root, args.out)
    print(f"{result['pages']} pages in {result['entries']} journal entries -> {result['path']}")
    if args.install:
        target = Path(args.install) / result["module"]
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(result["path"], target)
        print(f"installed in {target}; enable the module, then import the compendium entries into the world")
    return 0


def cmd_pull_foundry(args):
    report = pull(args.root, args.world)
    for rel in report["updated"]:
        print(f"updated {rel}")
    for rel in report["conflicts"]:
        print(f"conflict {rel}: changed in the repository and in Foundry since the export; repository kept")
    for note_id in report["missing"]:
        print(f"missing {note_id}: exported page whose note no longer exists")
    print(f"{len(report['updated'])} updated, {len(report['conflicts'])} conflicts, {report['unchanged']} unchanged; review with git diff")
    return 1 if report["conflicts"] else 0


def cmd_foundry(args):
    from . import foundry_live
    backend = foundry_live.Backend(args.host, args.port)
    exporter = foundry_live.Exporter(checker.vault.load(args.root))
    world = backend.world()
    print(f"world: {world['title']} ({world['id']})")
    refusal = foundry_live.world_guard(exporter.campaign.config, world, args.action == "apply")
    if refusal:
        raise SystemExit(refusal)
    if not (backend.sync(op="setting", key="core.moduleConfiguration")["value"] or {}).get(exporter.module_id):
        print(f"note: module {exporter.module_id} is not active in this world; images in the notes and the hex panel need it "
              "(`ttrpg export-foundry --install <Foundry Data/modules>`, then enable it in the world)")
    if args.action == "pull":
        report = foundry_live.pull(args.root, backend)
        for rel in report["updated"]:
            print(f"updated {rel}")
        for rel in report["conflicts"]:
            print(f"conflict {rel}: changed in the repository and in Foundry; repository kept")
        print(f"{len(report['updated'])} updated, {len(report['conflicts'])} conflicts, {report['unchanged']} unchanged; review with git diff")
        return 1 if report["conflicts"] else 0
    steps, done = foundry_live.sync(args.root, backend, apply=args.action == "apply", force=args.force)
    actions = ("adopt", "create", "update", "release", "delete")
    for action in actions:
        for document in steps[action]:
            print(f"{action} {document['documentName']} {foundry_live.label(document)}")
    for document in steps["edited"]:
        print(f"edited in Foundry {foundry_live.label(document)}")
    if steps["time"]:
        print(f"date: world clock to {steps['time']['date']}")
    if steps["time_ahead"]:
        print(f"date: Foundry's clock is past the notes ({steps['time_ahead']}); left as is")
    for clock in steps["clocks"].values():
        print(f"clock {clock['ttrpg']['path']}: {clock['value']}/{clock['max']}")
    for clock in steps["clocks_edited"]:
        print(f"clock moved in Foundry {clock['ttrpg']['path']}: {clock['value']}/{clock['max']} (pull to keep it)")
    for pin in steps["pins"]:
        target = pin["data"].get("flags", {}).get("ttrpg", {}).get("path")
        print(f"pin {pin['parent']} {pin['_id']}: " + (f"opens {target}" if target else "back to the adventure page"))
    for change in steps["explore"]:
        print(f"map {change['uuid']}: reveal {len(change['set'])} cells, hide {len(change['remove'])}")
    if steps["clocks_remove"]:
        print(f"clocks to remove: {len(steps['clocks_remove'])}")
    print(", ".join(f"{len(steps[action])} to {action}" for action in actions) + f", {len(steps['edited'])} pages edited in Foundry")
    if args.action == "apply" and done is None:
        print("nothing applied: run `ttrpg foundry pull` first (or --force to overwrite what changed in Foundry)")
        return 1
    if done:
        print(f"applied: {done['created']} created, {done['updated']} updated, {done['deleted']} deleted")
        for uuid in done["missing"]:
            print(f"not in this world: {uuid} (a note's foundry link points at an actor or a scene this world does not have)")
    return 0


def cmd_rename(args):
    changed = rename(args.root, args.old, args.new)
    print(f"{args.old} -> {args.new}; links updated in {changed} notes")
    return 0


def cmd_questions(args):
    from .vault import load, open_items
    counts, current = {}, None
    for note, line, kind, text in open_items(load(args.root), args.kind):
        counts[kind] = counts.get(kind, 0) + 1
        if note is not current:
            print(f"{note.rel} ({note.meta.get('title') or note.id})")
            current = note
        print(f"  {line} {kind}: {text[:160]}")
    print(", ".join(f"{n} {kind}" for kind, n in counts.items()) or "nothing open")
    return 0


def cmd_maps(args):
    campaign = checker.vault.load(args.root)
    maps = [note for note in campaign.notes.values() if note.type == "map"]
    for stage in ("raw", "walled", "lit", "ready"):
        print(f"{stage}: {sum(1 for note in maps if note.get('stage') == stage)} maps")
    gaps = checker.map_gaps(campaign)
    print(f"\n{len(gaps)} places with creatures and no map:")
    for note in sorted(gaps, key=lambda note: (str(note.get('region') or ''), note.id)):
        print(f"  {note.get('region') or '-'}: {note.id} ({note.rel})")
    return 0


def cmd_glossary(args):
    from . import glossary
    config = yaml.safe_load((Path(args.root) / "campaign.yaml").read_text(encoding="utf-8")) or {}
    rows = glossary.build(Path(args.root) / ".cache" / "glossary", config.get("language", "fr"))
    out = glossary.write(args.root, rows)
    print(f"{len(rows)} names ({sum(1 for row in rows if row[4])} pre-remaster) -> {out}")
    return 0


def cmd_drafts(args):
    from .drafts import drafts
    made, skipped = drafts(args.root, args.inventory or Path(args.root) / ".cache/compile/inventory.tsv")
    for rel in made:
        print(f"draft {rel}")
    print(f"{len(made)} drafts, {len(skipped)} subjects already had a note")
    return 0


def cmd_import_foundry(args):
    if args.json:
        stats = import_adventure(args.root, json.loads(Path(args.json).read_text(encoding="utf-8")), args.module_id)
    else:
        stats = import_module(args.root, args.module)
    print(f"{stats['relinked']} notes relinked to renamed pages, {stats['written']} AP notes written, {stats['kept']} GM-edited notes kept, {stats['removed']} stale removed, "
          f"{stats['seeded']} NPC drafts and {stats['maps']} maps seeded, {stats['indexed']} Foundry documents indexed")
    return 0


def cmd_pdf_text(args):
    """Extract a PDF page by page into .cache/sources/<id>/ (ignored by Git) for local agents."""
    pages = library.extract(args.pdf, Path(args.root) / ".cache" / "sources" / args.source)
    config_path = Path(args.root) / "campaign.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config.setdefault("sources", {}).setdefault(args.source, {})
    config["sources"][args.source].update({"title": args.title or Path(args.pdf).stem, "pages": pages})
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"{pages} pages in .cache/sources/{args.source}; cite as src:{args.source}#p<N>")
    return 0


def cmd_library(args):
    lib = Path(args.library) if args.library else library.location()
    if args.action == "index":
        if not args.args:
            print("ttrpg library index <directory>...", file=sys.stderr)
            return 2
        library.index(lib, args.args)
    elif not (lib / "catalog.yaml").is_file():
        print(f"no library at {lib}: run `ttrpg library index <directory of PDFs>` (or set TTRPG_LIBRARY)", file=sys.stderr)
        return 1
    elif args.action == "list":
        for book, entry in library.load(lib).items():
            line = f"{book}\t{entry.get('pages', '?')}\t{entry['title']}"
            if all(word.lower() in f"{line} {entry['path']}".lower() for word in args.args):
                print(line)
    elif args.action == "search":
        if not args.args:
            print("ttrpg library search <regex> [--book id-part]", file=sys.stderr)
            return 2
        hits = list(library.search(lib, " ".join(args.args), args.book, not args.case, args.context))
        if not hits:
            print("no match", file=sys.stderr)
            return 1
        if args.pages:
            found = {}
            for book, page, _ in hits:
                found.setdefault(book, []).append(page)
            titles = library.load(lib)
            for book, pages in found.items():
                pages = sorted(set(pages))
                print(f"{book}\t{len(pages)}\t{titles[book]['title']}\t" + " ".join(f"p{n}" for n in pages))
        else:
            for count, (book, page, line) in enumerate(hits):
                if count == args.limit:
                    print(f"... more than {args.limit} lines: narrow with --book or --pages", file=sys.stderr)
                    break
                print(f"{book}#p{page}: {line[:200]}" if not args.context else f"--- {book}#p{page}\n{line}")
    elif args.action == "page":
        if len(args.args) != 2:
            print("ttrpg library page <id> <page>", file=sys.stderr)
            return 2
        book, number = args.args[0], int(args.args[1])
        if args.text:
            text = lib / book / f"p{number:03}.txt"
            if not text.is_file():
                print(f"no page {number} in {book}", file=sys.stderr)
                return 1
            print(text.read_text(encoding="utf-8"))
        else:
            print(library.render_page(lib, book, number, args.dpi))
    return 0


def cmd_aon(args):
    found = False
    for name, category, sources, url, summary, edition in library.aon(" ".join(args.query), args.category, args.limit):
        found = True
        print(f"{name} [{category}{', ' + edition if edition else ''}] {sources}\n  {url}" + (f"\n  {summary[:300]}" if summary else ""))
    if not found:
        print("no entry on Archives of Nethys (it rarely has places: search the library)", file=sys.stderr)
        return 1
    return 0


def cmd_creatures(args):
    from . import creatures, vault
    index = library.location().parent / "creatures.json"
    if args.index:
        rows = creatures.build(args.index, index)
        print(f"{len(rows)} creatures and hazards in {index}")
        return 0
    if not index.is_file():
        print(f"no creature index at {index}: run `ttrpg creatures --index <Foundry Data/systems/pf2e>`", file=sys.stderr)
        return 1
    campaign = vault.load(args.root) if (Path(args.root) / "campaign.yaml").is_file() else None
    party = args.party or (campaign and campaign.config.get("party")) or 4
    party_level = args.party_level
    if party_level is None and campaign:
        sessions = sorted((str(n.get("day")), n.get("level")) for n in campaign.notes.values() if n.type == "session" and n.get("level"))
        party_level = sessions[-1][1] if sessions else None
    levels = None
    if args.level:
        bounds = re.fullmatch(r"(-?\d+)(?:-(-?\d+))?", args.level)
        if not bounds:
            print("--level takes a level or a range, e.g. 3, 1-5, -1-2", file=sys.stderr)
            return 2
        levels = range(int(bounds[1]), int(bounds[2] or bounds[1]) + 1)
    elif party_level is not None and not args.name:
        levels = range(party_level - 4, party_level + 5)  # GM Core: creatures beyond +-4 cost no XP
    if party_level is not None:
        budgets = ", ".join(f"{threat} {creatures.budget(party, threat)}" for threat in creatures.THREATS)
        print(f"party of {party} at level {party_level}: {budgets} XP (GM Core p. 75)")
    names = creatures.translations(Path(args.root) / "glossary.tsv")
    rows = creatures.find(json.loads(index.read_text(encoding="utf-8"))["creatures"], levels, args.trait, args.name, args.rarity, args.pack, args.hazards)
    for row in rows[:args.limit]:
        cost = creatures.xp(row["level"], party_level) if party_level is not None and not args.hazards else None
        name = row["name"] + (f" ({names[row['id']]})" if names.get(row["id"]) and names[row["id"]] != row["name"] else "")
        print(f"{row['level']}\t{cost if cost is not None else ''}\t{name}\t{row['rarity']}\t{', '.join(row['traits'])}\t@UUID[{row['uuid']}]")
    if not rows:
        print("no match" + (f" between levels {levels.start} and {levels.stop - 1}" if levels else ""), file=sys.stderr)
        return 1
    if len(rows) > args.limit:
        print(f"... {len(rows)} matches: narrow with --trait, --name or --level", file=sys.stderr)
    return 0


def cmd_hexmap(args):
    from . import hexmap
    def pair(text, sep=","):
        a, b = text.split(sep)
        return float(a), float(b)
    controls = {}
    for item in args.control:
        name, _, xy = item.rpartition("=")
        controls[name] = pair(xy)
    try:
        places, errors = hexmap.place(hexmap.wiki_places(library.location().parent / "wiki-map"), controls,
                                      args.size, pair(args.origin), pair(args.image, "x"))
    except (KeyError, ValueError) as error:
        print(f"hexmap: {error} (names as on PathfinderWiki's map)", file=sys.stderr)
        return 1
    for name, error in errors.items():
        print(f"# control {name}: {error / args.px_per_mile:.1f} mi off" if args.px_per_mile else f"# control {name}: {error:.0f} px off")
    for row in sorted(places, key=lambda r: (r[4], r[0])):
        print("\t".join(map(str, row)))
    return 0


def cmd_source_add(args):
    if args.action == "excerpts":
        written, removed, missing = library.excerpts(checker.vault.load(args.root))
        print(f"sources/: {written} pages written, {removed} no longer cited removed")
        for page in missing:
            print(f"{page}: no text in .cache/sources/ (declare the book with `source add`)", file=sys.stderr)
        return 1 if missing else 0
    if not args.books:
        print("source add: give library ids", file=sys.stderr)
        return 2
    lib = Path(args.library) if args.library else library.location()
    if args.alias and len(args.books) > 1:
        print("--as takes a single book", file=sys.stderr)
        return 2
    for book in args.books:
        book, _, alias = book.partition("=")
        try:
            print(library.declare(args.root, lib, book, alias or args.alias))
        except KeyError:
            print(f"{book}: not in the library ({lib}); see `ttrpg library list`", file=sys.stderr)
            return 1
    return 0


def session_dir(root, day):
    out = Path(root) / "sessions" / day
    out.mkdir(parents=True, exist_ok=True)
    return out


def cmd_transcribe(args):
    config = yaml.safe_load((Path(args.root) / "campaign.yaml").read_text(encoding="utf-8")) or {}
    names = dict(pair.split("=", 1) for pair in args.names)
    audio = Path(args.root) / ".cache" / "sessions" / "audio"
    files = session.tracks(args.audio, audio)
    if not files:
        raise SystemExit("no audio tracks found")
    day = args.day or session.craig_day(audio) or next(filter(None, (session.craig_day(p) for p in map(Path, args.audio) if p.is_dir())), None) or date.today().isoformat()
    sources = []
    for path in files:
        who, role = session.speaker(path, names, config.get("players"))
        if role == "bot":
            print(f"skipping {path.name}: bot", flush=True)
            continue
        if role == "unknown":
            print(f"warning: {path.name} is not in campaign.yaml players; kept as {who}", flush=True)
        sources.append((who, path))
    run = session.whisper(args.model, args.language or config.get("language"))
    segments = {}
    for who, path in sources:
        print(f"transcribing {path.name} as {who}", flush=True)
        segments.setdefault(who, []).extend(run(path))
    lines = session.merge(segments)
    out = session_dir(args.root, day)
    (out / "transcript.md").write_text(session.transcript(lines, sources, args.model, day), encoding="utf-8")
    print(f"{len(lines)} lines from {len(sources)} tracks -> {out / 'transcript.md'}")
    return 0


def cmd_flight(args):
    text, day = session.flight_summary(session.flight_events(args.session, args.db, args.ffr))
    path = session_dir(args.root, args.day or day) / "flight.md"
    path.write_text(text, encoding="utf-8")
    print(f"Flight Recorder summary -> {path}")
    return 0


def cmd_new(args):
    root = Path(args.root)
    if root.exists() and any(root.iterdir()):
        raise SystemExit(f"{root} is not empty")
    shutil.copytree(TOOLS / "template", root, dirs_exist_ok=True)
    # The id names the Foundry module and its documents: written once, so renaming the campaign keeps them.
    config = {"id": slug(args.name), "name": args.name, "system": args.system, "language": args.language,
              "calendar": args.calendar, "start": args.start or None, "sources": {}}
    (root / "campaign.yaml").write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    run = lambda *command: subprocess.run(command, cwd=root, check=True)
    run("git", "init", "-q", "-b", "main")
    tools_url = args.tools_url or subprocess.run(["git", "-C", str(TOOLS), "remote", "get-url", "origin"],
                                                 capture_output=True, text=True).stdout.strip()
    if not tools_url:
        raise SystemExit("--tools-url is needed: this copy of the tools has no `origin` remote")
    run("git", "-c", "protocol.file.allow=always", "submodule", "add", "-q", tools_url, "tools")
    for skills in (".claude/skills", ".agents/skills"):
        (root / skills).parent.mkdir(exist_ok=True)
        (root / skills).symlink_to(Path("../tools/skills"))
    run("git", "config", "core.hooksPath", ".githooks")
    print(f"campaign repository ready in {root}\n"
          "next: open it with your agent (Claude Code, Codex) and describe the campaign, or write notes by hand;\n"
          "`tools/bin/ttrpg check` validates them, tools/docs/getting-started.md has the rest")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ttrpg", description=__doc__)
    sub = parser.add_subparsers(required=True)

    p = sub.add_parser("check", help="validate a campaign repository")
    p.add_argument("root", nargs="?", default=".")
    p.add_argument("--fix", action="store_true", help="mark edited AP notes as origin: modified")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("export-foundry", help="build a Foundry module with the campaign notes as journals")
    p.add_argument("--root", default=".")
    p.add_argument("--out", help="module directory (default .cache/foundry/<module-id>)")
    p.add_argument("--install", help="Foundry Data/modules directory to copy the module into")
    p.set_defaults(func=cmd_export_foundry)

    p = sub.add_parser("pull-foundry", help="bring journal pages edited in Foundry back into the notes")
    p.add_argument("world", help="Foundry world directory (Data/worlds/<id>)")
    p.add_argument("--root", default=".")
    p.set_defaults(func=cmd_pull_foundry)

    p = sub.add_parser("foundry", help="bring a running Foundry world up to date with the notes (through foundry-mcp)")
    p.add_argument("action", choices=["plan", "apply", "pull"])
    p.add_argument("--root", default=".")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=31414, help="foundry-mcp backend control port")
    p.add_argument("--force", action="store_true", help="apply even over pages edited in Foundry")
    p.set_defaults(func=cmd_foundry)

    p = sub.add_parser("rename", help="rename a note and update every link to it")
    p.add_argument("old")
    p.add_argument("new")
    p.add_argument("--root", default=".")
    p.set_defaults(func=cmd_rename)

    p = sub.add_parser("questions", help="what waits on the GM: open [!question], [!verify] and [!idea] callouts by note")
    p.add_argument("root", nargs="?", default=".")
    p.add_argument("--kind", nargs="+", choices=["question", "verify", "idea"], default=["question", "verify", "idea"])
    p.set_defaults(func=cmd_questions)

    p = sub.add_parser("maps", help="list maps by stage and places that still need one")
    p.add_argument("root", nargs="?", default=".")
    p.set_defaults(func=cmd_maps)

    p = sub.add_parser("glossary", help="write glossary.tsv: translated names of spells, items, creatures... (pathfinder-fr, Archives of Nethys)")
    p.add_argument("--root", default=".")
    p.set_defaults(func=cmd_glossary)

    p = sub.add_parser("drafts", help="draft a note for each subject of a compile inventory that has none")
    p.add_argument("--root", default=".")
    p.add_argument("--inventory", help="TSV: type, id, title, aliases, main_page, pages, tier (default .cache/compile/inventory.tsv)")
    p.set_defaults(func=cmd_drafts)

    p = sub.add_parser("import-foundry", help="import a Foundry Adventure module into notes")
    p.add_argument("--root", default=".")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--module", help="Foundry module directory (contains module.json)")
    group.add_argument("--json", help="Adventure document already unpacked to JSON")
    p.add_argument("--module-id", default="", help="map file to use with --json, e.g. pf2e-kingmaker")
    p.set_defaults(func=cmd_import_foundry)

    p = sub.add_parser("pdf-text", help="extract a source PDF for local reading and declare it")
    p.add_argument("source", help="short source id used in citations, e.g. km")
    p.add_argument("pdf")
    p.add_argument("--title", default="")
    p.add_argument("--root", default=".")
    p.set_defaults(func=cmd_pdf_text)

    p = sub.add_parser("library", help="the GM's PDF library shared by every campaign: index, list, search, page image")
    p.add_argument("action", choices=["index", "list", "search", "page"])
    p.add_argument("args", nargs="*", help="index: directories; list: words; search: regex; page: id and page number")
    p.add_argument("--book", action="append", help="search: only books whose id contains this (repeatable)")
    p.add_argument("--pages", action="store_true", help="search: one line per book with the pages that match")
    p.add_argument("--case", action="store_true", help="search: case-sensitive")
    p.add_argument("--limit", type=int, default=300, help="search: maximum matches")
    p.add_argument("--context", type=int, default=0, metavar="N", help="search: N lines before and after each match")
    p.add_argument("--dpi", type=int, default=110, help="page: resolution")
    p.add_argument("--text", action="store_true", help="page: print the page's extracted text instead of rendering it")
    p.add_argument("--library", help="default $TTRPG_LIBRARY or ~/.local/share/ttrpg/library")
    p.set_defaults(func=cmd_library)

    p = sub.add_parser("aon", help="search Archives of Nethys (rules, creatures, deities...): name, book and page, URL")
    p.add_argument("query", nargs="+")
    p.add_argument("--category", help="e.g. deity, creature, spell, rules, organization")
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(func=cmd_aon)

    p = sub.add_parser("creatures", help="creatures by level and trait with their XP for the party and compendium link")
    p.add_argument("--index", metavar="PF2E_SYSTEM_DIR", help="build the index from a Foundry pf2e system directory (once)")
    p.add_argument("--level", help="level or range, e.g. 3 or 1-5 (default: party level -4 to +4)")
    p.add_argument("--trait", action="append", default=[], help="required trait (repeatable), e.g. undead")
    p.add_argument("--name", help="part of the name")
    p.add_argument("--rarity", choices=["common", "uncommon", "rare", "unique"])
    p.add_argument("--pack", action="append", default=[], help="part of the compendium name, e.g. monster-core")
    p.add_argument("--hazards", action="store_true", help="hazards instead of creatures (no XP computed)")
    p.add_argument("--party", type=int, help="number of PCs (default campaign.yaml party, else 4)")
    p.add_argument("--party-level", type=int, help="default: the latest session's level")
    p.add_argument("--limit", type=int, default=60)
    p.add_argument("--root", default=".")
    p.set_defaults(func=cmd_creatures)

    p = sub.add_parser("hexmap", help="put PathfinderWiki's named places on the hexes of an official region map")
    p.add_argument("--control", action="append", required=True, metavar="NAME=X,Y",
                   help="a town on both maps and its pixel on the map image (three or more)")
    p.add_argument("--size", type=float, required=True, help="the scene's grid size (hex height, px)")
    p.add_argument("--origin", required=True, help="image origin in the scene, X,Y (create-scene imageOrigin)")
    p.add_argument("--image", required=True, help="map image size, WxH")
    p.add_argument("--px-per-mile", type=float, help="report the fit error in miles")
    p.set_defaults(func=cmd_hexmap)

    p = sub.add_parser("source", help="declare library books as sources (cite as src:<id>#p<N>); "
                       "excerpts: commit the text of cited pages in sources/ for agents without the library")
    p.add_argument("action", choices=["add", "excerpts"])
    p.add_argument("books", nargs="*", help="library ids (ttrpg library list), each optionally id=alias")
    p.add_argument("--as", dest="alias", help="citation id in this campaign, e.g. km")
    p.add_argument("--root", default=".")
    p.add_argument("--library")
    p.set_defaults(func=cmd_source_add)

    p = sub.add_parser("transcribe", help="transcribe per-speaker session tracks locally into sessions/<day>/")
    p.add_argument("audio", nargs="+", help="audio files, a directory (Craig export, probe capture) or a Craig zip")
    p.add_argument("--names", nargs="*", default=[], metavar="TRACK=NAME", help="e.g. speaker-001=Hugo 1-alice=Alice")
    p.add_argument("--day", help="real-world session day (default: the Craig start time, else today)")
    p.add_argument("--language", help="default: campaign.yaml language")
    p.add_argument("--model", default=os.environ.get("TTRPG_WHISPER_MODEL", session.MODEL), help="faster-whisper model name or directory")
    p.add_argument("--root", default=".")
    p.set_defaults(func=cmd_transcribe)

    p = sub.add_parser("flight", help="summarize a Foundry Flight Recorder session into sessions/<day>/")
    p.add_argument("session", nargs="?", default="latest", help="ffr session id, prefix or latest")
    p.add_argument("--db", help="ffr database (default $FFR_DB)")
    p.add_argument("--ffr", default=os.environ.get("FFR", "ffr"), help="ffr command")
    p.add_argument("--day", help="default: the session's start date")
    p.add_argument("--root", default=".")
    p.set_defaults(func=cmd_flight)

    p = sub.add_parser("new", help="create a campaign repository")
    p.add_argument("root")
    p.add_argument("--name", required=True)
    p.add_argument("--system", default="pf2e")
    p.add_argument("--language", default="fr")
    p.add_argument("--calendar", default="golarion")
    p.add_argument("--start", default="", help='in-game date play begins, e.g. "4710-03-01"')
    p.add_argument("--tools-url", help="Git URL of this tools repository (default: this copy's origin)")
    p.set_defaults(func=cmd_new)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
