#!/usr/bin/env python3
"""Load Markdown note sources and render public notes surfaces."""

from __future__ import annotations

import datetime as dt
import html
import json
import pathlib
import re
import shlex
import unicodedata
from dataclasses import dataclass, field
from urllib.parse import urlparse

NOTE_SOURCE_DIR = pathlib.Path("content/notes")
NOTE_PUBLIC_DIR = pathlib.Path("notes")
NOTE_AUTO_BLOCK = "now-notes"
NOTE_DEFAULT_CATEGORY = "Nota"
NOTE_ARCHIVE_PAGE_SIZE = 20
NOW_NOTES_LIMIT = 12
SITE_NAME = "Bolívar Alencastro"
SITE_NAME_FALLBACK = "Bolivar Alencastro"
AUTHOR_PROFILE_URL = "https://bolivaralencastro.com.br/about.html"
AUTHOR_IMAGE_URL = "https://bolivaralencastro.com.br/assets/images/author/bolivar-alencastro.webp"
AUTHOR_SAME_AS = [
    "https://github.com/bolivaralencastro",
    "https://facebook.com/bolivaralencastrofotografia",
    "https://www.linkedin.com/in/bolivaralencastro/",
    "https://www.instagram.com/bolivar.alencastro/",
]
DEFAULT_OG_IMAGE = "/assets/images/og/site-og.jpg"
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


@dataclass
class RenderedBlock:
    html: str
    plain_text: str
    kind: str
    image_src: str = ""


@dataclass
class RenderedNoteBody:
    body_html: str
    blocks: list[RenderedBlock]

    @property
    def excerpt_html(self) -> str:
        for block in self.blocks:
            if block.kind != "media" and block.plain_text:
                return block.html
        return self.blocks[0].html if self.blocks else ""

    @property
    def description_text(self) -> str:
        for block in self.blocks:
            if block.kind != "media" and block.plain_text:
                return block.plain_text
        for block in self.blocks:
            if block.plain_text:
                return block.plain_text
        return ""

    @property
    def first_image_src(self) -> str:
        for block in self.blocks:
            if block.image_src:
                return block.image_src
        return ""


@dataclass
class Note:
    source: NoteSource
    article_id: str
    slug: str
    title: str
    display_title: str
    category: str
    date: dt.date
    classes: list[str]
    public_rel_path: str
    public_url: str
    canonical_url: str
    page_title: str
    description: str
    excerpt_html: str
    excerpt_text: str
    body_html: str
    og_image: str

    @property
    def rel_path(self) -> str:
        return self.source.rel_path

    @property
    def path(self) -> pathlib.Path:
        return self.source.path

    @property
    def status(self) -> str:
        return self.source.status

    @property
    def body_markdown(self) -> str:
        return self.source.body_markdown

    @property
    def now_anchor_url(self) -> str:
        return f"/now.html#{self.article_id}"


@dataclass
class NotesArchivePage:
    page_number: int
    total_pages: int
    rel_path: str
    href: str
    canonical_url: str
    title: str
    description: str
    notes: list[Note]
    prev_href: str = ""
    next_href: str = ""


def note_source_dir(repo_root: pathlib.Path) -> pathlib.Path:
    return repo_root / NOTE_SOURCE_DIR


def load_notes(
    repo_root: pathlib.Path,
    *,
    base_url: str = "",
    include_drafts: bool = False,
) -> list[Note]:
    notes_dir = note_source_dir(repo_root)
    if not notes_dir.exists():
        return []

    notes: list[Note] = []
    seen_ids: set[str] = set()

    for path in sorted(notes_dir.glob("*.md")):
        if path.name.startswith("_") or path.stem.lower() == "readme":
            continue

        source = parse_note_file(path, repo_root)
        if source.article_id in seen_ids:
            raise NoteError(f"{source.rel_path}: duplicate note permalink '{source.article_id}'")
        seen_ids.add(source.article_id)

        if source.status == "draft" and not include_drafts:
            continue

        notes.append(materialize_note(source, repo_root, base_url=base_url))

    notes.sort(key=lambda item: (item.date, item.rel_path), reverse=True)
    return notes


