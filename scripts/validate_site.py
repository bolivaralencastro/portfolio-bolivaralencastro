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

BASE_URL_DEFAULT = "https://bolivaralencastro.com.br"
ROOT_PAGES = ["index.html", "about.html", "blog.html", "projects.html", "now.html"]


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

    def __post_init__(self) -> None:
        if self.h1_texts is None:
            self.h1_texts = []
        if self.jsonld_blocks is None:
            self.jsonld_blocks = []
        if self.links is None:
            self.links = []
        if self.image_alts is None:
            self.image_alts = []


class PageParser(HTMLParser):
    def __init__(self, meta: PageMeta) -> None:
        super().__init__(convert_charrefs=True)
        self.meta = meta
        self._in_title = False
        self._in_h1 = False
        self._h1_chunks: List[str] = []
        self._in_jsonld_script = False
        self._jsonld_chunks: List[str] = []

    @staticmethod
    def _classes(attrs: dict) -> set[str]:
        classes = attrs.get("class", "")
        return {item.strip() for item in classes.split() if item.strip()}

    def handle_starttag(self, tag: str, attrs_list) -> None:
        attrs = dict(attrs_list)
        classes = self._classes(attrs)

        if tag == "html":
            self.meta.lang = (attrs.get("lang") or "").strip()

        if tag == "title":
            self._in_title = True

        if tag == "meta":
            name = (attrs.get("name") or "").lower().strip()
            prop = (attrs.get("property") or "").lower().strip()
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

        if tag == "link" and (attrs.get("rel") or "").lower() == "canonical":
            self.meta.canonical = (attrs.get("href") or "").strip()

        if tag == "h1":
            self.meta.h1_count += 1
            self._in_h1 = True
            self._h1_chunks = []

        if tag == "time" and "dt-published" in classes:
            self.meta.published_datetime = (attrs.get("datetime") or "").strip()

        if tag == "script" and (attrs.get("type") or "").lower() == "application/ld+json":
            self._in_jsonld_script = True
            self._jsonld_chunks = []

        if tag == "a":
            href = (attrs.get("href") or "").strip()
            if href:
                self.meta.links.append(href)

        if tag == "img":
            self.meta.image_alts.append((attrs.get("alt") or "").strip())

    def handle_endtag(self, tag: str) -> None:
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
    return f"{base_url}/{rel_path}"


def resolve_internal_link(repo_root: pathlib.Path, href: str) -> pathlib.Path:
    cleaned = href.split("#", 1)[0].split("?", 1)[0]
    if cleaned == "/":
        return repo_root / "index.html"
    if cleaned.endswith("/"):
        cleaned = f"{cleaned}index.html"
    return repo_root / cleaned.lstrip("/")


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

        if page.rel_path.startswith("blog/"):
            if not page.published_datetime:
                errors.append(f"{page.rel_path}: missing time.dt-published[datetime]")
            elif not is_valid_iso_datetime(page.published_datetime):
                errors.append(f"{page.rel_path}: dt-published datetime must be ISO format")

            has_blog_posting = any("BlogPosting" in extract_jsonld_types(payload) for payload in page.jsonld_blocks)
            if not has_blog_posting:
                errors.append(f"{page.rel_path}: missing JSON-LD BlogPosting")

            h1 = page.h1_texts[0] if page.h1_texts else ""
            if h1 and page.title_tag and h1 not in page.title_tag:
                errors.append(f"{page.rel_path}: <title> should include the main <h1> text")

        if page.rel_path.startswith("projects/"):
            if not page.title_tag:
                errors.append(f"{page.rel_path}: missing title")
            if not page.description:
                errors.append(f"{page.rel_path}: missing description")
            if not page.canonical:
                errors.append(f"{page.rel_path}: missing canonical")
            if page.h1_count < 1:
                errors.append(f"{page.rel_path}: at least one <h1> is required")
            if any(not alt for alt in page.image_alts):
                errors.append(f"{page.rel_path}: all <img> must include non-empty alt text")

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
