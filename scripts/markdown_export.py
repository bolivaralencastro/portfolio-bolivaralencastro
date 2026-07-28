"""Generate plain-Markdown twins of public HTML pages for agent content negotiation.

Every public page exposes a sibling `.md` file (e.g. /about.html -> /about.md) built
from the same `<main id="main">` content that ships in the HTML, so agents that
request `Accept: text/markdown` or fetch the `.md` URL directly get a clean,
dependency-free representation. No third-party HTML parser is used here on purpose:
the build pipeline runs with the stdlib only in CI (see .github/workflows).
"""

from __future__ import annotations

import html as html_lib
import re
from html.parser import HTMLParser
from urllib.parse import urljoin

_SKIP_TAGS = {"script", "style", "svg", "button", "form", "input", "select", "textarea", "template", "nav"}
_BLOCK_TAGS = {"p", "div", "section", "article", "header", "footer", "aside", "figure", "figcaption", "blockquote", "li"}
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
_WS_RE = re.compile(r"[ \t\r\n]+")
_BLANK_RE = re.compile(r"\n{3,}")

_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
_MAIN_START_RE = re.compile(r'<main\b[^>]*\bid=["\']main["\'][^>]*>')


class _MarkdownConverter(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self._base_url = base_url
        self._out: list[str] = []
        self._skip_depth = 0
        self._pre_depth = 0
        self._list_stack: list[str] = []
        self._link_stack: list[tuple[str, int]] = []

    def _emit(self, text: str) -> None:
        if self._skip_depth:
            return
        self._out.append(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag in _HEADING_TAGS:
            level = int(tag[1])
            self._emit("\n\n" + "#" * level + " ")
        elif tag == "li":
            marker = "1." if (self._list_stack and self._list_stack[-1] == "ol") else "-"
            depth = max(len(self._list_stack) - 1, 0)
            self._emit("\n" + ("  " * depth) + f"{marker} ")
        elif tag in ("ul", "ol"):
            self._list_stack.append(tag)
            self._emit("\n")
        elif tag in _BLOCK_TAGS:
            self._emit("\n\n")
        elif tag == "br":
            self._emit("\n")
        elif tag == "hr":
            self._emit("\n\n---\n\n")
        elif tag == "pre":
            self._pre_depth += 1
            self._emit("\n\n```\n")
        elif tag == "code" and not self._pre_depth:
            self._emit("`")
        elif tag in ("strong", "b"):
            self._emit("**")
        elif tag in ("em", "i"):
            self._emit("*")
        elif tag == "a":
            href = attrs_dict.get("href") or ""
            self._link_stack.append((href, len(self._out)))
        elif tag == "img":
            alt = (attrs_dict.get("alt") or "").strip()
            src = attrs_dict.get("src") or ""
            if src:
                self._emit(f"![{alt}]({urljoin(self._base_url, src)})")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS:
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag in ("ul", "ol"):
            if self._list_stack:
                self._list_stack.pop()
            self._emit("\n")
        elif tag == "pre":
            self._pre_depth = max(self._pre_depth - 1, 0)
            self._emit("\n```\n\n")
        elif tag == "code" and not self._pre_depth:
            self._emit("`")
        elif tag in ("strong", "b"):
            self._emit("**")
        elif tag in ("em", "i"):
            self._emit("*")
        elif tag == "a" and self._link_stack:
            href, start = self._link_stack.pop()
            text = "".join(self._out[start:]).strip()
            del self._out[start:]
            if text and href:
                self._out.append(f"[{text}]({urljoin(self._base_url, href)})")
            elif text:
                self._out.append(text)

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._pre_depth:
            self._out.append(data)
            return
        collapsed = _WS_RE.sub(" ", data)
        if collapsed.strip() == "" and collapsed != " ":
            return
        self._out.append(collapsed)

    def result(self) -> str:
        text = "".join(self._out)
        text = _BLANK_RE.sub("\n\n", text)
        return text.strip() + "\n"


def _extract_main_fragment(page_html: str) -> str | None:
    match = _MAIN_START_RE.search(page_html)
    if not match:
        return None
    end = page_html.rfind("</main>")
    if end == -1 or end < match.end():
        return None
    return page_html[match.end():end]


def html_page_to_markdown(page_html: str, canonical_url: str) -> str | None:
    """Convert one rendered public page to a Markdown document, or None if it has no <main id="main">."""
    fragment = _extract_main_fragment(page_html)
    if fragment is None:
        return None

    title_match = _TITLE_RE.search(page_html)
    title = html_lib.unescape(title_match.group(1)).strip() if title_match else ""

    converter = _MarkdownConverter(canonical_url)
    converter.feed(fragment)
    converter.close()
    body = converter.result()

    header_lines = [] if body.startswith("# ") else ([f"# {title}"] if title else [])
    header_lines.append(f"Source: {canonical_url}")
    return "\n".join(header_lines) + "\n\n" + body


def inject_markdown_alternate_link(page_html: str, markdown_href: str) -> str:
    """Insert a <link rel="alternate" type="text/markdown"> before </head> if not already present."""
    if "type=\"text/markdown\"" in page_html:
        return page_html
    tag = f'  <link rel="alternate" type="text/markdown" href="{markdown_href}">\n'
    marker = "</head>"
    idx = page_html.find(marker)
    if idx == -1:
        return page_html
    return page_html[:idx] + tag + page_html[idx:]