def generate_now_notes_html(
    repo_root: pathlib.Path,
    *,
    base_url: str = "",
    limit: int = NOW_NOTES_LIMIT,
) -> str:
    return render_now_notes_html(load_notes(repo_root, base_url=base_url), limit=limit)


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


def materialize_note(source: NoteSource, repo_root: pathlib.Path, *, base_url: str = "") -> Note:
    rendered = render_note_body(source, repo_root)
    display_title = source.title.strip() or humanize_slug(source.slug)
    description_source = rendered.description_text or display_title
    description = truncate_text(description_source, 165)
    public_rel_path = f"{NOTE_PUBLIC_DIR.as_posix()}/{source.date.isoformat()}-{source.slug}.html"
    public_url = f"/{public_rel_path}"
    canonical_url = canonical_url_for_rel_path(public_rel_path, base_url) if base_url else ""
    page_title = f"{display_title} - Nota - {SITE_NAME}"
    og_image = rendered.first_image_src or DEFAULT_OG_IMAGE
    excerpt_html = rendered.excerpt_html or f"<p>{html.escape(description)}</p>"

    return Note(
        source=source,
        article_id=source.article_id,
        slug=source.slug,
        title=source.title,
        display_title=display_title,
        category=source.category,
        date=source.date,
        classes=list(source.classes),
        public_rel_path=public_rel_path,
        public_url=public_url,
        canonical_url=canonical_url,
        page_title=page_title,
        description=description,
        excerpt_html=excerpt_html,
        excerpt_text=strip_tags(excerpt_html) or description,
        body_html=rendered.body_html,
        og_image=og_image,
    )


def humanize_slug(slug: str) -> str:
    words = [part for part in slug.split("-") if part]
    if not words:
        return "Nota"
    label = " ".join(words)
    return label[:1].upper() + label[1:]


def truncate_text(text: str, limit: int) -> str:
    normalized = " ".join(text.split()).strip()
    if len(normalized) <= limit:
        return normalized
    shortened = normalized[: limit - 1].rsplit(" ", 1)[0].strip()
    return f"{shortened}…"


def canonical_url_for_rel_path(rel_path: str, base_url: str) -> str:
    base = base_url.rstrip("/")
    if not base:
        return ""
    if rel_path == "index.html":
        return f"{base}/"
    if rel_path.endswith("/index.html"):
        return f"{base}/{rel_path.removesuffix('/index.html')}/"
    return f"{base}/{rel_path}"


def rel_path_to_href(rel_path: str) -> str:
    if rel_path == "index.html":
        return "/"
    if rel_path.endswith("/index.html"):
        return f"/{rel_path.removesuffix('index.html')}"
    return f"/{rel_path}"


def format_note_date(date_value: dt.date) -> str:
    return f"{date_value.day:02d} {NOTE_MONTHS_PT[date_value.month - 1]} {date_value.year}"


def format_note_date_short(date_value: dt.date) -> str:
    return date_value.strftime("%d/%m/%Y")


def render_now_notes_html(notes: list[Note], *, limit: int = NOW_NOTES_LIMIT) -> str:
    published = notes[:limit]
    if not published:
        return '        <p class="note-empty">Nenhuma nota publicada ainda.</p>'

    blocks: list[str] = []
    for note in published:
        classes = ["note", "h-entry", *note.classes]
        block_lines = [f'        <article id="{note.article_id}" class="{" ".join(classes)}">']
        block_lines.append(f'          <p class="visually-hidden p-name">{html.escape(note.display_title)}</p>')
        block_lines.append('          <div class="e-content">')
        block_lines.append(indent_block(note.body_html, "            "))
        block_lines.append("          </div>")
        block_lines.extend(
            [
                '          <footer class="note-meta">',
                f'            <span class="p-category">{html.escape(note.category)}</span>',
                f'            <time class="dt-published" datetime="{note.date.isoformat()}">{format_note_date(note.date)}</time>',
                f'            <a class="u-url" href="{note.public_url}">ler nota</a>',
                "          </footer>",
                "        </article>",
            ]
        )
        blocks.append("\n".join(block_lines))

    return "\n\n".join(blocks)


