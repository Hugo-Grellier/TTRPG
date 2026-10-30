"""ttrpg: tools for campaign repositories. Run `ttrpg <command> --help`."""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from . import check as checker
from .foundry_import import import_adventure, import_module
from .rename import rename

TOOLS = Path(__file__).resolve().parent.parent


def cmd_check(args):
    _, report = checker.check(args.root, fix=args.fix)
    if report.items:
        print(report)
    notes = len(checker.vault.load(args.root).notes)
    print(f"{notes} notes, {len(report.errors)} errors, {len(report.items) - len(report.errors)} warnings")
    return 1 if report.errors else 0


def cmd_rename(args):
    changed = rename(args.root, args.old, args.new)
    print(f"{args.old} -> {args.new}; links updated in {changed} notes")
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
    out = Path(args.root) / ".cache" / "sources" / args.source
    out.mkdir(parents=True, exist_ok=True)
    text = subprocess.run(["pdftotext", "-enc", "UTF-8", args.pdf, "-"], capture_output=True, check=True).stdout.decode("utf-8", "replace")
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    for number, page in enumerate(pages, 1):
        (out / f"p{number:03}.txt").write_text(page, encoding="utf-8")
    config_path = Path(args.root) / "campaign.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config.setdefault("sources", {}).setdefault(args.source, {})
    config["sources"][args.source].update({"title": args.title or Path(args.pdf).stem, "pages": len(pages)})
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"{len(pages)} pages in {out}; cite as src:{args.source}#p<N>")
    return 0


def cmd_new(args):
    root = Path(args.root)
    if root.exists() and any(root.iterdir()):
        raise SystemExit(f"{root} is not empty")
    shutil.copytree(TOOLS / "template", root, dirs_exist_ok=True)
    config = {"name": args.name, "system": args.system, "language": args.language,
              "calendar": args.calendar, "start": args.start or None, "sources": {}}
    (root / "campaign.yaml").write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    run = lambda *command: subprocess.run(command, cwd=root, check=True)
    run("git", "init", "-q", "-b", "main")
    run("git", "-c", "protocol.file.allow=always", "submodule", "add", "-q", args.tools_url, "tools")
    for skills in (".claude/skills", ".agents/skills"):
        (root / skills).parent.mkdir(exist_ok=True)
        (root / skills).symlink_to(Path("../tools/skills"))
    run("git", "config", "core.hooksPath", ".githooks")
    print(f"campaign repository ready in {root}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ttrpg", description=__doc__)
    sub = parser.add_subparsers(required=True)

    p = sub.add_parser("check", help="validate a campaign repository")
    p.add_argument("root", nargs="?", default=".")
    p.add_argument("--fix", action="store_true", help="mark edited AP notes as origin: modified")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("rename", help="rename a note and update every link to it")
    p.add_argument("old")
    p.add_argument("new")
    p.add_argument("--root", default=".")
    p.set_defaults(func=cmd_rename)

    p = sub.add_parser("maps", help="list maps by stage and places that still need one")
    p.add_argument("root", nargs="?", default=".")
    p.set_defaults(func=cmd_maps)

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

    p = sub.add_parser("new", help="create a campaign repository")
    p.add_argument("root")
    p.add_argument("--name", required=True)
    p.add_argument("--system", default="pf2e")
    p.add_argument("--language", default="fr")
    p.add_argument("--calendar", default="golarion")
    p.add_argument("--start", default="", help='in-game date play begins, e.g. "4710-03-01"')
    p.add_argument("--tools-url", required=True, help="Git URL of this tools repository")
    p.set_defaults(func=cmd_new)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
