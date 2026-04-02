#!/usr/bin/env python3
"""Validate editorial and SEO quality for the static portfolio site."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from html.parser import HTMLParser
import pathlib
import re
import sys
from dataclasses import dataclass
from typing import Iterable, List
from urllib.parse import parse_qs, urlsplit

BASE_URL_DEFAULT = "https://bolivaralencastro.com.br"
ROOT_PAGES = ["index.html", "about.html", "blog.html", "projects.html", "now.html"]
CLARITY_SCRIPT_SRC = "/assets/js/clarity.js"
MAIN_STYLESHEET_HREF = "/style.css"
CLARITY_CSP_SOURCES = ["https://*.clarity.ms", "https://c.bing.com"]
VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


@dataclass
class ImageMeta:
    src: str = ""
    alt: str = ""
    width: str = ""
    height: str = ""
    loading: str = ""
    decoding: str = ""
    fetchpriority: str = ""
    in_e_content: bool = False


@dataclass
class PageMeta:
    path: pathlib.Path
    rel_path: str
    lang: str = ""
    title_tag: str = ""
    description: str = ""
    canonical: str = ""
    h1_count: int = 0
    h1_texts: List[str] = None
    published_datetime: str = ""
    jsonld_blocks: List[str] = None
    links: List[str] = None
    image_alts: List[str] = None
    og_title: str = ""
    og_description: str = ""
    og_url: str = ""
    og_image: str = ""
    twitter_card: str = ""
    twitter_title: str = ""
    twitter_description: str = ""
    twitter_image: str = ""
    script_srcs: List[str] = None
    deferred_script_srcs: List[str] = None
    stylesheet_hrefs: List[str] = None
    csp_content: str = ""
    images: List[ImageMeta] = None

    def __post_init__(self) -> None:
        if self.h1_texts is None:
            self.h1_texts = []
        if self.jsonld_blocks is None:
            self.jsonld_blocks = []
        if self.links is None:
            self.links = []
        if self.image_alts is None:
            self.image_alts = []
        if self.script_srcs is None:
            self.script_srcs = []
        if self.deferred_script_srcs is None:
            self.deferred_script_srcs = []
        if self.stylesheet_hrefs is None:
            self.stylesheet_hrefs = []
        if self.images is None:
            self.images = []


class PageParser(HTMLParser):
    def __init__(self, meta: PageMeta) -> None:
        super().__init__(convert_charrefs=True)
        self.meta = meta
        self._in_title = False
        self._in_h1 = False
        self._h1_chunks: List[str] = []
        self._in_jsonld_script = False
        self._jsonld_chunks: List[str] = []
        self._tag_stack: List[bool] = []

    @staticmethod
    def _classes(attrs: dict) -> set[str]:
        classes = attrs.get("class", "")
        return {item.strip() for item in classes.split() if item.strip()}

    def handle_starttag(self, tag: str, attrs_list) -> None:
        attrs = dict(attrs_list)
        classes = self._classes(attrs)
        in_e_content = "e-content" in classes or any(self._tag_stack)
        if tag not in VOID_TAGS:
            self._tag_stack.append("e-content" in classes)

        if tag == "html":
            self.meta.lang = (attrs.get("lang") or "").strip()

        if tag == "title":
            self._in_title = True

        if tag == "meta":
            name = (attrs.get("name") or "").lower().strip()
            prop = (attrs.get("property") or "").lower().strip()
            http_equiv = (attrs.get("http-equiv") or "").lower().strip()
            if name == "description":
                self.meta.description = (attrs.get("content") or "").strip()
            if prop == "og:title":
                self.meta.og_title = (attrs.get("content") or "").strip()
            if prop == "og:description":
                self.meta.og_description = (attrs.get("content") or "").strip()
            if prop == "og:url":
                self.meta.og_url = (attrs.get("content") or "").strip()
            if prop == "og:image":
                self.meta.og_image = (attrs.get("content") or "").strip()
            if name == "twitter:card":
                self.meta.twitter_card = (attrs.get("content") or "").strip()
            if name == "twitter:title":
                self.meta.twitter_title = (attrs.get("content") or "").strip()
            if name == "twitter:description":
                self.meta.twitter_description = (attrs.get("content") or "").strip()
            if name == "twitter:image":
                self.meta.twitter_image = (attrs.get("content") or "").strip()
            if http_equiv == "content-security-policy":
                self.meta.csp_content = (attrs.get("content") or "").strip()

        if tag == "link":
            rel_values = {item.strip() for item in (attrs.get("rel") or "").lower().split() if item.strip()}
            href = (attrs.get("href") or "").strip()
            if "canonical" in rel_values:
                self.meta.canonical = href
            if "stylesheet" in rel_values and href:
                self.meta.stylesheet_hrefs.append(href)

        if tag == "h1":
            self.meta.h1_count += 1
            self._in_h1 = True
            self._h1_chunks = []

        if tag == "time" and "dt-published" in classes:
            self.meta.published_datetime = (attrs.get("datetime") or "").strip()

        if tag == "script" and (attrs.get("type") or "").lower() == "application/ld+json":
            self._in_jsonld_script = True
            self._jsonld_chunks = []
        elif tag == "script":
            src = (attrs.get("src") or "").strip()
            if src:
                self.meta.script_srcs.append(src)
                if "defer" in attrs:
                    self.meta.deferred_script_srcs.append(src)

        if tag == "a":
            href = (attrs.get("href") or "").strip()
            if href:
                self.meta.links.append(href)

        if tag == "img":
            self.meta.image_alts.append((attrs.get("alt") or "").strip())
            self.meta.images.append(
                ImageMeta(
                    src=(attrs.get("src") or "").strip(),
                    alt=(attrs.get("alt") or "").strip(),
                    width=(attrs.get("width") or "").strip(),
                    height=(attrs.get("height") or "").strip(),
                    loading=(attrs.get("loading") or "").strip().lower(),
                    decoding=(attrs.get("decoding") or "").strip().lower(),
                    fetchpriority=(attrs.get("fetchpriority") or "").strip().lower(),
                    in_e_content=in_e_content,
                )
            )

    def handle_startendtag(self, tag: str, attrs_list) -> None:
        self.handle_starttag(tag, attrs_list)

    def handle_endtag(self, tag: str) -> None:
        if self._tag_stack:
            self._tag_stack.pop()

        if tag == "title":
            self._in_title = False

        if tag == "h1":
            self._in_h1 = False
            text = " ".join("".join(self._h1_chunks).split()).strip()
            if text:
                self.meta.h1_texts.append(text)

        if tag == "script" and self._in_jsonld_script:
            self._in_jsonld_script = False
            payload = "".join(self._jsonld_chunks).strip()
            if payload:
                self.meta.jsonld_blocks.append(payload)

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.meta.title_tag += data
        if self._in_h1:
            self._h1_chunks.append(data)
        if self._in_jsonld_script:
            self._jsonld_chunks.append(data)


def parse_page(path: pathlib.Path, repo_root: pathlib.Path) -> PageMeta:
    rel_path = path.relative_to(repo_root).as_posix()
    meta = PageMeta(path=path, rel_path=rel_path)
    parser = PageParser(meta)
    parser.feed(path.read_text(encoding="utf-8"))
    meta.title_tag = " ".join(meta.title_tag.split()).strip()
    return meta


def iter_public_pages(repo_root: pathlib.Path) -> List[pathlib.Path]:
    pages: List[pathlib.Path] = []
    for name in ROOT_PAGES:
        path = repo_root / name
        if path.exists():
            pages.append(path)

    pages.extend(sorted((repo_root / "blog").glob("*.html")))
    pages.extend(sorted((repo_root / "projects").glob("*.html")))
    return pages


def is_valid_iso_datetime(value: str) -> bool:
    raw = (value or "").strip()
    if not raw:
        return False
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return True
    try:
        dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def extract_jsonld_types(payload: str) -> set[str]:
    types: set[str] = set()

    def walk(obj) -> None:
        if isinstance(obj, dict):
            atype = obj.get("@type")
            if isinstance(atype, str):
                types.add(atype)
            elif isinstance(atype, list):
                for item in atype:
                    if isinstance(item, str):
                        types.add(item)
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError:
        if "BlogPosting" in payload:
            types.add("BlogPosting")
        return types

    walk(decoded)
    return types


def canonical_expected(base_url: str, rel_path: str) -> str:
    if rel_path == "index.html":
        return f"{base_url}/"
    if rel_path.endswith("/index.html"):
        return f"{base_url}/{rel_path.removesuffix('/index.html')}/"
    return f"{base_url}/{rel_path}"


def resolve_internal_link(repo_root: pathlib.Path, href: str) -> pathlib.Path:
    cleaned = href.split("#", 1)[0].split("?", 1)[0]
    if cleaned == "/":
        return repo_root / "index.html"
    if cleaned.endswith("/"):
        cleaned = f"{cleaned}index.html"
    return repo_root / cleaned.lstrip("/")


def asset_path(value: str) -> str:
    return urlsplit(value).path


def has_version_query(value: str) -> bool:
    return bool(parse_qs(urlsplit(value).query).get("v", [""])[0])


def validate_robots(repo_root: pathlib.Path, base_url: str, errors: list[str]) -> None:
    robots_path = repo_root / "robots.txt"
    if not robots_path.exists():
        errors.append("robots.txt: file missing")
        return

    content = robots_path.read_text(encoding="utf-8")
    expected = f"Sitemap: {base_url}/sitemap.xml"
    if expected not in content:
        errors.append(f"robots.txt: missing expected sitemap declaration '{expected}'")


def validate_links(repo_root: pathlib.Path, pages: Iterable[PageMeta], errors: list[str]) -> None:
    for page in pages:
        for href in page.links:
            if href.startswith(("http://", "https://", "mailto:", "tel:")):
                continue
            if href.startswith("#"):
                continue
            if not href.startswith("/"):
                continue
            target = resolve_internal_link(repo_root, href)
            if not target.exists():
                errors.append(f"{page.rel_path}: broken internal link '{href}' (target '{target.relative_to(repo_root)}' not found)")


def class_exists(html_content: str, class_name: str) -> bool:
    pattern = re.compile(rf'class\s*=\s*["\'][^"\']*\b{re.escape(class_name)}\b[^"\']*["\']', flags=re.I)
    return bool(pattern.search(html_content))


def extract_first_class_text(html_content: str, class_name: str) -> str:
    pattern = re.compile(
        rf"<(?P<tag>[a-z0-9]+)[^>]*class\s*=\s*[\"'][^\"']*\b{re.escape(class_name)}\b[^\"']*[\"'][^>]*>(?P<body>.*?)</(?P=tag)>",
        flags=re.I | re.S,
    )
    match = pattern.search(html_content)
    if not match:
        return ""
    body = re.sub(r"<[^>]+>", " ", match.group("body"))
    return " ".join(body.split()).strip()


def class_inside_post_meta(html_content: str, class_name: str) -> bool:
    block_pattern = re.compile(
        r"<(?P<tag>[a-z0-9]+)[^>]*class\s*=\s*[\"'][^\"']*\bpost-meta\b[^\"']*[\"'][^>]*>(?P<body>.*?)</(?P=tag)>",
        flags=re.I | re.S,
    )
    block_match = block_pattern.search(html_content)
    if not block_match:
        return False

    body = block_match.group("body")
    class_pattern = re.compile(rf'class\s*=\s*["\'][^"\']*\b{re.escape(class_name)}\b[^"\']*["\']', flags=re.I)
    return bool(class_pattern.search(body))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate editorial and SEO metadata")
    parser.add_argument("--base-url", default=BASE_URL_DEFAULT, help="Canonical base URL")
    args = parser.parse_args()

    repo_root = pathlib.Path(__file__).resolve().parent.parent
    base_url = args.base_url.rstrip("/")

    public_paths = iter_public_pages(repo_root)
    metas = [parse_page(path, repo_root) for path in public_paths]

    errors: list[str] = []
    warnings: list[str] = []

    for page in metas:
        expected_canonical = canonical_expected(base_url, page.rel_path)

        if not page.title_tag:
            errors.append(f"{page.rel_path}: missing <title>")
        if not page.description:
            errors.append(f"{page.rel_path}: missing <meta name='description'>")
        if not page.canonical:
            errors.append(f"{page.rel_path}: missing <link rel='canonical'>")
        elif not page.canonical.startswith(f"{base_url}/"):
            errors.append(f"{page.rel_path}: canonical must be absolute and start with {base_url}/")
        if page.canonical and page.canonical != expected_canonical:
            errors.append(f"{page.rel_path}: canonical mismatch (expected {expected_canonical})")

        if page.h1_count != 1:
            errors.append(f"{page.rel_path}: expected exactly one <h1>, found {page.h1_count}")
        if page.lang != "pt-BR":
            errors.append(f"{page.rel_path}: <html lang> must be 'pt-BR' (found '{page.lang or 'missing'}')")
        matching_stylesheets = [href for href in page.stylesheet_hrefs if asset_path(href) == MAIN_STYLESHEET_HREF]
        if not matching_stylesheets:
            errors.append(f"{page.rel_path}: missing main stylesheet '{MAIN_STYLESHEET_HREF}'")
        elif not any(has_version_query(href) for href in matching_stylesheets):
            errors.append(f"{page.rel_path}: main stylesheet must include a version query parameter")

        matching_clarity_scripts = [src for src in page.script_srcs if asset_path(src) == CLARITY_SCRIPT_SRC]
        matching_deferred_clarity_scripts = [
            src for src in page.deferred_script_srcs if asset_path(src) == CLARITY_SCRIPT_SRC
        ]
        if not matching_clarity_scripts:
            errors.append(f"{page.rel_path}: missing Clarity loader script '{CLARITY_SCRIPT_SRC}'")
        elif not any(has_version_query(src) for src in matching_clarity_scripts):
            errors.append(f"{page.rel_path}: Clarity loader script must include a version query parameter")
        if not matching_deferred_clarity_scripts:
            errors.append(f"{page.rel_path}: Clarity loader script must use 'defer'")
        if page.csp_content:
            for source in CLARITY_CSP_SOURCES:
                if source not in page.csp_content:
                    errors.append(f"{page.rel_path}: CSP must allow Clarity source '{source}'")

        if page.rel_path.startswith("blog/"):
            raw_html = page.path.read_text(encoding="utf-8")
            if not page.published_datetime:
                errors.append(f"{page.rel_path}: missing time.dt-published[datetime]")
            elif not is_valid_iso_datetime(page.published_datetime):
                errors.append(f"{page.rel_path}: dt-published datetime must be ISO format")
            if not page.og_image:
                errors.append(f"{page.rel_path}: missing og:image (required for blog listing cover)")

            has_blog_posting = any("BlogPosting" in extract_jsonld_types(payload) for payload in page.jsonld_blocks)
            if not has_blog_posting:
                errors.append(f"{page.rel_path}: missing JSON-LD BlogPosting")

            h1 = page.h1_texts[0] if page.h1_texts else ""
            if h1 and page.title_tag and h1 not in page.title_tag:
                errors.append(f"{page.rel_path}: <title> should include the main <h1> text")

            if not class_exists(raw_html, "post-meta"):
                errors.append(f"{page.rel_path}: missing visible post metadata block (.post-meta)")
            elif not class_inside_post_meta(raw_html, "u-url"):
                errors.append(f"{page.rel_path}: permalink (.u-url) must be inside .post-meta")

            category_text = extract_first_class_text(raw_html, "p-category")
            if not category_text:
                errors.append(f"{page.rel_path}: missing visible category (.p-category) below title")

            reading_time_text = extract_first_class_text(raw_html, "reading-time")
            if not reading_time_text:
                errors.append(f"{page.rel_path}: missing visible reading time (.reading-time) below title")
            elif not re.search(r"\b\d+\s*min\b", reading_time_text.lower()):
                errors.append(f"{page.rel_path}: reading time must include minutes (ex: '6 min de leitura')")

        if page.rel_path == "blog.html":
            has_collection_jsonld = any(
                bool({"CollectionPage", "Blog"} & extract_jsonld_types(payload)) for payload in page.jsonld_blocks
            )
            has_item_list_jsonld = any("ItemList" in extract_jsonld_types(payload) for payload in page.jsonld_blocks)
            if not has_collection_jsonld:
                errors.append("blog.html: missing JSON-LD for CollectionPage or Blog")
            if not has_item_list_jsonld:
                errors.append("blog.html: missing JSON-LD ItemList for post listing")

            raw_html = page.path.read_text(encoding="utf-8")
            if "<!-- AUTO:blog-jsonld:start -->" not in raw_html or "<!-- AUTO:blog-jsonld:end -->" not in raw_html:
                errors.append("blog.html: missing AUTO markers for blog JSON-LD block")

        if page.rel_path.startswith("projects/"):
            project_content_images = [image for image in page.images if image.in_e_content]
            if not page.title_tag:
                errors.append(f"{page.rel_path}: missing title")
            if not page.description:
                errors.append(f"{page.rel_path}: missing description")
            if not page.canonical:
                errors.append(f"{page.rel_path}: missing canonical")
            if not page.og_image:
                errors.append(f"{page.rel_path}: missing og:image (required for project listing cover)")
            if page.h1_count < 1:
                errors.append(f"{page.rel_path}: at least one <h1> is required")
            if any(not alt for alt in page.image_alts):
                errors.append(f"{page.rel_path}: all <img> must include non-empty alt text")
            if not project_content_images:
                errors.append(f"{page.rel_path}: project content should include at least one image inside .e-content")
            for index, image in enumerate(project_content_images, start=1):
                if not image.width or not image.height or not image.width.isdigit() or not image.height.isdigit():
                    errors.append(
                        f"{page.rel_path}: project content image #{index} must declare numeric width and height"
                    )
                if image.decoding != "async":
                    errors.append(
                        f"{page.rel_path}: project content image #{index} must use decoding='async'"
                    )
                if index == 1:
                    if image.loading == "lazy":
                        errors.append(
                            f"{page.rel_path}: first project content image must not use loading='lazy'"
                        )
                    if image.fetchpriority != "high":
                        errors.append(
                            f"{page.rel_path}: first project content image must use fetchpriority='high'"
                        )
                elif image.loading != "lazy":
                    errors.append(
                        f"{page.rel_path}: project content image #{index} must use loading='lazy'"
                    )

        if page.rel_path in ROOT_PAGES:
            if not page.og_title:
                warnings.append(f"{page.rel_path}: missing og:title")
            if not page.og_description:
                warnings.append(f"{page.rel_path}: missing og:description")
            if not page.og_url:
                warnings.append(f"{page.rel_path}: missing og:url")
            if not page.og_image:
                warnings.append(f"{page.rel_path}: missing og:image")
            if not page.twitter_card:
                warnings.append(f"{page.rel_path}: missing twitter:card")
            if not page.twitter_title:
                warnings.append(f"{page.rel_path}: missing twitter:title")
            if not page.twitter_description:
                warnings.append(f"{page.rel_path}: missing twitter:description")
            if not page.twitter_image:
                warnings.append(f"{page.rel_path}: missing twitter:image")

    validate_robots(repo_root, base_url, errors)
    validate_links(repo_root, metas, errors)

    if errors:
        print("Validation errors:")
        for item in errors:
            print(f" - {item}")

    if warnings:
        print("Validation warnings:")
        for item in warnings:
            print(f" - {item}")

    if errors:
        return 1

    print("Validation passed.")
    if warnings:
        print("Warnings are informational and do not fail CI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
