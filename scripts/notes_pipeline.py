#!/usr/bin/env python3
"""Load Markdown note sources and render the notes section for now.html."""

from __future__ import annotations

import datetime as dt
import html
import pathlib
import re
import shlex
import unicodedata
from dataclasses import dataclass, field
from urllib.parse import urlparse

NOTE_SOURCE_DIR = pathlib.Path("content/notes")
NOTE_AUTO_BLOCK = "now-notes"
NOTE_DEFAULT_CATEGORY = "Nota"
NOTE_MONTHS_PT = ("Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez")
SHORTCODE_PATTERN = re.compile(r"^\{\{\s*(?P<name>[a-z][a-z0-9_-]*)\s*(?P<attrs>.*?)\s*\}\}$")
DATE_PREFIX_PATTERN = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})(?:-(?P<slug>.+))?$")


class NoteError(RuntimeError):
    """Raised when a note source cannot be parsed or rendered safely."""


@dataclass
class NoteSource:
    path: pathlib.Path
    rel_path: str
    date: dt.date
    slug: str
    category: str
    status: str
    title: str = ""
    classes: list[str] = field(default_factory=list)
    body_markdown: str = ""

    @property
    def article_id(self) -> str:
        return f"now-{self.date.isoformat()}-{self.slug}"

    @property
    def permalink(self) -> str:
        return f"/now.html#{self.article_id}"


def note_source_dir(repo_root: pathlib.Path) -> pathlib.Path:
    return repo_root / NOTE_SOURCE_DIR


def load_notes(repo_root: pathlib.Path, *, include_drafts: bool = False) -> list[NoteSource]:
    notes_dir = note_source_dir(repo_root)
    if not notes_dir.exists():
        return []

    notes: list[NoteSource] = []
    seen_ids: set[str] = set()

    for path in sorted(notes_dir.glob("*.md")):
        if path.name.startswith("_") or path.stem.lower() == "readme":
            continue

        note = parse_note_file(path, repo_root)
        if note.article_id in seen_ids:
            raise NoteError(f"{note.rel_path}: duplicate note permalink '{note.article_id}'")
        seen_ids.add(note.article_id)

        if note.status == "draft" and not include_drafts:
            continue

        render_note_body_html(note, repo_root)
        notes.append(note)

    notes.sort(key=lambda item: (item.date, item.rel_path), reverse=True)
    return notes


def generate_now_notes_html(repo_root: pathlib.Path) -> str:
    return render_now_notes_html(load_notes(repo_root), repo_root)


def parse_note_file(path: pathlib.Path, repo_root: pathlib.Path) -> NoteSource:
    rel_path = path.relative_to(repo_root).as_posix()
    raw = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    metadata, body = split_front_matter(raw, rel_path)

    date_value = metadata.get("date") or infer_date_from_filename(path.stem)
    if not date_value:
        raise NoteError(f"{rel_path}: missing date (front matter 'date' or YYYY-MM-DD filename prefix)")
    try:
        note_date = dt.date.fromisoformat(date_value)
    except ValueError as exc:
        raise NoteError(f"{rel_path}: invalid date '{date_value}', expected YYYY-MM-DD") from exc

    title = metadata.get("title", "").strip()
    slug_source = metadata.get("slug") or infer_slug_from_filename(path.stem) or title
    slug = slugify(slug_source)
    if not slug:
        raise NoteError(f"{rel_path}: missing slug (front matter 'slug', filename suffix, or title)")

    category = metadata.get("category", NOTE_DEFAULT_CATEGORY).strip() or NOTE_DEFAULT_CATEGORY
    status = metadata.get("status", "published").strip().lower() or "published"
    if status not in {"published", "draft"}:
        raise NoteError(f"{rel_path}: unsupported status '{status}' (use 'published' or 'draft')")

    class_tokens = []
    for token in re.split(r"[\s,]+", metadata.get("classes", "").strip()):
        normalized = token.strip()
        if normalized:
            class_tokens.append(normalized)

    body_markdown = body.strip()
    if not body_markdown:
        raise NoteError(f"{rel_path}: note body is empty")

    return NoteSource(
        path=path,
        rel_path=rel_path,
        date=note_date,
        slug=slug,
        category=category,
        status=status,
        title=title,
        classes=class_tokens,
        body_markdown=body_markdown,
    )


