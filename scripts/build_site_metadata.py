#!/usr/bin/env python3
"""Generate sitemap, Atom feed, and auto-managed index blocks for the static site."""

from __future__ import annotations

import argparse
import datetime as dt
import html
from html.parser import HTMLParser
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import List

BASE_URL_DEFAULT = "https://bolivaralencastro.com.br"
ROOT_PAGES = ["index.html", "about.html", "blog.html", "projects.html", "now.html"]
FEED_AUTHOR_NAME = "Bolívar Alencastro"
FEED_AUTHOR_FALLBACK = "Bolivar Alencastro"


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
    return f"{base_url}/{rel_path}"


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


def format_pt_date_short(date_value: dt.datetime) -> str:
    return date_value.strftime("%d/%m/%Y")


def build_blog_list_html(posts: list[dict]) -> str:
    lines: List[str] = []
    for post in posts:
        title = html.escape(post["title"])
        summary = html.escape(post["summary"])
        href = html.escape(post["href"])
        date_iso = post["published"].date().isoformat()
        date_human = format_pt_date_short(post["published"])
        lines.extend(
            [
                "      <article class=\"post-item h-entry col-8\">",
                f"        <h3 class=\"p-name\"><a href=\"{href}\" class=\"u-url\">{title}</a></h3>",
                f"        <time class=\"dt-published\" datetime=\"{date_iso}\">{date_human}</time>",
                f"        <p class=\"p-summary\">{summary}</p>",
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
        lines.extend(
            [
                "      <article class=\"project-item col-4\">",
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
    date_iso = latest_post["published"].date().isoformat()
    date_human = format_pt_date_short(latest_post["published"])

    return "\n".join(
        [
            "      <article class=\"post-item h-entry col-8\">",
            f"        <h3 class=\"p-name\"><a href=\"{href}\" class=\"u-url\">{title}</a></h3>",
            f"        <time class=\"dt-published\" datetime=\"{date_iso}\">{date_human}</time>",
            f"        <p class=\"p-summary\">{summary}</p>",
            "      </article>",
        ]
    )


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


def render_atom_feed(base_url: str, posts: list[dict]) -> str:
    if not posts:
        raise BuildError("Cannot generate feed.xml: no blog posts found in /blog")

    feed_updated = posts[0]["published"].strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "<?xml version=\"1.0\" encoding=\"utf-8\"?>",
        '<feed xmlns="http://www.w3.org/2005/Atom">',
        "  <title>Blog de Bolívar Alencastro</title>",
        "  <subtitle>Product Design e Arquitetura Web Nativa</subtitle>",
        f"  <link href=\"{base_url}/feed.xml\" rel=\"self\"/>",
        f"  <link href=\"{base_url}/blog.html\" rel=\"alternate\"/>",
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

    for post in posts:
        published = post["published"].strftime("%Y-%m-%dT%H:%M:%SZ")
        title = html.escape(post["title"])
        canonical = html.escape(post["canonical"])
        summary = html.escape(post["summary"])
        snippet = html.escape(post["snippet"])
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
            path.write_text(content, encoding="utf-8", newline="\n")


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
    return "/" if rel_path == "index.html" else f"/{rel_path}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate sitemap/feed and editorial index blocks")
    parser.add_argument("--check", action="store_true", help="Validate generated outputs without writing files")
    parser.add_argument("--base-url", default=BASE_URL_DEFAULT, help="Canonical base URL")
    args = parser.parse_args()

    repo_root = pathlib.Path(__file__).resolve().parent.parent
    base_url = args.base_url.rstrip("/")

    blog_dir = repo_root / "blog"
    projects_dir = repo_root / "projects"

    post_files = sorted(blog_dir.glob("*.html"))
    project_files = sorted(projects_dir.glob("*.html"))

    posts: list[dict] = []
    for post_path in post_files:
        meta = parse_page(post_path, repo_root)
        title = infer_post_title(meta)
        canonical = meta.canonical
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
        if not summary:
            missing.append("summary (.p-summary or first paragraph)")
        if not snippet:
            missing.append("content snippet (first paragraph in .e-content)")
        if missing:
            raise BuildError(f"{meta.rel_path}: missing required feed metadata: {', '.join(missing)}")

        published = parse_iso_datetime(published_raw, meta.rel_path)
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
                "published": published,
            }
        )

    posts.sort(key=lambda item: item["published"], reverse=True)

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
        href = normalize_href(meta.rel_path)
        if not title or not description or not canonical:
            missing = []
            if not title:
                missing.append("title")
            if not description:
                missing.append("meta description")
            if not canonical:
                missing.append("canonical")
            raise BuildError(f"{meta.rel_path}: missing required project metadata: {', '.join(missing)}")

        projects.append(
            {
                "path": project_path,
                "rel_path": meta.rel_path,
                "href": href,
                "url": rel_to_url(meta.rel_path, base_url),
                "title": title,
                "description": description,
                "canonical": canonical,
            }
        )

    projects.sort(key=lambda item: (manual_order.get(item["href"], 10_000), item["href"]))

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

    for post in posts:
        sitemap_items.append(
            {
                "loc": post["url"],
                "lastmod": get_lastmod_date(post["path"], repo_root),
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
    feed_content = render_atom_feed(base_url, posts)

    blog_list_inner = build_blog_list_html(posts)
    projects_list_inner = build_projects_list_html(projects)
    latest_post_inner = build_latest_post_html(posts[0])

    blog_html_path = repo_root / "blog.html"
    projects_html_path = repo_root / "projects.html"
    index_html_path = repo_root / "index.html"

    blog_html = replace_auto_block(blog_html_path.read_text(encoding="utf-8"), "blog-list", blog_list_inner)
    projects_html = replace_auto_block(
        projects_html_path.read_text(encoding="utf-8"), "projects-list", projects_list_inner
    )
    index_html = replace_auto_block(index_html_path.read_text(encoding="utf-8"), "latest-post", latest_post_inner)

    changed: list[pathlib.Path] = []
    write_or_check(repo_root / "sitemap.xml", sitemap_content, args.check, changed)
    write_or_check(repo_root / "feed.xml", feed_content, args.check, changed)
    write_or_check(repo_root / "feed.txt", feed_content, args.check, changed)
    write_or_check(blog_html_path, blog_html, args.check, changed)
    write_or_check(projects_html_path, projects_html, args.check, changed)
    write_or_check(index_html_path, index_html, args.check, changed)

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
