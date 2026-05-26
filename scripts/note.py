#!/usr/bin/env python3
"""Create, build, validate, commit, and push notes."""

from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import subprocess
import sys
import tempfile
from dataclasses import dataclass

from notes_pipeline import NOTE_SOURCE_DIR, NoteError, parse_note_file, slugify

DEFAULT_PUBLISH_BRANCH = "main"


class PublishError(RuntimeError):
    """Raised when note publication cannot continue safely."""


@dataclass
class CommandResult:
    stdout: str


def run(
    args: list[str],
    *,
    repo_root: pathlib.Path,
    capture: bool = False,
    check: bool = True,
) -> CommandResult:
    result = subprocess.run(
        args,
        cwd=repo_root,
        check=False,
        capture_output=capture,
        text=True,
    )
    if check and result.returncode != 0:
        stderr = result.stderr.strip() if capture else ""
        stdout = result.stdout.strip() if capture else ""
        details = stderr or stdout or f"command failed: {' '.join(args)}"
        raise PublishError(details)
    return CommandResult(stdout=result.stdout if capture else "")


def repo_root_from_script() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent.parent


def read_body(args: argparse.Namespace) -> str:
    if args.body and args.body_file:
        raise PublishError("use either --body or --body-file, not both")
    if args.body_file:
        return pathlib.Path(args.body_file).read_text(encoding="utf-8").strip()
    if args.body:
        return args.body.strip()
    raise PublishError("missing note body; provide --body or --body-file")


def write_note_file(args: argparse.Namespace, repo_root: pathlib.Path) -> pathlib.Path:
    date_value = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
    slug = slugify(args.slug or args.title)
    if not slug:
        raise PublishError("could not derive slug from title; use --slug")

    notes_dir = repo_root / NOTE_SOURCE_DIR
    notes_dir.mkdir(parents=True, exist_ok=True)
    note_path = notes_dir / f"{date_value.isoformat()}-{slug}.md"
    if note_path.exists():
        raise PublishError(f"note already exists: {note_path.relative_to(repo_root).as_posix()}")

    fields = [
        "---",
        f"title: {args.title}",
        f"date: {date_value.isoformat()}",
        f"category: {args.category}",
    ]
    if args.classes:
        fields.append(f"classes: {args.classes}")
    fields.append(f"status: {args.status}")
    fields.append("---")
    fields.append("")
    fields.append(read_body(args))
    fields.append("")
    note_path.write_text("\n".join(fields), encoding="utf-8", newline="\n")
    return note_path


def resolve_note_path(raw_path: str, repo_root: pathlib.Path) -> pathlib.Path:
    path = pathlib.Path(raw_path)
    if not path.is_absolute():
        path = repo_root / path
    path = path.resolve()
    if not path.exists():
        raise PublishError(f"note file not found: {raw_path}")
    return path


def git_dirty_paths(repo_root: pathlib.Path) -> list[str]:
    status = run(
        ["git", "status", "--short", "--untracked-files=all"],
        repo_root=repo_root,
        capture=True,
    ).stdout
    paths: list[str] = []
    for line in status.splitlines():
        if not line.strip():
            continue
        candidate = line[3:]
        if " -> " in candidate:
            candidate = candidate.split(" -> ", 1)[1]
        paths.append(candidate.strip())
    return paths


def ensure_note_scope_isolated(
    note_rel: str,
    include_paths: list[str],
    repo_root: pathlib.Path,
) -> None:
    allowed = {note_rel, "now.html", "sitemap.xml", "sitemap.txt", "feed.xml", "feed.txt", *include_paths}
    allowed_prefixes = ("notes/",)
    note_scope_dirty: list[str] = []
    for rel_path in git_dirty_paths(repo_root):
        if rel_path in allowed or any(rel_path.startswith(prefix) for prefix in allowed_prefixes):
            continue
        if rel_path.startswith("content/notes/") or rel_path.startswith("notes/") or rel_path in {
            "now.html",
            "sitemap.xml",
            "sitemap.txt",
            "feed.xml",
            "feed.txt",
        }:
            note_scope_dirty.append(rel_path)
    if note_scope_dirty:
        raise PublishError(
            "note publish aborted because other note-related changes are pending: "
            + ", ".join(note_scope_dirty)
        )


def build_and_validate(repo_root: pathlib.Path) -> None:
    run(["python3", "scripts/build_site_metadata.py"], repo_root=repo_root)
    run(["python3", "scripts/validate_site.py"], repo_root=repo_root)