def build_note_pages(notes: list[Note], *, base_url: str) -> dict[str, str]:
    return {note.public_rel_path: render_note_page(note, base_url=base_url) for note in notes}


def build_notes_archive_pages(notes: list[Note], *, base_url: str) -> dict[str, str]:
    pages = paginate_notes(notes, base_url=base_url)
    return {page.rel_path: render_notes_archive_page(page, base_url=base_url) for page in pages}


def paginate_notes(notes: list[Note], *, base_url: str, per_page: int = NOTE_ARCHIVE_PAGE_SIZE) -> list[NotesArchivePage]:
    total_pages = max(1, (len(notes) + per_page - 1) // per_page)
    pages: list[NotesArchivePage] = []

    for page_number in range(1, total_pages + 1):
        start = (page_number - 1) * per_page
        end = start + per_page
        page_notes = notes[start:end]
        rel_path = notes_archive_rel_path(page_number)
        href = rel_path_to_href(rel_path)
        title = "Arquivo de notas - Bolívar Alencastro"
        description = "Arquivo paginado de notas publicadas por Bolívar Alencastro, com apontamentos curtos, leituras e ideias em curso."
        if page_number > 1:
            title = f"Arquivo de notas - Página {page_number} - Bolívar Alencastro"
            description = (
                f"Página {page_number} do arquivo de notas publicadas por Bolívar Alencastro."
            )

        pages.append(
            NotesArchivePage(
                page_number=page_number,
                total_pages=total_pages,
                rel_path=rel_path,
                href=href,
                canonical_url=canonical_url_for_rel_path(rel_path, base_url),
                title=title,
                description=description,
                notes=page_notes,
                prev_href=rel_path_to_href(notes_archive_rel_path(page_number - 1)) if page_number > 1 else "",
                next_href=rel_path_to_href(notes_archive_rel_path(page_number + 1)) if page_number < total_pages else "",
            )
        )

    return pages


def notes_archive_rel_path(page_number: int) -> str:
    if page_number <= 1:
        return "notes/index.html"
    return f"notes/page/{page_number}.html"


def render_note_page(note: Note, *, base_url: str) -> str:
    og_image = absolute_asset_url(note.og_image, base_url)
    person_schema = {
        "@type": "Person",
        "@id": f"{AUTHOR_PROFILE_URL}#person",
        "name": SITE_NAME,
        "alternateName": SITE_NAME_FALLBACK,
        "url": AUTHOR_PROFILE_URL,
        "image": AUTHOR_IMAGE_URL,
        "sameAs": AUTHOR_SAME_AS,
    }
    jsonld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": note.display_title,
        "description": note.description,
        "datePublished": note.date.isoformat(),
        "dateModified": note.date.isoformat(),
        "articleSection": note.category,
        "url": note.canonical_url,
        "mainEntityOfPage": note.canonical_url,
        "image": og_image,
        "author": person_schema,
        "publisher": person_schema,
        "inLanguage": "pt-BR",
    }

    lines = [
        "<!DOCTYPE html>",
        '<html lang="pt-BR">',
        "<head>",
        '  <meta charset="UTF-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        f"  <title>{html.escape(note.page_title)}</title>",
        f'  <meta name="description" content="{html.escape(note.description, quote=True)}">',
        '  <link rel="stylesheet" href="/style.css">',
        '  <noscript><link rel="stylesheet" href="/assets/css/nojs-nav.css"></noscript>',
        f'  <link rel="canonical" href="{html.escape(note.canonical_url, quote=True)}">',
        f'  <meta name="author" content="{html.escape(SITE_NAME, quote=True)}">',
        '  <link rel="author" href="/about.html">',
        '  <meta name="generator" content="Handcrafted HTML">',
        '  <link rel="webmention" href="https://webmention.io/bolivaralencastro.com.br/webmention">',
        '  <link rel="pingback" href="https://webmention.io/bolivaralencastro.com.br/xmlrpc">',
        '  <link rel="me" href="https://github.com/bolivaralencastro">',
        '  <link rel="me" href="https://facebook.com/bolivaralencastrofotografia">',
        '  <link rel="me" href="https://www.instagram.com/bolivar.alencastro/">',
        '  <link rel="me" href="https://www.linkedin.com/in/bolivaralencastro/">',
        '  <link rel="alternate" type="text/plain" title="Perfil para modelos de linguagem" href="/llms.txt">',
        f'  <meta property="og:title" content="{html.escape(note.display_title, quote=True)}">',
        f'  <meta property="og:description" content="{html.escape(note.description, quote=True)}">',
        f'  <meta property="og:url" content="{html.escape(note.canonical_url, quote=True)}">',
        '  <meta property="og:type" content="article">',
        f'  <meta property="og:image" content="{html.escape(og_image, quote=True)}">',
        '  <meta name="twitter:card" content="summary_large_image">',
        f'  <meta name="twitter:title" content="{html.escape(note.display_title, quote=True)}">',
        f'  <meta name="twitter:description" content="{html.escape(note.description, quote=True)}">',
        f'  <meta name="twitter:image" content="{html.escape(og_image, quote=True)}">',
        '  <meta name="view-transition" content="same-origin">',
        '  <script type="application/ld+json">',
        json.dumps(jsonld, ensure_ascii=False, indent=2),
        "  </script>",
        '  <script src="/assets/js/lightbox.js" defer></script>',
        '  <script src="/assets/js/mobile-nav.js" defer></script>',
        '  <!-- Meta Pixel -->',
        '  <script src="/assets/js/meta-pixel.js" defer></script>',
        '  <noscript><img height="1" width="1" style="display:none" src="https://www.facebook.com/tr?id=1537864418068216&ev=PageView&noscript=1"/></noscript>',
        '  <!-- End Meta Pixel -->',
        "</head>",
        '<body class="note-page">',
        '  <div class="grain"></div>',
        '  <a href="#main" class="skip-link">Pular para o conteúdo</a>',
        "",
        build_site_header(now_current=True),
        "",
        '  <main id="main" class="grid">',
        '    <article class="h-entry col-12">',
        f'      <h1 class="p-name col-9">{html.escape(note.display_title)}</h1>',
        '      <div class="note-meta note-page-meta col-12">',
        f'        <span class="p-category">{html.escape(note.category)}</span>',
        f'        <time class="dt-published" datetime="{note.date.isoformat()}">{format_note_date(note.date)}</time>',
        f'        <a class="u-url" href="{note.public_url}">permalink</a>',
        "      </div>",
        f'      <p class="p-summary col-8">{html.escape(note.description)}</p>',
        '      <nav class="note-context-links col-12" aria-label="Contexto da nota">',
        '        <a href="/now.html">Voltar ao Now</a>',
        '        <a href="/notes/">Arquivo de notas</a>',
        "      </nav>",
        '      <div class="e-content col-8 section-block">',
        indent_block(note.body_html, "        "),
        "      </div>",
        "    </article>",
        "  </main>",
        "",
        indent_block(build_site_footer(), "  "),
        "</body>",
        "</html>",
        "",
    ]
    return "\n".join(lines)


