"""The GM's source library: every PDF they own, extracted once to text per page and shared by all
campaigns. A campaign cites a book as `src:<id>#p<N>` after declaring it with `ttrpg source add`.

Layout: `<library>/catalog.yaml` (id -> title, path, pages, size, mtime) and `<library>/<id>/pNNN.txt`.
Ids are derived from file names and kept in the catalog, so citations survive a re-index.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

from .foundry_import import slug

NUMBERING = re.compile(r"^\s*(\[[A-Z]+\d+\]|#?\d+(-\d+)?\.)\s*")


def location():
    if os.environ.get("TTRPG_LIBRARY"):
        return Path(os.environ["TTRPG_LIBRARY"])
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "ttrpg" / "library"


def load(library):
    path = library / "catalog.yaml"
    return (yaml.safe_load(path.read_text(encoding="utf-8")) or {}) if path.is_file() else {}


def save(library, catalog):
    library.mkdir(parents=True, exist_ok=True)
    (library / "catalog.yaml").write_text(yaml.safe_dump(dict(sorted(catalog.items())), allow_unicode=True, sort_keys=False), encoding="utf-8")


def title(path):
    return NUMBERING.sub("", Path(path).stem).strip()


def new_id(rel, taken):
    """File name without its numbering; parent folders prepended until unique."""
    parts = [slug(NUMBERING.sub("", part)) for part in (*rel.parent.parts, rel.stem)]
    for depth in range(1, len(parts) + 1):
        candidate = "-".join(parts[-depth:])
        if candidate not in taken:
            return candidate
    n = 2
    while f"{candidate}-{n}" in taken:
        n += 1
    return f"{candidate}-{n}"


def pdf_pages(pdf):
    text = subprocess.run(["pdftotext", "-enc", "UTF-8", str(pdf), "-"], capture_output=True, check=True).stdout.decode("utf-8", "replace")
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    return pages


def mostly_images(pages):
    """A scanned book: more than half of its pages carry no text layer (map folios are under that)."""
    return len(pages) >= 4 and sum(len(page.strip()) < 40 for page in pages) * 2 > len(pages)


def ocr(pdf):
    """Pages of the PDF after OCR of its image-only pages (ocrmypdf, English and French), or None without ocrmypdf."""
    if not shutil.which("ocrmypdf"):
        return None
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "ocr.pdf"
        subprocess.run(["ocrmypdf", "--skip-text", "-l", "eng+fra", "--jobs", "4", "--output-type", "pdf", "-q", str(pdf), str(out)],
                       check=True, capture_output=True)
        return pdf_pages(out)


def extract(pdf, out):
    """Write one text file per page (p001.txt...) and return the page count. Scanned books go through OCR."""
    pages = pdf_pages(pdf)
    if mostly_images(pages):
        print(f"{Path(pdf).name}: image-only pages, OCR...", file=sys.stderr)
        pages = ocr(pdf) or pages
        if mostly_images(pages):
            print(f"{Path(pdf).name}: still no text (install ocrmypdf and tesseract)", file=sys.stderr)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("p*.txt"):
        old.unlink()
    for number, page in enumerate(pages, 1):
        (out / f"p{number:03}.txt").write_text(page, encoding="utf-8")
    return len(pages)


def index(library, roots, extract=extract, log=print):
    """Add every PDF under roots to the catalog; extract new or changed files. Returns the catalog."""
    catalog = load(library)
    by_path = {entry["path"]: book for book, entry in catalog.items()}
    todo = []
    for root in map(Path, roots):
        for pdf in sorted(root.resolve().rglob("*")):
            if pdf.suffix.lower() != ".pdf" or not pdf.is_file():
                continue
            stat = pdf.stat()
            book = by_path.get(str(pdf)) or new_id(pdf.relative_to(root.resolve()), catalog)
            entry = catalog.setdefault(book, {"title": title(pdf), "path": str(pdf)})
            by_path[str(pdf)] = book
            if (entry.get("size"), entry.get("mtime")) != (stat.st_size, int(stat.st_mtime)) or not (library / book).is_dir():
                entry.update(size=stat.st_size, mtime=int(stat.st_mtime))
                todo.append(book)

    def run(book):
        try:
            catalog[book]["pages"] = extract(catalog[book]["path"], library / book)
        except (subprocess.CalledProcessError, OSError) as error:
            catalog[book].pop("size", None)  # retried next time
            log(f"{book}: extraction failed ({error})")

    with ThreadPoolExecutor(os.cpu_count() or 4) as pool:
        for done, _ in enumerate(pool.map(run, todo), 1):
            if done % 25 == 0:
                log(f"{done}/{len(todo)} extracted")
    save(library, catalog)
    missing = [book for book, entry in catalog.items() if not Path(entry["path"]).is_file()]
    log(f"{len(catalog)} books ({len(todo)} extracted){f'; files gone, kept for citations: {missing}' if missing else ''}")
    return catalog


def search(library, pattern, books=None, ignore_case=True, context=0):
    """Yield (book, page, line) for each line matching the regex, books in catalog order; with context,
    line is the matching line and the `context` lines around it, joined by newlines."""
    regex = re.compile(pattern, re.IGNORECASE if ignore_case else 0)
    for book in sorted(load(library)):
        if books and not any(part in book for part in books):
            continue
        for page in sorted((library / book).glob("p*.txt")):
            lines = page.read_text(encoding="utf-8").splitlines()
            matches = [n for n, line in enumerate(lines) if regex.search(line)]
            if not context:
                for n in matches:
                    yield book, int(page.stem[1:]), lines[n].strip()
                continue
            # Matches whose context overlaps share one block.
            blocks = []
            for n in matches:
                start, end = max(0, n - context), n + context + 1
                if blocks and start <= blocks[-1][1]:
                    blocks[-1][1] = end
                else:
                    blocks.append([start, end])
            for start, end in blocks:
                yield book, int(page.stem[1:]), "\n".join(part.strip() for part in lines[start:end])


def render_page(library, book, page, dpi=110):
    """PNG of one page (maps, layouts the text loses), cached beside the text."""
    entry = load(library)[book]
    out = library / book / "img" / f"p{page:03}"
    if not out.with_suffix(".png").is_file():
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["pdftoppm", "-png", "-singlefile", "-r", str(dpi), "-f", str(page), "-l", str(page), entry["path"], str(out)], check=True)
    return out.with_suffix(".png")


def declare(root, library, book, alias=None):
    """Declare a library book as a source of the campaign and link its text into .cache/sources/."""
    entry = load(library).get(book)
    if not entry or "pages" not in entry:
        raise KeyError(book)
    alias = alias or book
    config_path = Path(root) / "campaign.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    for other, declared in (config.get("sources") or {}).items():
        if other != alias and (declared or {}).get("library", other) == book:
            return f"{book}: already declared as {other}; cite src:{other}#p<N>"
    source = config.setdefault("sources", {}).setdefault(alias, {})
    source.update({"title": entry["title"], "pages": entry["pages"]})
    if alias != book:
        source["library"] = book
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    link = Path(root) / ".cache" / "sources" / alias
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink():
        link.unlink()
    if link.exists():
        return f"{alias}: declared; {link} already holds its own text, left as is"
    link.symlink_to(library / book, target_is_directory=True)
    return f"{alias}: {entry['title']}, {entry['pages']} pages; cite as src:{alias}#p<N>"


def aon(query, category=None, size=10, fetch=None):
    """Archives of Nethys entries matching the query: (name, category, sources, url, summary, edition)."""
    from .glossary import AON, fetch as get
    match = {"multi_match": {"query": query, "fields": ["name^4", "text"]}}
    body = {"size": size, "query": {"bool": {"must": [match], **({"filter": [{"term": {"category": category}}]} if category else {})}}}
    for hit in (fetch or get)(AON, None, body)["hits"]["hits"]:
        doc = hit["_source"]
        sources = doc.get("source_raw") or doc.get("source") or []
        edition = "legacy" if doc.get("remaster_id") else "remaster" if doc.get("legacy_id") else ""
        yield (doc.get("name", ""), doc.get("category", ""), ", ".join(sources if isinstance(sources, list) else [sources]),
               "https://2e.aonprd.com" + doc.get("url", ""), " ".join((doc.get("summary") or "").split()), edition)


def excerpts(campaign):
    """Copy the text of every cited page into sources/<id>/pNNN.txt (committed, for agents without the
    library) and drop the pages no longer cited. A page whose text is not in .cache/sources/ is left as is."""
    from .vault import SOURCE
    root = Path(campaign.root)
    cited = {(m[1], int(m[2])) for note in campaign.notes.values() for m in SOURCE.finditer(note.body)}
    written, missing, removed = 0, [], 0
    for book, page in sorted(cited):
        name = f"p{page:03d}.txt"
        src, dst = root / ".cache" / "sources" / book / name, root / "sources" / book / name
        if src.is_file():
            text = src.read_text(encoding="utf-8")
            if not dst.is_file() or dst.read_text(encoding="utf-8") != text:
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(text, encoding="utf-8")
                written += 1
        elif not dst.is_file():
            missing.append(f"{book}#p{page}")
    for path in (root / "sources").glob("*/p*.txt"):
        if (path.parent.name, int(path.stem[1:])) not in cited:
            path.unlink()
            removed += 1
    return written, removed, missing
