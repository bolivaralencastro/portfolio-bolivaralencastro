#!/usr/bin/env python3
"""Generate sitemap, Atom feed, and auto-managed index blocks for the static site."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
from html.parser import HTMLParser
import json
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import List
from urllib.parse import urlparse

from notes_pipeline import (
    NOTE_AUTO_BLOCK,
    build_note_pages,
    build_notes_archive_pages,
    generate_now_notes_html,
    load_notes,
)

BASE_URL_DEFAULT = "https://bolivaralencastro.com.br"
ROOT_PAGES = ["index.html", "about.html", "blog.html", "projects.html", "now.html", "links.html", "retratos-ufsc-florianopolis-imersivo.html"]
FEED_AUTHOR_NAME = "Bolívar Alencastro"
FEED_AUTHOR_FALLBACK = "Bolivar Alencastro"
BLOG_ARCHIVE_PAGE_SIZE = 20
LISTING_CARD_FILENAMES = ("card.png", "card.webp", "cover.png", "cover.webp")
LISTING_CARD_WIDTH = 960
LISTING_CARD_HEIGHT = 540
VERSIONED_ASSETS = {
    "/style.css": pathlib.Path("style.css"),
    "/assets/js/clarity.js": pathlib.Path("assets/js/clarity.js"),
    "/assets/js/lightbox.js": pathlib.Path("assets/js/lightbox.js"),
    "/assets/js/mobile-nav.js": pathlib.Path("assets/js/mobile-nav.js"),
}


class BuildError(RuntimeError):
    """Raised when generation cannot continue due to missing required metadata."""


@dataclass
class PageMeta:
    path: pathlib.Path
    rel_path: str
    title_tag: str = ""
    h1_texts: List[str] = None
    h1_p_name_text: str = ""
    description: str = ""
    og_image: str = ""
    canonical: str = ""
    lang: str = ""
    summary: str = ""
    published_datetime: str = ""
    e_content_first_paragraph: str = ""
    jsonld_blocks: List[str] = None
    links: List[str] = None
    image_alts: List[str] = None

    def __post_init__(self) -> None:
        if self.h1_texts is None:
            self.h1_texts = []
        if self.jsonld_blocks is None:
            self.jsonld_blocks = []
        if self.links is None:
            self.links = []
        if self.image_alts is None:
            self.image_alts = []


@dataclass
class ArchivePage:
    page_number: int
    total_pages: int
    rel_path: str
    href: str
    canonical_url: str
    title: str
    description: str
    items: list[dict]
    prev_href: str = ""
    next_href: str = ""


class MetaParser(HTMLParser):
    def __init__(self, page: PageMeta) -> None:
        super().__init__(convert_charrefs=True)
        self.page = page
        self._in_title = False
        self._in_h1 = False
        self._h1_has_p_name = False
        self._current_h1_chunks: List[str] = []
        self._in_summary = False
        self._summary_chunks: List[str] = []
        self._in_time_dt_published = False
        self._in_e_content = False
        self._e_content_depth = 0
        self._in_p = False
        self._current_p_chunks: List[str] = []
        self._captured_first_e_content_p = False
        self._in_jsonld_script = False
        self._jsonld_chunks: List[str] = []

    @staticmethod
    def _class_list(attrs: dict) -> set[str]:
        classes = attrs.get("class", "")
        return {c.strip() for c in classes.split() if c.strip()}

    def handle_starttag(self, tag: str, attrs_list) -> None:
        attrs = dict(attrs_list)
        classes = self._class_list(attrs)

        if tag == "html":
            self.page.lang = (attrs.get("lang") or "").strip()

        if tag == "title":
            self._in_title = True

        if tag == "meta" and (attrs.get("name") or "").lower() == "description":
            self.page.description = (attrs.get("content") or "").strip()
        if tag == "meta" and (attrs.get("property") or "").lower() == "og:image":
            self.page.og_image = (attrs.get("content") or "").strip()

        if tag == "link" and (attrs.get("rel") or "").lower() == "canonical":
            self.page.canonical = (attrs.get("href") or "").strip()

        if tag == "h1":
            self._in_h1 = True
            self._h1_has_p_name = "p-name" in classes
            self._current_h1_chunks = []

        if tag == "p" and "p-summary" in classes:
            self._in_summary = True
            self._summary_chunks = []

        if tag == "time" and "dt-published" in classes:
            self.page.published_datetime = (attrs.get("datetime") or "").strip()
            self._in_time_dt_published = True

        if tag == "div" and "e-content" in classes:
            self._in_e_content = True
            self._e_content_depth = 1
        elif self._in_e_content and tag not in {"br", "img", "meta", "link", "hr", "input"}:
            self._e_content_depth += 1

        if self._in_e_content and tag == "p" and not self._captured_first_e_content_p:
            self._in_p = True
            self._current_p_chunks = []

        if tag == "script" and (attrs.get("type") or "").lower() == "application/ld+json":
            self._in_jsonld_script = True
            self._jsonld_chunks = []

        if tag == "a":
            href = (attrs.get("href") or "").strip()
            if href:
                self.page.links.append(href)

        if tag == "img":
            self.page.image_alts.append((attrs.get("alt") or "").strip())

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False

        if tag == "h1":
            self._in_h1 = False
            h1_text = " ".join("".join(self._current_h1_chunks).split()).strip()
            if h1_text:
                self.page.h1_texts.append(h1_text)
                if self._h1_has_p_name and not self.page.h1_p_name_text:
                    self.page.h1_p_name_text = h1_text

        if tag == "p" and self._in_summary:
            self._in_summary = False
            summary = " ".join("".join(self._summary_chunks).split()).strip()
            if summary:
                self.page.summary = summary

        if tag == "time" and self._in_time_dt_published:
            self._in_time_dt_published = False

        if self._in_e_content and tag not in {"br", "img", "meta", "link", "hr", "input"}:
            self._e_content_depth -= 1
            if self._e_content_depth <= 0:
                self._in_e_content = False
                self._e_content_depth = 0

        if tag == "p" and self._in_p:
            self._in_p = False
            paragraph = " ".join("".join(self._current_p_chunks).split()).strip()
            if paragraph and not self._captured_first_e_content_p:
                self.page.e_content_first_paragraph = paragraph
                self._captured_first_e_content_p = True

        if tag == "script" and self._in_jsonld_script:
            self._in_jsonld_script = False
            block = "".join(self._jsonld_chunks).strip()
            if block:
                self.page.jsonld_blocks.append(block)

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.page.title_tag += data
        if self._in_h1:
            self._current_h1_chunks.append(data)
        if self._in_summary:
            self._summary_chunks.append(data)
        if self._in_p:
            self._current_p_chunks.append(data)
        if self._in_jsonld_script:
            self._jsonld_chunks.append(data)


def parse_page(path: pathlib.Path, repo_root: pathlib.Path) -> PageMeta:
    rel_path = path.relative_to(repo_root).as_posix()
    page = PageMeta(path=path, rel_path=rel_path)
    parser = MetaParser(page)
    parser.feed(path.read_text(encoding="utf-8"))
    page.title_tag = " ".join(page.title_tag.split()).strip()
    return page


def parse_iso_datetime(value: str, context: str) -> dt.datetime:
    raw = (value or "").strip()
    if not raw:
        raise BuildError(f"{context}: missing datetime value")

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return dt.datetime.combine(dt.date.fromisoformat(raw), dt.time.min, tzinfo=dt.timezone.utc)

    try:
        parsed = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BuildError(f"{context}: invalid ISO datetime '{raw}'") from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    else:
        parsed = parsed.astimezone(dt.timezone.utc)
    return parsed


def get_lastmod_date(path: pathlib.Path, repo_root: pathlib.Path) -> str:
    rel = path.relative_to(repo_root)
    git_cmd = ["git", "log", "-1", "--format=%cs", "--", str(rel)]
    try:
        result = subprocess.run(
            git_cmd,
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        result = None

    if result and result.returncode == 0:
        output = result.stdout.strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", output):
            return output

    mtime = dt.datetime.fromtimestamp(path.stat().st_mtime, tz=dt.timezone.utc)
    return mtime.date().isoformat()


def rel_to_url(rel_path: str, base_url: str) -> str:
    if rel_path == "index.html":
        return f"{base_url}/"
    if rel_path.endswith("/index.html"):
        return f"{base_url}/{rel_path.removesuffix('/index.html')}/"
    return f"{base_url}/{rel_path}"


def rel_path_to_href(rel_path: str) -> str:
    if rel_path == "index.html":
        return "/"
    if rel_path.endswith("/index.html"):
        return f"/{rel_path.removesuffix('index.html')}"
    return f"/{rel_path}"


def replace_auto_block(content: str, block_name: str, inner_html: str) -> str:
    start_token = f"<!-- AUTO:{block_name}:start -->"
    end_token = f"<!-- AUTO:{block_name}:end -->"

    start_idx = content.find(start_token)
    end_idx = content.find(end_token, start_idx + len(start_token))
    if start_idx == -1 or end_idx == -1:
        raise BuildError(
            f"Missing markers for block '{block_name}'. Add <!-- AUTO:{block_name}:start --> and <!-- AUTO:{block_name}:end -->"
        )

    line_start = content.rfind("\n", 0, start_idx) + 1
    indent = content[line_start:start_idx]
    block_after_end = end_idx + len(end_token)

    replacement = f"{start_token}\n{inner_html.rstrip()}\n{indent}{end_token}"
    return content[:start_idx] + replacement + content[block_after_end:]


def ensure_auto_block_before_token(content: str, block_name: str, anchor_token: str) -> str:
    start_token = f"<!-- AUTO:{block_name}:start -->"
    end_token = f"<!-- AUTO:{block_name}:end -->"
    if start_token in content and end_token in content:
        return content

    anchor_idx = content.find(anchor_token)
    if anchor_idx == -1:
        raise BuildError(f"Missing anchor token '{anchor_token}' for block '{block_name}'")

    line_start = content.rfind("\n", 0, anchor_idx) + 1
    indent = content[line_start:anchor_idx]
    auto_block = (
        f"{indent}{start_token}\n"
        f"{indent}{end_token}\n"
    )
    return content[:anchor_idx] + auto_block + content[anchor_idx:]


def relocate_auto_block_before_token(content: str, block_name: str, anchor_token: str) -> str:
    start_token = f"<!-- AUTO:{block_name}:start -->"
    end_token = f"<!-- AUTO:{block_name}:end -->"
    block_pattern = re.compile(
        rf"\s*{re.escape(start_token)}.*?{re.escape(end_token)}\s*",
        re.DOTALL,
    )
    stripped = block_pattern.sub("", content)
    stripped = re.sub(
        r"\s*<article class=\"e-content col-12 section-block\">\s*</article>\s*",
        "\n",
        stripped,
    )
    stripped = re.sub(
        r"(<!-- AUTO:project-author-card:end -->\s*</article>)(?:\s*\1)+",
        r"\1",
        stripped,
    )
    return ensure_auto_block_before_token(stripped, block_name, anchor_token)


def indent_html_block(block: str, prefix: str) -> str:
    return "\n".join(f"{prefix}{line}" if line else "" for line in block.splitlines())


def build_standard_footer_html() -> str:
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


def ensure_standard_footer(content: str) -> str:
    footer_html = build_standard_footer_html()
    footer_pattern = re.compile(r"\n?<footer class=\"grid\">.*?</footer>\s*", re.DOTALL)
    if footer_pattern.search(content):
        return footer_pattern.sub(f"\n{footer_html}\n", content, count=1)

    body_close = "</body>"
    body_idx = content.find(body_close)
    if body_idx == -1:
        raise BuildError("Missing </body> while applying standard footer")
    return content[:body_idx] + f"{footer_html}\n" + content[body_idx:]


def rewrite_project_detail_blocks(content: str, author_html: str, related_html: str) -> str:
    content = ensure_auto_block_before_token(content, "project-author-card", "</article>")
    content = relocate_auto_block_before_token(content, "project-related-projects", "</main>")

    combined_pattern = re.compile(
        r"\s*<!-- AUTO:project-author-card:start -->.*?<!-- AUTO:project-related-projects:end -->",
        re.DOTALL,
    )
    replacement = "\n".join(
        [
            "        <!-- AUTO:project-author-card:start -->",
            author_html,
            "        <!-- AUTO:project-author-card:end -->",
            "    </article>",
            "    <!-- AUTO:project-related-projects:start -->",
            related_html,
            "    <!-- AUTO:project-related-projects:end -->",
        ]
    )
    if combined_pattern.search(content):
        return combined_pattern.sub(replacement, content, count=1)
    raise BuildError("Could not rewrite project detail blocks")


def format_pt_date_short(date_value: dt.datetime) -> str:
    return date_value.strftime("%d/%m/%Y")


def build_blog_list_html(posts: list[dict]) -> str:
    lines: List[str] = []
    for post in posts:
        title = html.escape(post["title"])
        summary = html.escape(post["summary"])
        href = html.escape(post["href"])
        cover = html.escape(post["listing_cover_html"])
        date_iso = post["published"].date().isoformat()
        date_human = format_pt_date_short(post["published"])
        size_attrs = ""
        if post["listing_cover_width"] and post["listing_cover_height"]:
            size_attrs = f' width="{post["listing_cover_width"]}" height="{post["listing_cover_height"]}"'
        lines.extend(
            [
                "      <article class=\"post-item post-row h-entry col-12\">",
                f"        <a href=\"{href}\" class=\"post-row-cover\" aria-label=\"Abrir post: {title}\">",
                f"          <img src=\"{cover}\" alt=\"Capa do post: {title}\" loading=\"lazy\" decoding=\"async\"{size_attrs}>",
                "        </a>",
                "        <div class=\"post-row-body\">",
                f"          <h3 class=\"p-name\"><a href=\"{href}\" class=\"u-url\">{title}</a></h3>",
                f"          <p class=\"p-summary\">{summary}</p>",
                "        </div>",
                f"        <time class=\"dt-published post-row-date\" datetime=\"{date_iso}\">{date_human}</time>",
                "      </article>",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def build_projects_list_html(projects: list[dict]) -> str:
    lines: List[str] = []
    for project in projects:
        title = html.escape(project["title"])
        description = html.escape(project["description"])
        href = html.escape(project["href"])
        cover = html.escape(project["listing_cover_html"])
        size_attrs = ""
        if project["listing_cover_width"] and project["listing_cover_height"]:
            size_attrs = f' width="{project["listing_cover_width"]}" height="{project["listing_cover_height"]}"'
        lines.extend(
            [
                "      <article class=\"project-item col-4\">",
                f"        <a href=\"{href}\" class=\"project-cover\" aria-label=\"Abrir projeto: {title}\">",
                f"          <img src=\"{cover}\" alt=\"Capa do projeto: {title}\" loading=\"lazy\" decoding=\"async\"{size_attrs}>",
                "        </a>",
                f"        <h3><a href=\"{href}\">{title}</a></h3>",
                f"        <p>{description}</p>",
                "      </article>",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def build_latest_post_html(latest_post: dict) -> str:
    title = html.escape(latest_post["title"])
    summary = html.escape(latest_post["summary"])
    href = html.escape(latest_post["href"])
    cover = html.escape(latest_post["listing_cover_html"])
    date_iso = latest_post["published"].date().isoformat()
    date_human = format_pt_date_short(latest_post["published"])
    size_attrs = ""
    if latest_post["listing_cover_width"] and latest_post["listing_cover_height"]:
        size_attrs = (
            f' width="{latest_post["listing_cover_width"]}"'
            f' height="{latest_post["listing_cover_height"]}"'
        )

    return "\n".join(
        [
            "      <article class=\"post-item post-row h-entry col-12\">",
            f"        <a href=\"{href}\" class=\"post-row-cover\" aria-label=\"Abrir post: {title}\">",
            f"          <img src=\"{cover}\" alt=\"Capa do post: {title}\" loading=\"lazy\" decoding=\"async\"{size_attrs}>",
            "        </a>",
            "        <div class=\"post-row-body\">",
            f"          <h3 class=\"p-name\"><a href=\"{href}\" class=\"u-url\">{title}</a></h3>",
            f"          <p class=\"p-summary\">{summary}</p>",
            "        </div>",
            f"        <time class=\"dt-published post-row-date\" datetime=\"{date_iso}\">{date_human}</time>",
            "      </article>",
        ]
    )


def build_featured_projects_html(projects: list[dict], limit: int = 3) -> str:
    return build_projects_list_html(projects[:limit])


def build_links_latest_post_html(latest_post: dict) -> str:
    title = html.escape(latest_post["title"])
    summary = html.escape(latest_post["summary"])
    href = html.escape(latest_post["href"])
    cover = html.escape(latest_post["listing_cover_html"])
    date_iso = latest_post["published"].date().isoformat()
    date_human = format_pt_date_short(latest_post["published"])
    size_attrs = ""
    if latest_post["listing_cover_width"] and latest_post["listing_cover_height"]:
        size_attrs = (
            f' width="{latest_post["listing_cover_width"]}"'
            f' height="{latest_post["listing_cover_height"]}"'
        )

    return "\n".join(
        [
            '      <article class="links-feature-card links-feature-post col-12 h-entry">',
            f'        <a href="{href}" class="links-feature-cover" aria-label="Abrir post: {title}">',
            f'          <img src="{cover}" alt="Capa do post: {title}" loading="lazy" decoding="async"{size_attrs}>',
            "        </a>",
            '        <div class="links-feature-body">',
            '          <p class="meta">Post mais recente</p>',
            f'          <h3 class="p-name"><a href="{href}" class="u-url">{title}</a></h3>',
            f'          <p class="p-summary">{summary}</p>',
            f'          <time class="dt-published" datetime="{date_iso}">{date_human}</time>',
            '        </div>',
            "      </article>",
        ]
    )


def build_links_featured_project_html(project: dict) -> str:
    title = html.escape(project["title"])
    description = html.escape(project["description"])
    href = html.escape(project["href"])
    cover = html.escape(project["listing_cover_html"])
    size_attrs = ""
    if project["listing_cover_width"] and project["listing_cover_height"]:
        size_attrs = f' width="{project["listing_cover_width"]}" height="{project["listing_cover_height"]}"'

    return "\n".join(
        [
            '      <article class="links-feature-card links-feature-project col-12">',
            f'        <a href="{href}" class="links-feature-cover" aria-label="Abrir projeto: {title}">',
            f'          <img src="{cover}" alt="Capa do projeto: {title}" loading="lazy" decoding="async"{size_attrs}>',
            "        </a>",
            '        <div class="links-feature-body">',
            '          <p class="meta">Projeto em destaque</p>',
            f'          <h3><a href="{href}">{title}</a></h3>',
            f'          <p>{description}</p>',
            '        </div>',
            "      </article>",
        ]
    )


def build_links_primary_actions_html(latest_post: dict, project: dict) -> str:
    post_title = html.escape(latest_post["title"])
    post_href = html.escape(latest_post["href"])
    project_title = html.escape(project["title"])
    project_href = html.escape(project["href"])
    post_label = f"Último texto: {post_title}"
    project_label = f"Projeto em destaque: {project_title}"

    return "\n".join(
        [
            f'      <a class="ltree-btn ltree-btn--featured" href="{post_href}" title="{post_label}">{post_label}</a>',
            f'      <a class="ltree-btn ltree-btn--featured" href="{project_href}" title="{project_label}">{project_label}</a>',
        ]
    )


def build_author_card_html() -> str:
    return "\n".join(
        [
            '<section class="author-card h-card" aria-label="Sobre o autor">',
            '  <p class="author-card-title">Sobre o autor</p>',
            '  <div class="author-card-inner">',
            '    <img class="author-card-photo u-photo" src="/assets/images/author/bolivar-alencastro.webp" alt="Foto de Bolívar Alencastro" width="641" height="640" loading="lazy" decoding="async">',
            '    <div class="author-card-body">',
            '      <h3 class="author-card-name p-name"><a class="u-url" href="/about.html">Bolívar Alencastro</a></h3>',
            '      <p class="author-card-copy p-note">Product Designer em São Paulo. Estruturo narrativas, interfaces e sistemas para transformar complexidade em decisões claras.</p>',
            '      <ul class="author-card-links" aria-label="Redes sociais do autor">',
            '        <li><a rel="me noopener noreferrer" target="_blank" href="https://www.linkedin.com/in/bolivaralencastro/">LinkedIn</a></li>',
            '        <li><a rel="me noopener noreferrer" target="_blank" href="https://www.instagram.com/bolivar.alencastro/">Instagram</a></li>',
            '      </ul>',
            '    </div>',
            '  </div>',
            '</section>',
        ]
    )


def build_related_projects_block(current_href: str, projects: list[dict], limit: int = 3) -> str:
    related = [project for project in projects if project["href"] != current_href][:limit]
    if not related:
        return ""

    cards_html = build_projects_list_html(related)
    return "\n".join(
        [
            '<section class="grid col-12 section-block related-list" aria-label="Outros projetos">',
            '  <h2 class="col-12">Outros Projetos</h2>',
            cards_html,
            '</section>',
        ]
    )


def build_related_posts_block(current_href: str, posts: list[dict], limit: int = 3) -> str:
    related = [post for post in posts if post["href"] != current_href][:limit]
    if not related:
        return ""

    card_lines: list[str] = []
    for post in related:
        title = html.escape(post["title"])
        summary = html.escape(post["summary"])
        href = html.escape(post["href"])
        cover = html.escape(post["listing_cover_html"])
        size_attrs = ""
        if post["listing_cover_width"] and post["listing_cover_height"]:
            size_attrs = f' width="{post["listing_cover_width"]}" height="{post["listing_cover_height"]}"'
        card_lines.extend(
            [
                '      <article class="post-item col-4">',
                f'        <a href="{href}" class="post-card-cover" aria-label="Abrir post: {title}">',
                f'          <img src="{cover}" alt="Capa do post: {title}" loading="lazy" decoding="async"{size_attrs}>',
                "        </a>",
                f'        <h3 class="p-name"><a href="{href}" class="u-url">{title}</a></h3>',
                f'        <p class="post-card-summary">{summary}</p>',
                "      </article>",
                "",
            ]
        )
    cards_html = "\n".join(card_lines).rstrip()
    return "\n".join(
        [
            '<section class="grid col-12 section-block related-list" aria-label="Outras publicações">',
            '  <h2 class="col-12">Outras Publicações</h2>',
            cards_html,
            '</section>',
        ]
    )


def build_blog_collection_jsonld(posts: list[dict], collection_url: str, collection_name: str) -> str:
    item_list = []
    for idx, post in enumerate(posts, start=1):
        item_list.append(
            {
                "@type": "ListItem",
                "position": idx,
                "url": post["canonical"],
                "item": {
                    "@type": "BlogPosting",
                    "headline": post["title"],
                    "datePublished": post["published"].date().isoformat(),
                    "url": post["canonical"],
                    "description": post["summary"],
                },
            }
        )

    payload = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": collection_name,
        "url": collection_url,
        "mainEntity": {
            "@type": "ItemList",
            "itemListElement": item_list,
        },
    }
    return (
        "  <script type=\"application/ld+json\">\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + "\n  </script>"
    )


def blog_archive_rel_path(page_number: int) -> str:
    if page_number <= 1:
        return "blog.html"
    return f"blog/page/{page_number}.html"


def paginate_archive(
    items: list[dict],
    *,
    per_page: int,
    rel_path_for_page,
    title_for_page,
    description_for_page,
    base_url: str,
) -> list[ArchivePage]:
    total_pages = max(1, (len(items) + per_page - 1) // per_page)
    pages: list[ArchivePage] = []
    for page_number in range(1, total_pages + 1):
        start = (page_number - 1) * per_page
        end = start + per_page
        rel_path = rel_path_for_page(page_number)
        pages.append(
            ArchivePage(
                page_number=page_number,
                total_pages=total_pages,
                rel_path=rel_path,
                href=rel_path_to_href(rel_path),
                canonical_url=rel_to_url(rel_path, base_url),
                title=title_for_page(page_number),
                description=description_for_page(page_number),
                items=items[start:end],
                prev_href=rel_path_to_href(rel_path_for_page(page_number - 1)) if page_number > 1 else "",
                next_href=rel_path_to_href(rel_path_for_page(page_number + 1)) if page_number < total_pages else "",
            )
        )
    return pages


def build_archive_pagination_html(page: ArchivePage, *, aria_label: str) -> str:
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
            f'<nav class="archive-pagination grid col-12 section-block" aria-label="{html.escape(aria_label, quote=True)}">',
            f'  <p class="archive-pagination-status col-12">Página {page.page_number} de {page.total_pages}</p>',
            f'  <div class="archive-pagination-links col-12">{prev_link}{next_link}</div>',
            "</nav>",
        ]
    )


def render_blog_archive_page(page: ArchivePage, *, base_url: str) -> str:
    blog_list_inner = build_blog_list_html(page.items)
    blog_jsonld_inner = build_blog_collection_jsonld(page.items, page.canonical_url, page.title.replace(" - Bolívar Alencastro", ""))
    pagination_html = build_archive_pagination_html(page, aria_label="Paginação do blog")

    lines = [
        "<!DOCTYPE html>",
        '<html lang="pt-BR">',
        "<head>",
        '  <meta charset="UTF-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        f"  <title>{html.escape(page.title)}</title>",
        f'  <meta name="description" content="{html.escape(page.description, quote=True)}">',
        '  <link rel="stylesheet" href="/style.css">',
        '  <script src="/assets/js/clarity.js" defer></script>',
        f'  <link rel="canonical" href="{html.escape(page.canonical_url, quote=True)}">',
        f'  <meta name="author" content="{html.escape(FEED_AUTHOR_NAME, quote=True)}">',
        '  <meta name="generator" content="Handcrafted HTML">',
        '  <link rel="webmention" href="https://webmention.io/bolivaralencastro.com.br/webmention">',
        '  <link rel="pingback" href="https://webmention.io/bolivaralencastro.com.br/xmlrpc">',
        '  <link rel="me" href="https://github.com/bolivaralencastro">',
        '  <link rel="me" href="https://www.instagram.com/bolivar.alencastro/">',
        '  <link rel="me" href="https://www.linkedin.com/in/bolivaralencastro/">',
        '  <meta property="og:title" content="Blog - Bolívar Alencastro">',
        f'  <meta property="og:description" content="{html.escape(page.description, quote=True)}">',
        f'  <meta property="og:url" content="{html.escape(page.canonical_url, quote=True)}">',
        '  <meta property="og:type" content="website">',
        f'  <meta property="og:image" content="{html.escape(base_url.rstrip("/") + "/assets/images/about.png", quote=True)}">',
        '  <meta name="twitter:card" content="summary_large_image">',
        '  <meta name="twitter:title" content="Blog - Bolívar Alencastro">',
        f'  <meta name="twitter:description" content="{html.escape(page.description, quote=True)}">',
        f'  <meta name="twitter:image" content="{html.escape(base_url.rstrip("/") + "/assets/images/about.png", quote=True)}">',
        blog_jsonld_inner,
        '  <meta name="view-transition" content="same-origin">',
        '  <script src="/assets/js/lightbox.js" defer></script>',
        '  <script src="/assets/js/mobile-nav.js" defer></script>',
        "</head>",
        "<body>",
        '  <div class="grain"></div>',
        '  <a href="#main" class="skip-link">Pular para o conteúdo principal</a>',
        "",
        '<header class="grid">',
        '  <div class="brand col-7"><a href="/" class="brand-link" aria-label="Ir para a página inicial"><span class="brand-mark" aria-hidden="true"><span class="dot dot-blue"></span></span><strong>Bolívar Alencastro</strong></a></div>',
        '  <nav class="col-5" aria-label="Navegação principal">',
        "    <ul>",
        '      <li><a href="/">Home</a></li>',
        '      <li><a href="/about.html">About</a></li>',
        '      <li><a href="/projects.html">Projects</a></li>',
        '      <li><a href="/blog.html" aria-current="page">Blog</a></li>',
        '      <li><a href="/now.html">Now</a></li>',
        "    </ul>",
        "  </nav>",
        "</header>",
        "",
        '  <main id="main" class="grid">',
        '    <section class="page-hero grid col-12 section-block">',
        '      <h1 class="page-title col-8">Blog</h1>',
        '      <p class="lead col-4">Notas editoriais sobre design, sistema visual e arquitetura web nativa.</p>',
        "    </section>",
        '    <section class="grid col-12 section-block">',
        '      <h2 class="col-12">Posts</h2>',
        indent_html_block(blog_list_inner, "      "),
        "    </section>",
    ]
    if pagination_html:
        lines.append(indent_html_block(pagination_html, "    "))
    lines.extend(
        [
            "  </main>",
            build_standard_footer_html(),
            "</body>",
            "</html>",
            "",
        ]
    )
    return "\n".join(lines)


def render_sitemap(base_url: str, items: list[dict]) -> str:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for item in items:
        lines.extend(
            [
                "  <url>",
                f"    <loc>{html.escape(item['loc'])}</loc>",
                f"    <lastmod>{item['lastmod']}</lastmod>",
                f"    <priority>{item['priority']:.1f}</priority>",
                "  </url>",
            ]
        )
    lines.append("</urlset>")
    lines.append("")
    return "\n".join(lines)


def render_sitemap_txt(items: list[dict]) -> str:
    return "\n".join(item["loc"] for item in items) + "\n"


def render_atom_feed(base_url: str, entries: list[dict]) -> str:
    if not entries:
        raise BuildError("Cannot generate feed.xml: no public entries found")

    feed_updated = entries[0]["published"].strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "<?xml version=\"1.0\" encoding=\"utf-8\"?>",
        '<feed xmlns="http://www.w3.org/2005/Atom">',
        "  <title>Publicações de Bolívar Alencastro</title>",
        "  <subtitle>Blog, notas e páginas publicadas em um site HTML-first.</subtitle>",
        f"  <link href=\"{base_url}/feed.xml\" rel=\"self\"/>",
        f"  <link href=\"{base_url}/\" rel=\"alternate\"/>",
        f"  <updated>{feed_updated}</updated>",
        f"  <id>{base_url}/feed.xml</id>",
        "  <author>",
        f"    <name>{html.escape(FEED_AUTHOR_NAME)}</name>",
        f"    <uri>{base_url}/about.html</uri>",
        "  </author>",
        "  <contributor>",
        f"    <name>{html.escape(FEED_AUTHOR_FALLBACK)}</name>",
        "  </contributor>",
        "",
    ]

    for entry in entries:
        published = entry["published"].strftime("%Y-%m-%dT%H:%M:%SZ")
        title = html.escape(entry["title"])
        canonical = html.escape(entry["canonical"])
        summary = html.escape(entry["summary"])
        snippet = html.escape(entry["snippet"])
        lines.extend(
            [
                "  <entry>",
                f"    <title>{title}</title>",
                f"    <link href=\"{canonical}\" rel=\"alternate\"/>",
                f"    <id>{canonical}</id>",
                f"    <published>{published}</published>",
                f"    <updated>{published}</updated>",
                f"    <summary>{summary}</summary>",
                f"    <content type=\"html\">&lt;p&gt;{snippet}&lt;/p&gt;</content>",
                "  </entry>",
                "",
            ]
        )

    lines.append("</feed>")
    lines.append("")
    return "\n".join(lines)


def write_or_check(path: pathlib.Path, content: str, check: bool, changed: list[pathlib.Path]) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if existing != content:
        changed.append(path)
        if not check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")


def remove_or_check_stale(path: pathlib.Path, check: bool, changed: list[pathlib.Path]) -> None:
    if not path.exists():
        return
    changed.append(path)
    if not check:
        path.unlink()


def infer_post_title(page: PageMeta) -> str:
    if page.h1_p_name_text:
        return page.h1_p_name_text
    if page.title_tag:
        return page.title_tag
    return ""


def infer_project_title(page: PageMeta) -> str:
    if page.h1_texts:
        return page.h1_texts[0]
    if page.title_tag:
        return page.title_tag
    return ""


def normalize_href(rel_path: str) -> str:
    return rel_path_to_href(rel_path)


def normalize_cover_for_html(url: str, base_url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme:
        return url

    base_host = (urlparse(base_url).hostname or "").lower()
    image_host = (parsed.hostname or "").lower()
    if image_host == base_host or image_host.endswith(f".{base_host}"):
        return parsed.path or url
    return url


def resolve_listing_cover(url: str, base_url: str, repo_root: pathlib.Path) -> dict[str, object]:
    normalized = normalize_cover_for_html(url, base_url)
    parsed = urlparse(normalized)
    asset_path = parsed.path or normalized

    if not asset_path.startswith("/"):
        return {"path": normalized, "width": None, "height": None}

    source_asset = repo_root / asset_path.lstrip("/")
    for filename in LISTING_CARD_FILENAMES:
        candidate = source_asset.with_name(filename)
        if candidate.exists():
            result = {"path": f"/{candidate.relative_to(repo_root).as_posix()}", "width": None, "height": None}
            if filename in {"card.png", "card.webp"}:
                result["width"] = LISTING_CARD_WIDTH
                result["height"] = LISTING_CARD_HEIGHT
            return result

    return {"path": asset_path, "width": None, "height": None}


def build_asset_versions(repo_root: pathlib.Path) -> dict[str, str]:
    versions: dict[str, str] = {}
    for public_path, relative_path in VERSIONED_ASSETS.items():
        asset_path = repo_root / relative_path
        if not asset_path.exists():
            raise BuildError(f"Missing versioned asset: {relative_path.as_posix()}")

        # Normalize text asset newlines so versioned URLs remain stable across
        # Windows and Linux checkouts.
        normalized_bytes = (
            asset_path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
        )
        digest = hashlib.sha256(normalized_bytes).hexdigest()[:10]
        versions[public_path] = digest
    return versions


def versioned_asset_url(public_path: str, version: str) -> str:
    return f"{public_path}?v={version}"


def replace_asset_reference(html_content: str, attr_name: str, public_path: str, version: str) -> str:
    versioned_url = versioned_asset_url(public_path, version)
    pattern = re.compile(rf'({attr_name}=["\']){re.escape(public_path)}(?:\?v=[0-9a-f]+)?(["\'])')
    return pattern.sub(rf"\1{versioned_url}\2", html_content)


def ensure_script_reference(html_content: str, public_path: str, defer: bool = True) -> str:
    if public_path in html_content:
        return html_content

    head_close = "</head>"
    head_idx = html_content.find(head_close)
    if head_idx == -1:
        raise BuildError(f"Missing </head> while injecting script {public_path}")

    defer_attr = " defer" if defer else ""
    snippet = f'  <script src="{public_path}"{defer_attr}></script>\n'
    return html_content[:head_idx] + snippet + html_content[head_idx:]


def apply_versioned_asset_refs(html_content: str, versions: dict[str, str]) -> str:
    updated = html_content
    updated = replace_asset_reference(updated, "href", "/style.css", versions["/style.css"])
    updated = replace_asset_reference(updated, "src", "/assets/js/clarity.js", versions["/assets/js/clarity.js"])
    updated = replace_asset_reference(updated, "src", "/assets/js/lightbox.js", versions["/assets/js/lightbox.js"])
    updated = replace_asset_reference(updated, "src", "/assets/js/mobile-nav.js", versions["/assets/js/mobile-nav.js"])
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate sitemap/feed and editorial index blocks")
    parser.add_argument("--check", action="store_true", help="Validate generated outputs without writing files")
    parser.add_argument("--base-url", default=BASE_URL_DEFAULT, help="Canonical base URL")
    args = parser.parse_args()

    repo_root = pathlib.Path(__file__).resolve().parent.parent
    base_url = args.base_url.rstrip("/")

    blog_dir = repo_root / "blog"
    projects_dir = repo_root / "projects"
    asset_versions = build_asset_versions(repo_root)

    post_files = sorted(blog_dir.glob("*.html"))
    project_files = sorted(projects_dir.glob("*.html"))

    posts: list[dict] = []
    for post_path in post_files:
        meta = parse_page(post_path, repo_root)
        title = infer_post_title(meta)
        canonical = meta.canonical
        og_image = meta.og_image
        published_raw = meta.published_datetime
        summary = meta.summary or meta.e_content_first_paragraph
        snippet = meta.e_content_first_paragraph

        missing = []
        if not title:
            missing.append("title (<h1 class='p-name'> or <title>)")
        if not canonical:
            missing.append("canonical")
        if not published_raw:
            missing.append("time.dt-published[datetime]")
        if not og_image:
            missing.append("meta property='og:image'")
        if not summary:
            missing.append("summary (.p-summary or first paragraph)")
        if not snippet:
            missing.append("content snippet (first paragraph in .e-content)")
        if missing:
            raise BuildError(f"{meta.rel_path}: missing required feed metadata: {', '.join(missing)}")

        published = parse_iso_datetime(published_raw, meta.rel_path)
        listing_cover = resolve_listing_cover(og_image, base_url, repo_root)
        posts.append(
            {
                "path": post_path,
                "rel_path": meta.rel_path,
                "href": normalize_href(meta.rel_path),
                "url": rel_to_url(meta.rel_path, base_url),
                "canonical": canonical,
                "title": title,
                "summary": summary,
                "snippet": snippet,
                "cover": og_image,
                "cover_html": normalize_cover_for_html(og_image, base_url),
                "listing_cover_html": listing_cover["path"],
                "listing_cover_width": listing_cover["width"],
                "listing_cover_height": listing_cover["height"],
                "published": published,
            }
        )

    posts.sort(key=lambda item: item["published"], reverse=True)
    notes = load_notes(repo_root, base_url=base_url)

    existing_projects_page = (repo_root / "projects.html").read_text(encoding="utf-8")
    manual_order = {}
    for idx, href in enumerate(re.findall(r"href=[\"'](/projects/[^\"']+\.html)[\"']", existing_projects_page)):
        manual_order[href] = idx

    projects: list[dict] = []
    for project_path in project_files:
        meta = parse_page(project_path, repo_root)
        title = infer_project_title(meta)
        description = meta.description
        canonical = meta.canonical
        cover = meta.og_image
        href = normalize_href(meta.rel_path)
        if not title or not description or not canonical or not cover:
            missing = []
            if not title:
                missing.append("title")
            if not description:
                missing.append("meta description")
            if not canonical:
                missing.append("canonical")
            if not cover:
                missing.append("meta property='og:image'")
            raise BuildError(f"{meta.rel_path}: missing required project metadata: {', '.join(missing)}")

        listing_cover = resolve_listing_cover(cover, base_url, repo_root)
        projects.append(
            {
                "path": project_path,
                "rel_path": meta.rel_path,
                "href": href,
                "url": rel_to_url(meta.rel_path, base_url),
                "title": title,
                "description": description,
                "canonical": canonical,
                "cover": cover,
                "cover_html": normalize_cover_for_html(cover, base_url),
                "listing_cover_html": listing_cover["path"],
                "listing_cover_width": listing_cover["width"],
                "listing_cover_height": listing_cover["height"],
            }
        )

    projects.sort(key=lambda item: (manual_order.get(item["href"], 10_000), item["href"]))

    blog_html_path = repo_root / "blog.html"
    projects_html_path = repo_root / "projects.html"
    index_html_path = repo_root / "index.html"
    links_html_path = repo_root / "links.html"
    now_html_path = repo_root / "now.html"

    notes_lastmod = max((get_lastmod_date(note.path, repo_root) for note in notes), default=get_lastmod_date(now_html_path, repo_root))
    blog_pages = paginate_archive(
        posts,
        per_page=BLOG_ARCHIVE_PAGE_SIZE,
        rel_path_for_page=blog_archive_rel_path,
        title_for_page=lambda page_number: "Blog - Bolívar Alencastro"
        if page_number == 1
        else f"Blog - Página {page_number} - Bolívar Alencastro",
        description_for_page=lambda page_number: "Artigos, ensaios e notas sobre Product Design, HTML, CSS e arquitetura estática."
        if page_number == 1
        else f"Página {page_number} do arquivo do blog com artigos e ensaios de Bolívar Alencastro.",
        base_url=base_url,
    )
    blog_page_one = blog_pages[0]
    blog_extra_pages = {page.rel_path: render_blog_archive_page(page, base_url=base_url) for page in blog_pages[1:]}
    note_pages = build_note_pages(notes, base_url=base_url)
    note_archive_pages = build_notes_archive_pages(notes, base_url=base_url)

    sitemap_items: list[dict] = []
    for root_page in ROOT_PAGES:
        page_path = repo_root / root_page
        if not page_path.exists():
            continue
        rel_path = root_page
        url = rel_to_url(rel_path, base_url)
        if rel_path == "index.html":
            priority = 1.0
        elif rel_path in {"about.html", "blog.html", "projects.html"}:
            priority = 0.8
        else:
            priority = 0.7
        sitemap_items.append(
            {
                "loc": url,
                "lastmod": get_lastmod_date(page_path, repo_root),
                "priority": priority,
            }
        )

    for rel_path in sorted(note_archive_pages):
        priority = 0.7 if rel_path == "notes/index.html" else 0.5
        sitemap_items.append(
            {
                "loc": rel_to_url(rel_path, base_url),
                "lastmod": notes_lastmod,
                "priority": priority,
            }
        )

    for rel_path in sorted(blog_extra_pages):
        page_items = next(page.items for page in blog_pages[1:] if page.rel_path == rel_path)
        lastmod = max(get_lastmod_date(item["path"], repo_root) for item in page_items)
        sitemap_items.append(
            {
                "loc": rel_to_url(rel_path, base_url),
                "lastmod": lastmod,
                "priority": 0.6,
            }
        )

    for post in posts:
        sitemap_items.append(
            {
                "loc": post["url"],
                "lastmod": get_lastmod_date(post["path"], repo_root),
                "priority": 0.6,
            }
        )

    for note in notes:
        sitemap_items.append(
            {
                "loc": note.canonical_url,
                "lastmod": get_lastmod_date(note.path, repo_root),
                "priority": 0.6,
            }
        )

    for project in projects:
        sitemap_items.append(
            {
                "loc": project["url"],
                "lastmod": get_lastmod_date(project["path"], repo_root),
                "priority": 0.7,
            }
        )

    sitemap_content = render_sitemap(base_url, sitemap_items)
    sitemap_txt_content = render_sitemap_txt(sitemap_items)

    feed_entries = list(posts)
    for note in notes:
        feed_entries.append(
            {
                "title": note.display_title,
                "canonical": note.canonical_url,
                "summary": note.description,
                "snippet": note.excerpt_text or note.description,
                "published": dt.datetime.combine(note.date, dt.time.min, tzinfo=dt.timezone.utc),
            }
        )
    feed_entries.sort(key=lambda item: item["published"], reverse=True)
    feed_content = render_atom_feed(base_url, feed_entries)

    blog_list_inner = build_blog_list_html(blog_page_one.items)
    blog_jsonld_inner = build_blog_collection_jsonld(blog_page_one.items, blog_page_one.canonical_url, "Blog - Bolívar Alencastro")
    blog_pagination_inner = build_archive_pagination_html(blog_page_one, aria_label="Paginação do blog")
    projects_list_inner = build_projects_list_html(projects)
    featured_projects_inner = build_featured_projects_html(projects, limit=3)
    latest_post_inner = build_latest_post_html(posts[0])
    links_latest_post_inner = build_links_latest_post_html(posts[0])
    links_featured_project_inner = build_links_featured_project_html(projects[0])
    links_primary_actions_inner = build_links_primary_actions_html(posts[0], projects[0])
    now_notes_inner = generate_now_notes_html(repo_root, base_url=base_url)

    blog_html = blog_html_path.read_text(encoding="utf-8")
    blog_html = ensure_auto_block_before_token(blog_html, "blog-pagination", "</main>")
    blog_html = replace_auto_block(blog_html, "blog-jsonld", blog_jsonld_inner)
    blog_html = replace_auto_block(blog_html, "blog-list", blog_list_inner)
    blog_html = replace_auto_block(blog_html, "blog-pagination", blog_pagination_inner)
    projects_html = replace_auto_block(
        projects_html_path.read_text(encoding="utf-8"), "projects-list", projects_list_inner
    )
    index_html = index_html_path.read_text(encoding="utf-8")
    index_html = replace_auto_block(index_html, "featured-projects", featured_projects_inner)
    index_html = replace_auto_block(index_html, "latest-post", latest_post_inner)
    links_html = links_html_path.read_text(encoding="utf-8")
    links_html = replace_auto_block(links_html, "links-primary-actions", links_primary_actions_inner)
    now_html = replace_auto_block(now_html_path.read_text(encoding="utf-8"), NOTE_AUTO_BLOCK, now_notes_inner)

    post_detail_managed: dict[pathlib.Path, str] = {}
    for post in posts:
        post_content = post["path"].read_text(encoding="utf-8")
        post_content = ensure_auto_block_before_token(post_content, "post-related-posts", "</article>")
        post_content = replace_auto_block(
            post_content,
            "post-related-posts",
            build_related_posts_block(post["href"], posts, limit=3),
        )
        post_content = replace_auto_block(post_content, "post-related-projects", "")
        post_content = ensure_standard_footer(post_content)
        post_detail_managed[post["path"]] = post_content

    project_detail_managed: dict[pathlib.Path, str] = {}
    for project in projects:
        project_content = project["path"].read_text(encoding="utf-8")
        project_content = rewrite_project_detail_blocks(
            project_content,
            build_author_card_html(),
            build_related_projects_block(project["href"], projects, limit=3),
        )
        project_content = ensure_standard_footer(project_content)
        project_detail_managed[project["path"]] = project_content

    changed: list[pathlib.Path] = []
    write_or_check(repo_root / "sitemap.xml", sitemap_content, args.check, changed)
    write_or_check(repo_root / "sitemap.txt", sitemap_txt_content, args.check, changed)
    write_or_check(repo_root / "feed.xml", feed_content, args.check, changed)
    write_or_check(repo_root / "feed.txt", feed_content, args.check, changed)

    managed_pages = {
        blog_html_path: blog_html,
        projects_html_path: projects_html,
        index_html_path: index_html,
        links_html_path: links_html,
        now_html_path: now_html,
    }
    managed_pages.update({repo_root / rel_path: content for rel_path, content in blog_extra_pages.items()})
    managed_pages.update({repo_root / rel_path: content for rel_path, content in note_pages.items()})
    managed_pages.update({repo_root / rel_path: content for rel_path, content in note_archive_pages.items()})
    managed_pages.update(post_detail_managed)
    managed_pages.update(project_detail_managed)
    public_pages = [repo_root / name for name in ROOT_PAGES]
    public_pages.extend(sorted(repo_root / rel_path for rel_path in blog_extra_pages))
    public_pages.extend(sorted(repo_root / rel_path for rel_path in note_pages))
    public_pages.extend(sorted(repo_root / rel_path for rel_path in note_archive_pages))
    public_pages.extend(post_files)
    public_pages.extend(project_files)

    existing_note_generated = set((repo_root / "notes").glob("**/*.html")) if (repo_root / "notes").exists() else set()
    expected_note_generated = {repo_root / rel_path for rel_path in note_pages} | {
        repo_root / rel_path for rel_path in note_archive_pages
    }
    for stale_path in sorted(existing_note_generated - expected_note_generated):
        remove_or_check_stale(stale_path, args.check, changed)

    existing_blog_generated = set((repo_root / "blog" / "page").glob("*.html")) if (repo_root / "blog" / "page").exists() else set()
    expected_blog_generated = {repo_root / rel_path for rel_path in blog_extra_pages}
    for stale_path in sorted(existing_blog_generated - expected_blog_generated):
        remove_or_check_stale(stale_path, args.check, changed)

    for page_path in public_pages:
        source_html = managed_pages.get(page_path)
        if source_html is None:
            source_html = page_path.read_text(encoding="utf-8")
        source_html = ensure_script_reference(source_html, "/assets/js/lightbox.js")
        source_html = ensure_script_reference(source_html, "/assets/js/mobile-nav.js")
        versioned_html = apply_versioned_asset_refs(source_html, asset_versions)
        write_or_check(page_path, versioned_html, args.check, changed)

    if changed:
        if args.check:
            print("Generated files are stale:")
            for item in changed:
                print(f" - {item.relative_to(repo_root).as_posix()}")
            return 1
        print("Updated files:")
        for item in changed:
            print(f" - {item.relative_to(repo_root).as_posix()}")
    else:
        print("No metadata changes needed.")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
