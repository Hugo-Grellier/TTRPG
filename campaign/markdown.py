"""Safe Markdown rendering with source-line anchors for review comments."""

from html.parser import HTMLParser

from markdown_it import MarkdownIt


_parser = MarkdownIt("commonmark", {"html": False}).enable("table")


def render_markdown(source):
    return _parser.render(source)


def render_blocks(source):
    tokens = _parser.parse(source)
    starts = [i for i, token in enumerate(tokens) if token.level == 0 and token.map and token.nesting >= 0]
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(tokens)
        first, last = tokens[start].map
        yield first + 1, last, _parser.renderer.render(tokens[start:end], _parser.options, {})


class _VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in ("br", "p", "li", "h1", "h2", "h3", "h4", "h5", "h6"):
            self.parts.append(" ")


def visible_text(source):
    parser = _VisibleText()
    parser.feed(_parser.render(source))
    return " ".join("".join(parser.parts).split())