def split_front_matter(raw: str, rel_path: str) -> tuple[dict[str, str], str]:
    if not raw.startswith("---\n"):
        return {}, raw

    marker = "\n---\n"
    end_idx = raw.find(marker, 4)
    if end_idx == -1:
        raise NoteError(f"{rel_path}: front matter is missing closing '---'")

    block = raw[4:end_idx]
    body = raw[end_idx + len(marker):]
    metadata: dict[str, str] = {}

    for line_number, line in enumerate(block.splitlines(), start=2):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in line:
            raise NoteError(f"{rel_path}:{line_number}: invalid front matter line '{line}'")
        key, value = line.split(":", 1)
        key = key.strip().lower().replace("-", "_")
        value = strip_quotes(value.strip())
        metadata[key] = value

    return metadata, body


def strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def infer_date_from_filename(stem: str) -> str:
    match = DATE_PREFIX_PATTERN.match(stem)
    if not match:
        return ""
    return match.group("date") or ""


def infer_slug_from_filename(stem: str) -> str:
    match = DATE_PREFIX_PATTERN.match(stem)
    if match:
        return (match.group("slug") or "").strip("-_ ")
    return stem


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    collapsed = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_only.lower()).strip("-")
    return re.sub(r"-{2,}", "-", collapsed)


def format_note_date(date_value: dt.date) -> str:
    return f"{date_value.day:02d} {NOTE_MONTHS_PT[date_value.month - 1]} {date_value.year}"


def render_now_notes_html(notes: list[NoteSource], repo_root: pathlib.Path) -> str:
    if not notes:
        return '        <p class="note-empty">Nenhuma nota publicada ainda.</p>'

    blocks: list[str] = []
    for note in notes:
        classes = ["note", "h-entry", *note.classes]
        block_lines = [f'        <article id="{note.article_id}" class="{" ".join(classes)}">']
        if note.title:
            block_lines.append(f'          <p class="visually-hidden p-name">{html.escape(note.title)}</p>')
        block_lines.append('          <div class="e-content">')
        block_lines.append(indent_block(render_note_body_html(note, repo_root), "            "))
        block_lines.append("          </div>")
        block_lines.extend(
            [
                '          <footer class="note-meta">',
                f'            <span class="p-category">{html.escape(note.category)}</span>',
                f'            <time class="dt-published" datetime="{note.date.isoformat()}">{format_note_date(note.date)}</time>',
                f'            <a class="u-url" href="{note.permalink}">permalink</a>',
                "          </footer>",
                "        </article>",
            ]
        )
        blocks.append("\n".join(block_lines))

    return "\n\n".join(blocks)


def render_note_body_html(note: NoteSource, repo_root: pathlib.Path) -> str:
    lines = note.body_markdown.splitlines()
    html_blocks: list[str] = []
    paragraph_lines: list[str] = []
    list_mode: str | None = None
    list_items: list[str] = []
    quote_lines: list[str] = []
    raw_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if paragraph_lines:
            text = " ".join(chunk.strip() for chunk in paragraph_lines if chunk.strip())
            html_blocks.append(f"<p>{render_inline_markdown(text)}</p>")
            paragraph_lines = []

    def flush_list() -> None:
        nonlocal list_mode, list_items
        if list_mode and list_items:
            items_html = "".join(f"<li>{render_inline_markdown(item)}</li>" for item in list_items)
            html_blocks.append(f"<{list_mode}>{items_html}</{list_mode}>")
        list_mode = None
        list_items = []

    def flush_quote() -> None:
        nonlocal quote_lines
        if quote_lines:
            text = " ".join(chunk.strip() for chunk in quote_lines if chunk.strip())
            html_blocks.append(f"<blockquote><p>{render_inline_markdown(text)}</p></blockquote>")
            quote_lines = []

    def flush_raw() -> None:
        nonlocal raw_lines
        if raw_lines:
            html_blocks.append("\n".join(raw_lines))
            raw_lines = []

    for line in lines:
        stripped = line.strip()
        shortcode_match = SHORTCODE_PATTERN.match(stripped)
        unordered_match = re.match(r"^[-*]\s+(.*)$", stripped)
        ordered_match = re.match(r"^\d+\.\s+(.*)$", stripped)

        if not stripped:
            flush_paragraph()
            flush_list()
            flush_quote()
            flush_raw()
            continue

        if shortcode_match:
            flush_paragraph()
            flush_list()
            flush_quote()
            flush_raw()
            html_blocks.append(render_shortcode(shortcode_match.group("name"), shortcode_match.group("attrs"), note, repo_root))
            continue

        if stripped.startswith("<"):
            flush_paragraph()
            flush_list()
            flush_quote()
            raw_lines.append(line)
            continue

        if unordered_match:
            flush_paragraph()
            flush_quote()
            flush_raw()
            if list_mode not in {None, "ul"}:
                flush_list()
            list_mode = "ul"
            list_items.append(unordered_match.group(1).strip())
            continue

        if ordered_match:
            flush_paragraph()
            flush_quote()
            flush_raw()
            if list_mode not in {None, "ol"}:
                flush_list()
            list_mode = "ol"
            list_items.append(ordered_match.group(1).strip())
            continue

        if stripped.startswith("> "):
            flush_paragraph()
            flush_list()
            flush_raw()
            quote_lines.append(stripped[2:].strip())
            continue

        flush_list()
        flush_quote()
        flush_raw()
        paragraph_lines.append(stripped)

    flush_paragraph()
    flush_list()
    flush_quote()
    flush_raw()

    return "\n".join(html_blocks)


