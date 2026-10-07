#!/usr/bin/env python3
"""Canonical paths for files that must never be committed or deployed."""

from __future__ import annotations

import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _local_root() -> Path:
    configured = os.environ.get("PORTFOLIO_LOCAL_DIR", "").strip()
    if not configured:
        return REPO_ROOT / ".local"
    candidate = Path(configured).expanduser()
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


LOCAL_ROOT = _local_root().resolve()
ENV_FILE = LOCAL_ROOT / ".env"
DATA_ROOT = LOCAL_ROOT / "data"
STATE_ROOT = LOCAL_ROOT / "state"
DRAFTS_ROOT = LOCAL_ROOT / "drafts"
CURATION_ROOT = LOCAL_ROOT / "curadorias"
REFERENCES_ROOT = LOCAL_ROOT / "references"
YOUTUBE_RESEARCH_ROOT = LOCAL_ROOT / "youtube-research" / "videos"
SOCIAL_ASSETS_ROOT = LOCAL_ROOT / "assets-source" / "social"
CREDENTIALS_ROOT = LOCAL_ROOT / "credentials"


def local_path(*parts: str) -> Path:
    """Return a path below the private workspace root."""
    return LOCAL_ROOT.joinpath(*parts)
