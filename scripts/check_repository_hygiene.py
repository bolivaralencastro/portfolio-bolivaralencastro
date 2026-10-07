#!/usr/bin/env python3
"""Reject tracked local-only files and high-confidence secret material."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from build_public_site import public_files


REPO_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PREFIXES = (
    ".local/",
    ".social_publish_state/",
    ".local/assets-source/social/",
    "curadorias/",
    "data/",
    "ideias-blogposts/",
    "youtube-research/videos/",
)
ALLOWED_SENSITIVE_NAMES = {
    ".env.example",
    "scripts/check_repository_hygiene.py",
    "scripts/export_instagram_cookies.py",
    "scripts/refresh_meta_tokens.py",
}
SENSITIVE_PATH = re.compile(
    r"(^|/)(\.env(?:\..+)?|.*(?:cookie|credential|private[-_]?key|secret|session|token).*)$|"
    r"\.(?:key|p12|pem|pfx|pyc|sqlite)$",
    re.IGNORECASE,
)
SECRET_CONTENT = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\b(?:ghp|gho|ghu|ghs|github_pat)_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{16,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"(?m)^\.?[^\t\n]+\t(?:TRUE|FALSE)\t/\t(?:TRUE|FALSE)\t\d+\t(?:sessionid|csrftoken)\t\S+"),
)
ENV_SECRET = re.compile(
    r"(?m)^(?:export\s+)?[A-Z0-9_]*(?:API_KEY|API_SECRET|ACCESS_TOKEN|CLIENT_SECRET|PASSWORD|PRIVATE_KEY)\s*=\s*(.+)$"
)
TEXT_SUFFIXES = {"", ".cjs", ".css", ".html", ".js", ".json", ".md", ".py", ".sh", ".toml", ".txt", ".xml", ".yaml", ".yml"}


def tracked_files(repo_root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=repo_root, check=True, capture_output=True
    )
    return [item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def is_placeholder(value: str) -> bool:
    value = value.strip().strip("\"'")
    return not value or value.startswith(("<", "${", "$", "SEU_", "SUA_")) or value.lower() in {
        "changeme", "example", "placeholder", "none",
    }


def findings(repo_root: Path, tracked: list[str] | None = None) -> list[str]:
    problems: list[str] = []
    supplied_tracking = tracked is not None
    tracked = tracked if tracked is not None else tracked_files(repo_root)
    for rel in tracked:
        if rel in ALLOWED_SENSITIVE_NAMES:
            continue
        if rel.startswith(FORBIDDEN_PREFIXES):
            problems.append(f"{rel}: local-only path is tracked")
            continue
        if "__pycache__" in Path(rel).parts or SENSITIVE_PATH.search(rel):
            problems.append(f"{rel}: sensitive or generated filename is tracked")
            continue
        path = repo_root / rel
        if path.suffix.lower() not in TEXT_SUFFIXES or not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if rel.startswith("content/notes/") and re.search(r"(?mi)^status:\s*draft\s*$", text):
            problems.append(f"{rel}: draft notes must stay under .local/drafts/notes")
            continue
        if any(pattern.search(text) for pattern in SECRET_CONTENT):
            problems.append(f"{rel}: high-confidence secret pattern found")
            continue
        if any(not is_placeholder(match.group(1)) for match in ENV_SECRET.finditer(text)):
            problems.append(f"{rel}: non-placeholder secret assignment found")
    if not supplied_tracking:
        published = public_files(repo_root, set(tracked))
        for rel in tracked:
            if rel.startswith("assets/") and rel not in published:
                problems.append(f"{rel}: tracked asset is not referenced by the public site")
    return problems


def main() -> int:
    try:
        problems = findings(REPO_ROOT)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"Repository hygiene check failed to run: {exc}", file=sys.stderr)
        return 1
    if problems:
        print("Repository hygiene errors:")
        for problem in problems:
            print(f" - {problem}")
        return 1
    print("Repository hygiene passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