def render_shortcode(name: str, attrs_raw: str, note: NoteSource, repo_root: pathlib.Path) -> str:
    attrs = parse_shortcode_attrs(attrs_raw, note.rel_path)
    normalized_name = name.strip().lower()

    if normalized_name in {"image", "figure"}:
        src = require_attr(attrs, "src", note.rel_path, normalized_name)
        alt = require_attr(attrs, "alt", note.rel_path, normalized_name)
        validate_media_src(src, note.rel_path, repo_root)
        width = optional_numeric_attr(attrs, "width", note.rel_path, normalized_name)
        height = optional_numeric_attr(attrs, "height", note.rel_path, normalized_name)
        loading = attrs.get("loading", "lazy").strip() or "lazy"
        if loading not in {"lazy", "eager"}:
            raise NoteError(f"{note.rel_path}: shortcode '{normalized_name}' has invalid loading '{loading}'")
        caption = attrs.get("caption", "").strip()
        size_attrs = ""
        if width:
            size_attrs += f' width="{width}"'
        if height:
            size_attrs += f' height="{height}"'
        figure_lines = [
            '<figure class="note-media">',
            f'  <img src="{html.escape(src, quote=True)}" alt="{html.escape(alt, quote=True)}"{size_attrs} loading="{loading}" decoding="async">',
        ]
        if caption:
            figure_lines.append(f"  <figcaption>{render_inline_markdown(caption)}</figcaption>")
        figure_lines.append("</figure>")
        return "\n".join(figure_lines)

    if normalized_name == "audio":
        src = require_attr(attrs, "src", note.rel_path, normalized_name)
        validate_media_src(src, note.rel_path, repo_root)
        caption = attrs.get("caption", "").strip()
        title = attrs.get("title", "").strip()
        preload = attrs.get("preload", "none").strip() or "none"
        if preload not in {"none", "metadata", "auto"}:
            raise NoteError(f"{note.rel_path}: shortcode 'audio' has invalid preload '{preload}'")
        wrapper = [
            '<figure class="note-media">',
            f'  <audio controls preload="{preload}" src="{html.escape(src, quote=True)}">'
            "Seu navegador não suporta áudio HTML5.</audio>",
        ]
        if title:
            wrapper.insert(1, f'  <p class="visually-hidden">{html.escape(title)}</p>')
        if caption:
            wrapper.append(f"  <figcaption>{render_inline_markdown(caption)}</figcaption>")
        wrapper.append("</figure>")
        return "\n".join(wrapper)

    if normalized_name == "video":
        src = require_attr(attrs, "src", note.rel_path, normalized_name)
        validate_media_src(src, note.rel_path, repo_root)
        caption = attrs.get("caption", "").strip()
        poster = attrs.get("poster", "").strip()
        if poster:
            validate_media_src(poster, note.rel_path, repo_root)
        width = optional_numeric_attr(attrs, "width", note.rel_path, normalized_name)
        height = optional_numeric_attr(attrs, "height", note.rel_path, normalized_name)
        preload = attrs.get("preload", "metadata").strip() or "metadata"
        if preload not in {"none", "metadata", "auto"}:
            raise NoteError(f"{note.rel_path}: shortcode 'video' has invalid preload '{preload}'")
        size_attrs = ""
        if width:
            size_attrs += f' width="{width}"'
        if height:
            size_attrs += f' height="{height}"'
        poster_attr = f' poster="{html.escape(poster, quote=True)}"' if poster else ""
        video_lines = [
            '<figure class="note-media">',
            f'  <video controls playsinline preload="{preload}" src="{html.escape(src, quote=True)}"{poster_attr}{size_attrs}>'
            "Seu navegador não suporta vídeo HTML5.</video>",
        ]
        if caption:
            video_lines.append(f"  <figcaption>{render_inline_markdown(caption)}</figcaption>")
        video_lines.append("</figure>")
        return "\n".join(video_lines)

    raise NoteError(f"{note.rel_path}: unsupported shortcode '{normalized_name}'")