def render_notes_archive_page(page: NotesArchivePage, *, base_url: str) -> str:
    jsonld_items = []
    for index, note in enumerate(page.notes, start=1 + ((page.page_number - 1) * NOTE_ARCHIVE_PAGE_SIZE)):
        jsonld_items.append(
            {
                "@type": "ListItem",
                "position": index,
                "url": note.canonical_url,
                "item": {
                    "@type": "Article",
                    "headline": note.display_title,
                    "datePublished": note.date.isoformat(),
                    "url": note.canonical_url,
                    "description": note.description,
                },
            }
        )

    jsonld = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "Arquivo de notas",
        "url": page.canonical_url,
        "about": {
            "@type": "Person",
            "@id": f"{AUTHOR_PROFILE_URL}#person",
            "name": SITE_NAME,
            "alternateName": SITE_NAME_FALLBACK,
            "url": AUTHOR_PROFILE_URL,
            "image": AUTHOR_IMAGE_URL,
            "sameAs": AUTHOR_SAME_AS,
        },
        "mainEntity": {
            "@type": "ItemList",
            "itemListElement": jsonld_items,
        },
    }

    lines = [
        "<!DOCTYPE html>",
        '<html lang="pt-BR">',
        "<head>",
        '  <meta charset="UTF-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        f"  <title>{html.escape(page.title)}</title>",
        f'  <meta name="description" content="{html.escape(page.description, quote=True)}">',
        '  <link rel="stylesheet" href="/style.css">',
        '  <noscript><link rel="stylesheet" href="/assets/css/nojs-nav.css"></noscript>',
        f'  <link rel="canonical" href="{html.escape(page.canonical_url, quote=True)}">',
        f'  <meta name="author" content="{html.escape(SITE_NAME, quote=True)}">',
        '  <meta name="generator" content="Handcrafted HTML">',
        '  <link rel="webmention" href="https://webmention.io/bolivaralencastro.com.br/webmention">',
        '  <link rel="pingback" href="https://webmention.io/bolivaralencastro.com.br/xmlrpc">',
        '  <link rel="me" href="https://github.com/bolivaralencastro">',
        '  <link rel="me" href="https://facebook.com/bolivaralencastrofotografia">',
        '  <link rel="me" href="https://www.instagram.com/bolivar.alencastro/">',
        '  <link rel="me" href="https://www.linkedin.com/in/bolivaralencastro/">',
        '  <link rel="alternate" type="text/plain" title="Perfil para modelos de linguagem" href="/llms.txt">',
        '  <meta property="og:title" content="Arquivo de notas - Bolívar Alencastro">',
        f'  <meta property="og:description" content="{html.escape(page.description, quote=True)}">',
        f'  <meta property="og:url" content="{html.escape(page.canonical_url, quote=True)}">',
        '  <meta property="og:type" content="website">',
        f'  <meta property="og:image" content="{html.escape(absolute_asset_url(DEFAULT_OG_IMAGE, base_url), quote=True)}">',
        '  <meta name="twitter:card" content="summary_large_image">',
        '  <meta name="twitter:title" content="Arquivo de notas - Bolívar Alencastro">',
        f'  <meta name="twitter:description" content="{html.escape(page.description, quote=True)}">',
        f'  <meta name="twitter:image" content="{html.escape(absolute_asset_url(DEFAULT_OG_IMAGE, base_url), quote=True)}">',
        '  <meta name="view-transition" content="same-origin">',
        '  <script type="application/ld+json">',
        json.dumps(jsonld, ensure_ascii=False, indent=2),
        "  </script>",
        '  <script src="/assets/js/lightbox.js" defer></script>',
        '  <script src="/assets/js/mobile-nav.js" defer></script>',
        '  <!-- Meta Pixel -->',
        '  <script src="/assets/js/meta-pixel.js" defer></script>',
        '  <noscript><img height="1" width="1" style="display:none" src="https://www.facebook.com/tr?id=1537864418068216&ev=PageView&noscript=1"/></noscript>',
        '  <!-- End Meta Pixel -->',
        "</head>",
        '<body class="notes-archive-page">',
        '  <div class="grain"></div>',
        '  <a href="#main" class="skip-link">Pular para o conteúdo principal</a>',
        "",
        build_site_header(now_current=True),
        "",
        '  <main id="main" class="grid">',
        '    <section class="page-hero grid col-12 section-block">',
        '      <h1 class="page-title col-8">Arquivo de notas</h1>',
        '      <p class="lead col-4">Notas publicadas a partir do Now: leituras, ideias em aberto, imagens e pequenos registros com página própria.</p>',
        "    </section>",
        '    <section class="grid col-12 section-block note-archive-list" aria-label="Notas publicadas">',
        '      <p class="archive-kicker col-12">O Now abre a conversa. Aqui ficam reunidas as notas publicadas.</p>',
    ]

    if page.notes:
        for note in page.notes:
            lines.extend(render_archive_note_item(note))
    else:
        lines.append('      <p class="note-empty col-12">Nenhuma nota publicada ainda.</p>')

    lines.append("    </section>")

    pagination_html = render_archive_pagination(page)
    if pagination_html:
        lines.append(indent_block(pagination_html, "    "))

    lines.extend(
        [
            "  </main>",
            "",
            indent_block(build_site_footer(), "  "),
            "</body>",
            "</html>",
            "",
        ]
    )
    return "\n".join(lines)


