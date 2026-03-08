#!/usr/bin/env python3
"""Convert a Markdown file into a blog post HTML page for this static site."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import math
import pathlib
import re
import subprocess
import sys
import textwrap
import unicodedata
from dataclasses import dataclass

BASE_URL_DEFAULT = "https://bolivaralencastro.com.br"
AUTHOR_DEFAULT = "Bolívar Alencastro"
GENERATOR_DEFAULT = "Generated from Markdown"
WORDS_PER_MINUTE = 200
PT_BR_MONTHS = {
    1: "Jan",
    2: "Fev",
    3: "Mar",
    4: "Abr",
    5: "Mai",
    6: "Jun",
    7: "Jul",
    8: "Ago",
    9: "Set",
    10: "Out",
    11: "Nov",
    12: "Dez",
}


class ConversionError(RuntimeError):
    """Raised when required metadata is missing or invalid."""


@dataclass
class PostMetadata:
    title: str
    description: str
    date: str
    updated: str
    category: str
    reading_time: str
    slug: str
    cover_image: str
    cover_alt: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=pathlib.Path, help="Markdown input file")
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        help="Output HTML file. Defaults to blog/<slug>.html inside the repository.",
    )
    parser.add_argument("--base-url", default=BASE_URL_DEFAULT, help="Canonical site base URL")
    parser.add_argument("--author", default=AUTHOR_DEFAULT, help="Author/publisher name")
    parser.add_argument("--generator", default=GENERATOR_DEFAULT, help="Generator metadata value")
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print HTML to stdout instead of writing a file",
    )
    parser.add_argument(
        "--sync-metadata",
        action="store_true",
        help="Run scripts/build_site_metadata.py after generating the post",
    )
    return parser.parse_args()


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_value = ascii_value.lower()
    ascii_value = re.sub(r"[^a-z0-9]+", "-", ascii_value)
    return ascii_value.strip("-")


def format_pt_date(date_value: dt.date) -> str:
    return f"{date_value.day:02d} {PT_BR_MONTHS[date_value.month]} {date_value.year}"


def parse_iso_date(value: str, field_name: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise ConversionError(f"Campo '{field_name}' precisa estar em YYYY-MM-DD.") from exc


def read_markdown_file(path: pathlib.Path) -> tuple[dict[str, str], str]:
    raw = path.read_text(encoding="utf-8")
    normalized = raw.replace("\r\n", "\n")

    if not normalized.startswith("---\n"):
        return {}, normalized.strip()

    closing_marker = normalized.find("\n---\n", 4)
    if closing_marker == -1:
        raise ConversionError("Front matter iniciado com '---' mas sem fechamento correspondente.")

    front_matter = normalized[4:closing_marker]
    body = normalized[closing_marker + 5 :].strip()
    metadata: dict[str, str] = {}

    for line in front_matter.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            raise ConversionError(f"Linha invalida no front matter: '{line}'")
        key, value = stripped.split(":", 1)
        metadata[key.strip().lower().replace("-", "_")] = value.strip()

    return metadata, body


def strip_markdown(text: str) -> str:
    stripped = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    stripped = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", stripped)
    stripped = re.sub(r"`([^`]+)`", r"\1", stripped)
    stripped = re.sub(r"(\*\*|__)(.*?)\1", r"\2", stripped)
    stripped = re.sub(r"(\*|_)(.*?)\1", r"\2", stripped)
    stripped = re.sub(r"^#+\s*", "", stripped, flags=re.MULTILINE)
    stripped = re.sub(r"\s+", " ", stripped)
    return stripped.strip()


def estimate_reading_time(text: str) -> str:
    word_count = len(re.findall(r"\b\w+\b", strip_markdown(text), flags=re.UNICODE))
    minutes = max(1, math.ceil(word_count / WORDS_PER_MINUTE))
    return f"{minutes} min de leitura"


def truncate_description(text: str, max_length: int = 160) -> str:
    clean = strip_markdown(text)
    if len(clean) <= max_length:
        return clean
    shortened = clean[: max_length - 3].rsplit(" ", 1)[0].strip()
    return f"{shortened}..."


def first_paragraph(markdown: str) -> str:
    blocks = re.split(r"\n\s*\n", markdown)
    for block in blocks:
        candidate = strip_markdown(block.strip())
        if candidate:
            return candidate
    return ""


def ensure_cover_image(value: str) -> str:
    if not value:
        raise ConversionError("Informe 'cover_image' no front matter para gerar og:image e capa do blog.")
    return value


def resolve_post_metadata(front_matter: dict[str, str], markdown_body: str) -> PostMetadata:
    body_title = ""
    lines = markdown_body.splitlines()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            body_title = stripped[2:].strip()
            break

    title = front_matter.get("title") or body_title
    if not title:
        raise ConversionError("Informe 'title' no front matter ou use um heading '# Titulo' no Markdown.")

    slug = front_matter.get("slug") or slugify(title)
    if not slug:
        raise ConversionError("Nao foi possivel gerar um slug valido a partir do titulo.")

    date_value = front_matter.get("date") or dt.date.today().isoformat()
    updated_value = front_matter.get("updated") or date_value
    parse_iso_date(date_value, "date")
    parse_iso_date(updated_value, "updated")

    summary_source = front_matter.get("description") or first_paragraph(markdown_body)
    description = truncate_description(summary_source)
    if not description:
        raise ConversionError("Nao foi possivel derivar a descricao. Adicione 'description' ou um primeiro paragrafo.")

    cover_image = ensure_cover_image(front_matter.get("cover_image", ""))
    cover_alt = front_matter.get("cover_alt") or f"Capa do post: {title}"
    category = front_matter.get("category") or "Artigo"
    reading_time = front_matter.get("reading_time") or estimate_reading_time(markdown_body)

    return PostMetadata(
        title=title,
        description=description,
        date=date_value,
        updated=updated_value,
        category=category,
        reading_time=reading_time,
        slug=slug,
        cover_image=cover_image,
        cover_alt=cover_alt,
    )


def escape_attr(value: str) -> str:
    return html.escape(value, quote=True)


def convert_inline_markdown(text: str) -> str:
    placeholders: dict[str, str] = {}

    def store_placeholder(prefix: str, rendered: str) -> str:
        token = f"@@{prefix}{len(placeholders)}@@"
        placeholders[token] = rendered
        return token

    def code_repl(match: re.Match[str]) -> str:
        return store_placeholder("CODE", f"<code>{html.escape(match.group(1))}</code>")

    def image_repl(match: re.Match[str]) -> str:
        alt = escape_attr(match.group(1))
        src = escape_attr(match.group(2).strip())
        return store_placeholder("IMG", f"<img src=\"{src}\" alt=\"{alt}\">")

    def link_repl(match: re.Match[str]) -> str:
        label = html.escape(match.group(1))
        href = escape_attr(match.group(2).strip())
        attrs = " rel=\"noopener noreferrer\" target=\"_blank\"" if href.startswith(("http://", "https://")) else ""
        return store_placeholder("LINK", f"<a href=\"{href}\"{attrs}>{label}</a>")

    processed = text
    processed = re.sub(r"`([^`]+)`", code_repl, processed)
    processed = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", image_repl, processed)
    processed = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link_repl, processed)
    escaped = html.escape(processed)
    escaped = re.sub(r"(\*\*|__)(.+?)\1", r"<strong>\2</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<em>\1</em>", escaped)
    escaped = re.sub(r"(?<!_)_(?!\s)(.+?)(?<!\s)_(?!_)", r"<em>\1</em>", escaped)

    for token, replacement in placeholders.items():
        escaped = escaped.replace(token, replacement)

    return escaped


def render_markdown(markdown: str, page_title: str) -> str:
    lines = markdown.splitlines()
    rendered: list[str] = []
    index = 0
    skipped_title = False

    while index < len(lines):
        raw_line = lines[index]
        stripped = raw_line.strip()

        if not stripped:
            index += 1
            continue

        fence_match = re.match(r"^```([\w+-]*)\s*$", stripped)
        if fence_match:
            language = fence_match.group(1)
            index += 1
            code_lines: list[str] = []
            while index < len(lines) and not re.match(r"^```", lines[index].strip()):
                code_lines.append(lines[index])
                index += 1
            if index == len(lines):
                raise ConversionError("Bloco de codigo sem fechamento ```.")
            language_attr = f" class=\"language-{escape_attr(language)}\"" if language else ""
            code_html = html.escape("\n".join(code_lines))
            rendered.append(f"        <pre><code{language_attr}>{code_html}</code></pre>")
            index += 1
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading_match:
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()
            if level == 1 and not skipped_title and strip_markdown(heading_text) == strip_markdown(page_title):
                skipped_title = True
                index += 1
                continue
            if level == 1:
                level = 2
            rendered.append(f"        <h{level}>{convert_inline_markdown(heading_text)}</h{level}>")
            index += 1
            continue

        if re.match(r"^>\s?", stripped):
            quote_lines: list[str] = []
            while index < len(lines) and re.match(r"^>\s?", lines[index].strip()):
                quote_lines.append(re.sub(r"^>\s?", "", lines[index].strip()))
                index += 1
            quote_text = " ".join(line for line in quote_lines if line).strip()
            rendered.append(f"        <blockquote><p>{convert_inline_markdown(quote_text)}</p></blockquote>")
            continue

        if re.match(r"^[-*+]\s+", stripped):
            items: list[str] = []
            while index < len(lines) and re.match(r"^[-*+]\s+", lines[index].strip()):
                item_text = re.sub(r"^[-*+]\s+", "", lines[index].strip())
                items.append(f"          <li>{convert_inline_markdown(item_text)}</li>")
                index += 1
            rendered.append("        <ul>")
            rendered.extend(items)
            rendered.append("        </ul>")
            continue

        if re.match(r"^\d+\.\s+", stripped):
            items = []
            while index < len(lines) and re.match(r"^\d+\.\s+", lines[index].strip()):
                item_text = re.sub(r"^\d+\.\s+", "", lines[index].strip())
                items.append(f"          <li>{convert_inline_markdown(item_text)}</li>")
                index += 1
            rendered.append("        <ol>")
            rendered.extend(items)
            rendered.append("        </ol>")
            continue

        image_only_match = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", stripped)
        if image_only_match:
            alt = escape_attr(image_only_match.group(1))
            src = escape_attr(image_only_match.group(2).strip())
            rendered.append(f"        <img src=\"{src}\" alt=\"{alt}\">")
            index += 1
            continue

        paragraph_lines = [stripped]
        index += 1
        while index < len(lines):
            next_stripped = lines[index].strip()
            if not next_stripped:
                break
            if re.match(r"^(#{1,6})\s+", next_stripped):
                break
            if re.match(r"^```", next_stripped):
                break
            if re.match(r"^>\s?", next_stripped):
                break
            if re.match(r"^[-*+]\s+", next_stripped):
                break
            if re.match(r"^\d+\.\s+", next_stripped):
                break
            if re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", next_stripped):
                break
            paragraph_lines.append(next_stripped)
            index += 1

        paragraph_text = " ".join(paragraph_lines).strip()
        rendered.append(f"        <p>{convert_inline_markdown(paragraph_text)}</p>")

    return "\n".join(rendered)


def ensure_absolute_url(path_or_url: str, base_url: str) -> str:
    if path_or_url.startswith(("http://", "https://")):
        return path_or_url
    normalized = path_or_url if path_or_url.startswith("/") else f"/{path_or_url}"
    return f"{base_url.rstrip('/')}{normalized}"


def build_post_html(
    metadata: PostMetadata,
    content_html: str,
    base_url: str,
    author: str,
    generator: str,
) -> str:
    canonical = f"{base_url.rstrip('/')}/blog/{metadata.slug}.html"
    cover_absolute = ensure_absolute_url(metadata.cover_image, base_url)
    published_date = parse_iso_date(metadata.date, "date")

    json_ld = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": metadata.title,
        "description": metadata.description,
        "mainEntityOfPage": canonical,
        "url": canonical,
        "image": cover_absolute,
        "datePublished": metadata.date,
        "dateModified": metadata.updated,
        "author": {"@type": "Person", "name": author},
        "publisher": {"@type": "Person", "name": author},
    }
    json_ld_html = json.dumps(json_ld, ensure_ascii=False, indent=2)

    return textwrap.dedent(
        f"""\
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <title>{escape_attr(metadata.title)} - Blog</title>
          <meta name="description" content="{escape_attr(metadata.description)}">
          <link rel="stylesheet" href="/style.css">
          <link rel="canonical" href="{escape_attr(canonical)}">
          <meta name="author" content="{escape_attr(author)}">
          <meta name="generator" content="{escape_attr(generator)}">
          <link rel="webmention" href="https://webmention.io/bolivaralencastro.com.br/webmention">
          <link rel="pingback" href="https://webmention.io/bolivaralencastro.com.br/xmlrpc">
          <link rel="me" href="https://www.instagram.com/bolivar.alencastro/">
          <link rel="me" href="https://www.linkedin.com/in/bolivaralencastro/">

          <meta property="og:title" content="{escape_attr(metadata.title)}">
          <meta property="og:description" content="{escape_attr(metadata.description)}">
          <meta property="og:url" content="{escape_attr(canonical)}">
          <meta property="og:type" content="article">
          <meta property="og:image" content="{escape_attr(cover_absolute)}">
          <meta name="twitter:card" content="summary_large_image">
          <meta name="twitter:title" content="{escape_attr(metadata.title)}">
          <meta name="twitter:description" content="{escape_attr(metadata.description)}">
          <meta name="twitter:image" content="{escape_attr(cover_absolute)}">

          <script type="application/ld+json">
        {json_ld_html}
          </script>
          <script src="/assets/js/image-fallback.js" defer></script>
        </head>
        <body>
          <div class="grain"></div>
          <a href="#main" class="skip-link">Pular para o conteúdo</a>

          <header class="grid">
            <div class="brand col-7"><a href="/" class="brand-link" aria-label="Ir para a página inicial"><span class="brand-mark" aria-hidden="true"><span class="dot dot-blue"></span></span><strong>Bolívar Alencastro</strong></a></div>
            <nav class="col-5" aria-label="Navegação principal">
              <ul>
                <li><a href="/">Home</a></li>
                <li><a href="/about.html">About</a></li>
                <li><a href="/projects.html">Projects</a></li>
                <li><a href="/blog.html" aria-current="page">Blog</a></li>
                <li><a href="/now.html">Now</a></li>
              </ul>
            </nav>
          </header>

          <main id="main" class="grid">
            <article class="h-entry col-12">
              <h1 class="p-name col-9">{html.escape(metadata.title)}</h1>
              <div class="post-meta col-12">
                <time class="dt-published" datetime="{metadata.date}">{format_pt_date(published_date)}</time>
                <span class="meta-separator" aria-hidden="true">•</span>
                <span class="p-category">{html.escape(metadata.category)}</span>
                <span class="meta-separator" aria-hidden="true">•</span>
                <span class="reading-time">{html.escape(metadata.reading_time)}</span>
                <span class="meta-separator" aria-hidden="true">•</span>
                <a class="u-url" href="/blog/{metadata.slug}.html">permalink</a>
              </div>
              <p class="p-summary col-8">{html.escape(metadata.description)}</p>

              <div class="e-content col-8 section-block">
                <img src="{escape_attr(metadata.cover_image)}" alt="{escape_attr(metadata.cover_alt)}">
        {content_html}
              </div>
            </article>
          </main>

          <footer class="grid">
            <p class="col-9">&copy; {dt.date.today().year} Bolívar Alencastro. Design HTML-first.</p>
            <nav class="footer-links col-3" aria-label="Links do rodapé">
              <ul>
                <li><a href="/feed.xml" rel="alternate">RSS Feed</a></li>
                <li><a href="/sitemap.xml">Sitemap</a></li>
                <li><a href="/humans.txt">Humans</a></li>
              </ul>
            </nav>
          </footer>
        </body>
        </html>
        """
    ).rstrip() + "\n"


def maybe_sync_metadata(repo_root: pathlib.Path) -> None:
    result = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "build_site_metadata.py")],
        cwd=repo_root,
        check=False,
    )
    if result.returncode != 0:
        raise ConversionError("O post foi gerado, mas scripts/build_site_metadata.py falhou.")


def main() -> int:
    args = parse_args()
    input_path = args.input.resolve()
    if not input_path.exists():
        raise ConversionError(f"Arquivo Markdown nao encontrado: {input_path}")

    repo_root = pathlib.Path(__file__).resolve().parents[1]
    front_matter, markdown_body = read_markdown_file(input_path)
    metadata = resolve_post_metadata(front_matter, markdown_body)
    content_html = render_markdown(markdown_body, metadata.title)
    output_path = args.output or (repo_root / "blog" / f"{metadata.slug}.html")

    html_output = build_post_html(
        metadata=metadata,
        content_html=content_html,
        base_url=args.base_url,
        author=args.author,
        generator=args.generator,
    )

    if args.stdout:
        sys.stdout.write(html_output)
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html_output, encoding="utf-8")
        print(f"Post gerado em: {output_path}")

    if args.sync_metadata and not args.stdout:
        maybe_sync_metadata(repo_root)
        print("Metadados do site atualizados.")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ConversionError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        raise SystemExit(1)
