"""Foundry journal HTML to readable Markdown. Enrichers such as @UUID and @Check pass through as text."""

import re
from html import unescape
from html.parser import HTMLParser

BLOCK = {"p", "div", "section", "article", "aside", "header", "footer", "figure", "figcaption", "blockquote",
         "ul", "ol", "li", "table", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "br", "dl", "dt", "dd"}
LISTED = re.compile(r"\s*(-|\d+\.) ")
CALLOUT = {"sidebar": "note", "milestone": "info", "read-aloud": "quote", "readaloud": "quote", "gm": "secret"}


class _Converter(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []          # finished blocks
        self.line = []         # inline text of the current block
        self.lists = []        # stack of "ul"/"ol" counters
        self.quote = []        # stack of callout kinds (None for plain blockquote)
        self.table = None      # list of rows while inside a table
        self.row = None
        self.cell = None
        self.heading = 0
        self.href = []

    # -- output helpers
    def flush(self):
        text = re.sub(r"[ \t]+", " ", "".join(self.line)).strip()
        self.line = []
        if not text:
            return
        if self.heading:
            text = "#" * self.heading + " " + text
        elif self.lists:
            indent = "  " * (len(self.lists) - 1)
            kind = self.lists[-1]
            marker = f"{kind}." if isinstance(kind, int) else "-"
            text = f"{indent}{marker} {text}"
        if self.quote:
            text = "\n".join("> " + part for part in text.split("\n"))
        self.out.append(text)

    def write(self, text):
        if self.cell is not None:
            self.cell.append(text)
        else:
            self.line.append(text)

    # -- parser events
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set((attrs.get("class") or "").split())
        if tag in BLOCK and self.cell is None:
            self.flush()
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.heading = int(tag[1])
        elif tag == "ul":
            self.lists.append("ul")
        elif tag == "ol":
            self.lists.append(0)
        elif tag == "li" and self.lists and isinstance(self.lists[-1], int):
            self.lists[-1] += 1
        elif tag in ("blockquote", "section", "aside", "div"):
            kind = next((CALLOUT[name] for name in classes if name in CALLOUT), None)
            if tag == "blockquote" or kind:
                self.quote.append(kind)
                if kind:
                    self.out.append(f"> [!{kind}]")
            elif tag != "div":
                self.quote.append(False)
        elif tag == "table":
            self.table = []
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []
        elif tag in ("strong", "b"):
            self.write("**")
        elif tag in ("em", "i"):
            self.write("*")
        elif tag == "a":
            href = attrs.get("href") or ""
            href = "" if href.startswith("#") else href
            self.href.append(href)
            if href:
                self.write("[")
        elif tag == "img" and attrs.get("src"):
            src = attrs["src"].replace("\\", "/")
            self.write(f"![{attrs.get('alt') or ''}]({src})")
        elif tag == "br":
            self.write("\n")
        elif tag == "hr":
            self.out.append("---")

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(re.sub(r"\s+", " ", "".join(self.cell)).strip().replace("|", "\\|"))
            self.cell = None
            return
        if tag == "tr" and self.row is not None:
            self.table.append(self.row)
            self.row = None
            return
        if tag == "table" and self.table is not None:
            self.out.append(markdown_table(self.table))
            self.table = None
            return
        if tag in ("strong", "b"):
            self.write("**")
        elif tag in ("em", "i"):
            self.write("*")
        elif tag == "a" and self.href:
            href = self.href.pop()
            if href:
                self.write(f"]({href})")
        if tag in BLOCK and self.cell is None:
            self.flush()
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.heading = 0
        elif tag in ("ul", "ol") and self.lists:
            self.lists.pop()
        elif tag in ("blockquote", "section", "aside") and self.quote:
            self.quote.pop()
        elif tag == "div" and self.quote and self.quote[-1]:
            self.quote.pop()

    def handle_data(self, data):
        self.write(data if self.cell is not None else data.replace("\n", " "))


def markdown_table(rows):
    rows = [row for row in rows if row]
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    rows = [row + [""] * (width - len(row)) for row in rows]
    lines = ["| " + " | ".join(rows[0]) + " |", "|" + " --- |" * width]
    lines += ["| " + " | ".join(row) + " |" for row in rows[1:]]
    return "\n".join(lines)


def to_markdown(html):
    converter = _Converter()
    converter.feed(unescape(html) if "&lt;" in html and "<" not in html else html)
    converter.close()
    converter.flush()
    text = ""
    for block in filter(None, converter.out):
        tight = text and (LISTED.match(block) and LISTED.match(text.rsplit("\n", 1)[-1])
                          or block.startswith(">") and text.rsplit("\n", 1)[-1].startswith(">"))
        text += ("\n" if tight else "\n\n") + block if text else block
    text = re.sub(r"(?<!!)\[\]\(([^)]*)\)", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