def render_archive_note_item(note: Note) -> list[str]:
    lines = [
        '      <article class="note-index-item h-entry col-12">',
        '        <div class="note-index-body">',
        f'          <h2 class="p-name"><a class="u-url" href="{note.public_url}">{html.escape(note.display_title)}</a></h2>',
        '          <div class="note-index-excerpt e-content">',
        indent_block(note.body_html, "            "),
        "          </div>",
        '          <footer class="note-meta">',
        f'            <span class="p-category">{html.escape(note.category)}</span>',
        f'            <time class="dt-published" datetime="{note.date.isoformat()}">{format_note_date_short(note.date)}</time>',
        f'            <a href="{note.public_url}">abrir nota</a>',
        "          </footer>",
        "        </div>",
        "      </article>",
    ]
    return lines


def render_archive_pagination(page: NotesArchivePage) -> str:
    if page.total_pages <= 1:
        return ""

    prev_link = (
        f'<a class="button" href="{page.prev_href}" rel="prev">Página anterior</a>'
        if page.prev_href
        else '<span class="button button-disabled" aria-disabled="true">Página anterior</span>'
    )
    next_link = (
        f'<a class="button" href="{page.next_href}" rel="next">Próxima página</a>'
        if page.next_href
        else '<span class="button button-disabled" aria-disabled="true">Próxima página</span>'
    )

    return "\n".join(
        [
            '<nav class="archive-pagination grid col-12 section-block" aria-label="Paginação das notas">',
            f'  <p class="archive-pagination-status col-12">Página {page.page_number} de {page.total_pages}</p>',
            f'  <div class="archive-pagination-links col-12">{prev_link}{next_link}</div>',
            "</nav>",
        ]
    )


