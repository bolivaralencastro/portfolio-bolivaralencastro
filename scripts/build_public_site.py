#!/usr/bin/env python3
"""Build the exact allowlisted artifact published by GitHub Pages."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "_site"

ROOT_PUBLIC_FILES = {
    ".nojekyll",
    "CNAME",
    "_redirects",
    "favicon.ico",
    "feed.txt",
    "feed.xml",
    "humans.txt",
    "llms.txt",
    "robots.txt",
    "sitemap.txt",
    "sitemap.xml",
    "style.css",
}
ROOT_PUBLIC_PAGES = {
    "index.html",
    "about.html",
    "blog.html",
    "projects.html",
    "now.html",
    "links.html",
    "retratos-ufsc-florianopolis-imersivo.html",
}
PUBLIC_PAGE_DIRS = ("blog", "projects", "notes", "curriculo")
TEXT_SUFFIXES = {".css", ".html", ".js", ".json", ".md", ".txt", ".xml"}
ASSET_REFERENCE = re.compile(
    r"(?:(?:https?://bolivaralencastro\.com\.br)?/)?assets/[^\s\"'<>),]+",
    re.IGNORECASE,
)
INDEXNOW_KEY = re.compile(r"^[0-9a-f]{32}\.txt$")


class PublicBuildError(RuntimeError):
    """Raised when the public artifact cannot be assembled safely."""


def tracked_files(repo_root: Path) -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    return {item.decode("utf-8") for item in result.stdout.split(b"\0") if item}


def seed_files(repo_root: Path, tracked: set[str]) -> set[str]:
    seeds = {name for name in ROOT_PUBLIC_FILES | ROOT_PUBLIC_PAGES if name in tracked}
    seeds.update(
        path.with_suffix(".md").as_posix()
        for path in (repo_root / ".").glob("*.html")
        if path.name in ROOT_PUBLIC_PAGES and path.with_suffix(".md").as_posix() in tracked
    )
    for directory in PUBLIC_PAGE_DIRS:
        prefix = f"{directory}/"
        seeds.update(
            path for path in tracked
            if path.startswith(prefix) and Path(path).suffix.lower() in {".html", ".md"}
        )
    seeds.update(path for path in tracked if INDEXNOW_KEY.fullmatch(path))
    return seeds


def asset_references(path: Path) -> set[str]:
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return set()
    text = path.read_text(encoding="utf-8", errors="replace")
    references: set[str] = set()
    for match in ASSET_REFERENCE.finditer(text):
        raw = match.group(0)
        parsed = urlsplit(raw if "://" in raw else f"https://local.invalid/{raw.lstrip('/')}")
        rel = unquote(parsed.path).lstrip("/")
        if rel.startswith("assets/") and not rel.endswith("/"):
            references.add(rel)
    return references


def public_files(repo_root: Path, tracked: set[str] | None = None) -> set[str]:
    tracked = tracked if tracked is not None else tracked_files(repo_root)
    selected = seed_files(repo_root, tracked)
    pending = list(selected)

    while pending:
        rel = pending.pop()
        source = repo_root / rel
        if not source.is_file():
            raise PublicBuildError(f"Public file is missing: {rel}")
        for asset in asset_references(source):
            if asset not in tracked:
                raise PublicBuildError(f"Public reference is not tracked: {rel} -> {asset}")
            if asset not in selected:
                selected.add(asset)
                pending.append(asset)
    return selected


def prepare_output(repo_root: Path, output: Path) -> None:
    output = output.resolve()
    protected = {repo_root.resolve(), (repo_root / ".git").resolve(), (repo_root / ".local").resolve()}
    if output in protected or any(parent in protected - {repo_root.resolve()} for parent in output.parents):
        raise PublicBuildError(f"Refusing unsafe output path: {output}")
    if output.exists():
        if output != DEFAULT_OUTPUT.resolve():
            raise PublicBuildError(f"Output already exists and is not the managed _site directory: {output}")
        shutil.rmtree(output)
    output.mkdir(parents=True)


def build(repo_root: Path, output: Path) -> set[str]:
    selected = public_files(repo_root)
    prepare_output(repo_root, output)
    for rel in sorted(selected):
        source = repo_root / rel
        destination = output / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else REPO_ROOT / args.output
    try:
        selected = build(REPO_ROOT, output)
    except (OSError, subprocess.CalledProcessError, PublicBuildError) as exc:
        print(f"Public build failed: {exc}", file=sys.stderr)
        return 1
    size = sum((output / rel).stat().st_size for rel in selected)
    print(f"Public artifact: {len(selected)} files, {size / 1024 / 1024:.1f} MiB -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