def prepare_temp_publish_repo(repo_root: pathlib.Path, publish_branch: str) -> tuple[tempfile.TemporaryDirectory[str], pathlib.Path]:
    temp_dir = tempfile.TemporaryDirectory(prefix="portfolio-note-publish-")
    worktree_path = pathlib.Path(temp_dir.name)

    run(["git", "fetch", "origin", publish_branch], repo_root=repo_root)
    run(
        ["git", "worktree", "add", "--detach", str(worktree_path), f"origin/{publish_branch}"],
        repo_root=repo_root,
    )
    return temp_dir, worktree_path


def cleanup_temp_publish_repo(repo_root: pathlib.Path, temp_dir: tempfile.TemporaryDirectory[str], worktree_path: pathlib.Path) -> None:
    try:
        run(["git", "worktree", "remove", "--force", str(worktree_path)], repo_root=repo_root, check=False)
    finally:
        temp_dir.cleanup()


def write_note_file_in_repo(
    repo_root: pathlib.Path,
    *,
    title: str,
    body: str,
    date_value: dt.date,
    category: str,
    classes: str,
    status: str,
    slug_value: str | None,
) -> pathlib.Path:
    slug = slugify(slug_value or title)
    if not slug:
        raise PublishError("could not derive slug from title; use --slug")

    notes_dir = repo_root / NOTE_SOURCE_DIR
    notes_dir.mkdir(parents=True, exist_ok=True)
    note_path = notes_dir / f"{date_value.isoformat()}-{slug}.md"
    if note_path.exists():
        raise PublishError(f"note already exists: {note_path.relative_to(repo_root).as_posix()}")

    fields = [
        "---",
        f"title: {title}",
        f"date: {date_value.isoformat()}",
        f"category: {category}",
    ]
    if classes:
        fields.append(f"classes: {classes}")
    fields.append(f"status: {status}")
    fields.append("---")
    fields.append("")
    fields.append(body)
    fields.append("")
    note_path.write_text("\n".join(fields), encoding="utf-8", newline="\n")
    return note_path


def stage_commit_push(
    note_path: pathlib.Path,
    *,
    include: list[str],
    repo_root: pathlib.Path,
    no_push: bool,
    message: str | None,
) -> None:
    note_rel = note_path.relative_to(repo_root).as_posix()
    include_rels = [resolve_include_path(item, repo_root) for item in include]
    ensure_note_scope_isolated(note_rel, include_rels, repo_root)

    stage_paths = [note_rel, "now.html", "notes", "sitemap.xml", "sitemap.txt", "feed.xml", "feed.txt", *include_rels]
    run(["git", "add", "--", *stage_paths], repo_root=repo_root)

    diff_result = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--", *stage_paths],
        cwd=repo_root,
        check=False,
    )
    if diff_result.returncode == 0:
        raise PublishError("no staged note changes to commit")

    note = parse_note_file(note_path, repo_root)
    commit_message = message or f"Add note: {note.title or note.slug}"
    run(["git", "commit", "-m", commit_message], repo_root=repo_root)

    if not no_push:
        run(["git", "push", "origin", current_branch(repo_root)], repo_root=repo_root)


def stage_commit_push_to_branch(
    note_path: pathlib.Path,
    *,
    repo_root: pathlib.Path,
    publish_branch: str,
    message: str | None,
) -> None:
    note_rel = note_path.relative_to(repo_root).as_posix()
    stage_paths = [note_rel, "now.html", "notes", "sitemap.xml", "sitemap.txt", "feed.xml", "feed.txt"]
    run(["git", "add", "--", *stage_paths], repo_root=repo_root)

    diff_result = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--", *stage_paths],
        cwd=repo_root,
        check=False,
    )
    if diff_result.returncode == 0:
        raise PublishError("no staged note changes to commit")

    note = parse_note_file(note_path, repo_root)
    commit_message = message or f"Add note: {note.title or note.slug}"
    run(["git", "commit", "-m", commit_message], repo_root=repo_root)
    run(["git", "push", "origin", f"HEAD:{publish_branch}"], repo_root=repo_root)


def resolve_include_path(raw_path: str, repo_root: pathlib.Path) -> str:
    path = pathlib.Path(raw_path)
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    if not path.exists():
        raise PublishError(f"include path not found: {raw_path}")
    return path.relative_to(repo_root).as_posix()