def parse_shortcode_attrs(attrs_raw: str, rel_path: str) -> dict[str, str]:
    attrs_raw = attrs_raw.strip()
    if not attrs_raw:
        return {}

    try:
        parts = shlex.split(attrs_raw)
    except ValueError as exc:
        raise NoteError(f"{rel_path}: invalid shortcode attributes '{attrs_raw}'") from exc

    attrs: dict[str, str] = {}
    for part in parts:
        if "=" not in part:
            raise NoteError(f"{rel_path}: invalid shortcode attribute '{part}', expected key=value")
        key, value = part.split("=", 1)
        attrs[key.strip().lower()] = value.strip()
    return attrs


def require_attr(attrs: dict[str, str], key: str, rel_path: str, shortcode_name: str) -> str:
    value = attrs.get(key, "").strip()
    if not value:
        raise NoteError(f"{rel_path}: shortcode '{shortcode_name}' requires '{key}'")
    return value


def optional_numeric_attr(attrs: dict[str, str], key: str, rel_path: str, shortcode_name: str) -> str:
    value = attrs.get(key, "").strip()
    if not value:
        return ""
    if not value.isdigit():
        raise NoteError(f"{rel_path}: shortcode '{shortcode_name}' field '{key}' must be numeric")
    return value


def validate_media_src(value: str, rel_path: str, repo_root: pathlib.Path) -> None:
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"}:
        return
    if not value.startswith("/"):
        raise NoteError(f"{rel_path}: media paths must use an absolute site path or full URL ('{value}')")
    target = repo_root / value.lstrip("/")
    if not target.exists():
        raise NoteError(f"{rel_path}: media asset not found at '{value}'")


def render_inline_markdown(text: str) -> str:
    placeholders: dict[str, str] = {}

    def store(raw_html: str) -> str:
        token = f"__NOTE_TOKEN_{len(placeholders)}__"
        placeholders[token] = raw_html
        return token

    escaped = html.escape(text, quote=False)
    escaped = re.sub(r"`([^`]+)`", lambda match: store(f"<code>{match.group(1)}</code>"), escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", lambda match: f"<strong>{match.group(1)}</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", lambda match: f"<em>{match.group(1)}</em>", escaped)
    escaped = re.sub(
        r"\[([^\]]+)\]\(([^)\s]+)\)",
        lambda match: render_link(match.group(1), match.group(2)),
        escaped,
    )

    for token, raw_html in placeholders.items():
        escaped = escaped.replace(token, raw_html)
    return escaped


def render_link(label: str, href: str) -> str:
    parsed = urlparse(href)
    rel_attr = ""
    target_attr = ""
    if parsed.scheme in {"http", "https"}:
        rel_attr = ' rel="noopener noreferrer"'
        target_attr = ' target="_blank"'
    return f'<a href="{html.escape(href, quote=True)}"{rel_attr}{target_attr}>{label}</a>'


def indent_block(block: str, prefix: str) -> str:
    return "\n".join(f"{prefix}{line}" if line else "" for line in block.splitlines())