def render_note_body(note: NoteSource, repo_root: pathlib.Path) -> RenderedNoteBody:
    lines = note.body_markdown.splitlines()
    blocks: list[RenderedBlock] = []
    paragraph_lines: list[str] = []
    list_mode: str | None = None
    list_items: list[str] = []
    quote_lines: list[str] = []
    raw_lines: list[str] = []

    def push_block(fragment: RenderedBlock) -> None:
        blocks.append(fragment)

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if paragraph_lines:
            text = " ".join(chunk.strip() for chunk in paragraph_lines if chunk.strip())
            push_block(RenderedBlock(f"<p>{render_inline_markdown(text)}</p>", strip_inline_markdown(text), "paragraph"))
            paragraph_lines = []

    def flush_list() -> None:
        nonlocal list_mode, list_items
        if list_mode and list_items:
            items_html = "".join(f"<li>{render_inline_markdown(item)}</li>" for item in list_items)
            items_text = " ".join(strip_inline_markdown(item) for item in list_items)
            push_block(RenderedBlock(f"<{list_mode}>{items_html}</{list_mode}>", items_text, "list"))
        list_mode = None
        list_items = []

    def flush_quote() -> None:
        nonlocal quote_lines
        if quote_lines:
            text = " ".join(chunk.strip() for chunk in quote_lines if chunk.strip())
            push_block(RenderedBlock(f"<blockquote><p>{render_inline_markdown(text)}</p></blockquote>", strip_inline_markdown(text), "quote"))
            quote_lines = []

    def flush_raw() -> None:
        nonlocal raw_lines
        if raw_lines:
            raw_html = "\n".join(raw_lines)
            push_block(RenderedBlock(raw_html, strip_tags(raw_html), "raw"))
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
            push_block(render_shortcode(shortcode_match.group("name"), shortcode_match.group("attrs"), note, repo_root))
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

    return RenderedNoteBody(body_html="\n".join(block.html for block in blocks), blocks=blocks)