def current_branch(repo_root: pathlib.Path) -> str:
    branch = run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        repo_root=repo_root,
        capture=True,
    ).stdout.strip()
    if not branch or branch == "HEAD":
        raise PublishError("cannot push from detached HEAD")
    return branch


def direct_publish_note(args: argparse.Namespace, repo_root: pathlib.Path) -> str:
    if args.include:
        raise PublishError("--include is not supported with --direct-main yet")
    if args.no_push:
        raise PublishError("--no-push cannot be used with --direct-main")
    if args.no_publish:
        raise PublishError("--no-publish cannot be used with --direct-main")

    date_value = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
    body = read_body(args)
    temp_dir, temp_repo_root = prepare_temp_publish_repo(repo_root, DEFAULT_PUBLISH_BRANCH)
    try:
        note_path = write_note_file_in_repo(
            temp_repo_root,
            title=args.title,
            body=body,
            date_value=date_value,
            category=args.category,
            classes=args.classes,
            status=args.status,
            slug_value=args.slug,
        )
        build_and_validate(temp_repo_root)
        stage_commit_push_to_branch(
            note_path,
            repo_root=temp_repo_root,
            publish_branch=DEFAULT_PUBLISH_BRANCH,
            message=args.message,
        )
        return note_path.relative_to(temp_repo_root).as_posix()
    finally:
        cleanup_temp_publish_repo(repo_root, temp_dir, temp_repo_root)


def command_new(args: argparse.Namespace, repo_root: pathlib.Path) -> int:
    if args.direct_main:
        note_rel = direct_publish_note(args, repo_root)
        print(f"Published directly to {DEFAULT_PUBLISH_BRANCH}: {note_rel}")
        return 0

    note_path = write_note_file(args, repo_root)
    if args.no_publish:
        print(f"Created {note_path.relative_to(repo_root).as_posix()}")
        return 0

    build_and_validate(repo_root)
    stage_commit_push(
        note_path,
        include=args.include,
        repo_root=repo_root,
        no_push=args.no_push,
        message=args.message,
    )
    print(f"Published {note_path.relative_to(repo_root).as_posix()}")
    return 0


def command_publish(args: argparse.Namespace, repo_root: pathlib.Path) -> int:
    note_path = resolve_note_path(args.note_path, repo_root)
    build_and_validate(repo_root)
    stage_commit_push(
        note_path,
        include=args.include,
        repo_root=repo_root,
        no_push=args.no_push,
        message=args.message,
    )
    print(f"Published {note_path.relative_to(repo_root).as_posix()}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create and publish notes for the portfolio")
    subparsers = parser.add_subparsers(dest="command", required=True)

    new_parser = subparsers.add_parser("new", help="create a new note")
    new_parser.add_argument("title", help="note title")
    new_parser.add_argument("--body", help="note body")
    new_parser.add_argument("--body-file", help="path to a file containing the note body")
    new_parser.add_argument("--date", help="publish date in YYYY-MM-DD format")
    new_parser.add_argument("--category", default="Ideia em aberto", help="visible note category")
    new_parser.add_argument("--classes", default="note-seed", help="space-separated extra note classes")
    new_parser.add_argument("--status", default="published", choices=["published", "draft"])
    new_parser.add_argument("--slug", help="optional custom slug")
    new_parser.add_argument("--include", action="append", default=[], help="extra paths to stage with the note")
    new_parser.add_argument("--message", help="custom git commit message")
    new_parser.add_argument(
        "--direct-main",
        action="store_true",
        help="publish from an isolated temporary worktree directly to origin/main",
    )
    new_parser.add_argument("--no-publish", action="store_true", help="create the note source without git commit/push")
    new_parser.add_argument("--no-push", action="store_true", help="commit locally but skip git push")
    new_parser.set_defaults(func=command_new)

    publish_parser = subparsers.add_parser("publish", help="build, validate, commit, and push an existing note")
    publish_parser.add_argument("note_path", help="path to the note markdown file")
    publish_parser.add_argument("--include", action="append", default=[], help="extra paths to stage with the note")
    publish_parser.add_argument("--message", help="custom git commit message")
    publish_parser.add_argument("--no-push", action="store_true", help="commit locally but skip git push")
    publish_parser.set_defaults(func=command_publish)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    repo_root = repo_root_from_script()
    return args.func(args, repo_root)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PublishError, NoteError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