def render_shortcode(name: str, attrs_raw: str, note: NoteSource, repo_root: pathlib.Path) -> RenderedBlock:
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
        plain_text = caption or ""
        return RenderedBlock("\n".join(figure_lines), strip_inline_markdown(plain_text), "media", image_src=src)

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
        return RenderedBlock("\n".join(wrapper), strip_inline_markdown(caption), "media")

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
        return RenderedBlock("\n".join(video_lines), strip_inline_markdown(caption), "media", image_src=poster)

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


def strip_inline_markdown(text: str) -> str:
    plain = re.sub(r"`([^`]+)`", r"\1", text)
    plain = re.sub(r"\*\*([^*]+)\*\*", r"\1", plain)
    plain = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", plain)
    plain = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r"\1", plain)
    return " ".join(plain.split()).strip()


def render_link(label: str, href: str) -> str:
    parsed = urlparse(href)
    rel_attr = ""
    target_attr = ""
    if parsed.scheme in {"http", "https"}:
        rel_attr = ' rel="noopener noreferrer"'
        target_attr = ' target="_blank"'
    return f'<a href="{html.escape(href, quote=True)}"{rel_attr}{target_attr}>{label}</a>'


def absolute_asset_url(value: str, base_url: str) -> str:
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"}:
        return value
    if value.startswith("/"):
        return f"{base_url.rstrip('/')}{value}"
    return value


def strip_tags(value: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", value)
    return " ".join(html.unescape(cleaned).split()).strip()


def indent_block(block: str, prefix: str) -> str:
    return "\n".join(f"{prefix}{line}" if line else "" for line in block.splitlines())


def build_site_header(*, now_current: bool = False) -> str:
    now_attr = ' aria-current="page"' if now_current else ""
    return "\n".join(
        [
            '  <header class="grid">',
            '    <div class="brand col-7"><a href="/" class="brand-link"><span class="brand-mark" aria-hidden="true"><span class="dot dot-blue"></span></span><strong>Bolívar Alencastro</strong></a></div>',
            '    <nav class="col-5" aria-label="Navegação principal">',
            '      <button type="button" class="mobile-menu-toggle" aria-controls="mobile-nav-overlay" aria-expanded="false">Menu</button>',
            "      <ul>",
            '        <li><a href="/">Home</a></li>',
            '        <li><a href="/about.html">About</a></li>',
            '        <li><a href="/projects.html">Projects</a></li>',
            '        <li><a href="/blog.html">Blog</a></li>',
            f'        <li><a href="/now.html"{now_attr}>Now</a></li>',
            "      </ul>",
            "    </nav>",
            "  </header>",
        ]
    )


def build_site_footer() -> str:
    return "\n".join(
        [
            '<footer class="grid">',
            '  <p class="col-9">&copy; 2026 Bolívar Alencastro. Design HTML-first.</p>',
            '  <nav class="footer-links col-3" aria-label="Links do rodapé">',
            '    <ul>',
            '      <li><a href="/feed.xml" rel="alternate">RSS Feed</a></li>',
            '      <li><a href="/sitemap.xml">Sitemap</a></li>',
            '      <li><a href="/humans.txt">Humans</a></li>',
            '    </ul>',
            '  </nav>',
            '</footer>',
        ]
    )
