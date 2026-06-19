#!/usr/bin/env python3
"""Export Microsoft Clarity dashboard data using the local .env token."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import subprocess
import sys
import urllib.parse


ROOT = pathlib.Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
OUT_DIR = ROOT / "data" / "analytics" / "clarity"
API_URL = "https://www.clarity.ms/export-data/api/v1/project-live-insights"
TOKEN_KEY = "CLARITY_DATA_EXPORT_TOKEN"
ALLOWED_DAYS = {"1", "2", "3"}


def load_env_value(key: str) -> str:
    if not ENV_PATH.exists():
        return ""

    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() == key:
            return value.strip().strip("\"'")
    return ""


def fetch_clarity(token: str, days: str, dimensions: list[str]) -> list[dict]:
    params = {"numOfDays": days}
    for index, dimension in enumerate(dimensions, start=1):
        params[f"dimension{index}"] = dimension

    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    result = subprocess.run(
        [
            "curl",
            "-sS",
            "--location",
            url,
            "--header",
            "Content-Type: application/json",
            "--header",
            f"Authorization: Bearer {token}",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout or "[]")
    if isinstance(payload, dict) and "error" in payload:
        raise RuntimeError(json.dumps(payload, ensure_ascii=False))
    if not isinstance(payload, list):
        raise RuntimeError(f"Unexpected Clarity response: {payload!r}")
    return payload


def output_path(days: str, dimensions: list[str]) -> pathlib.Path:
    date_slug = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    dim_slug = "-".join(d.lower().replace("/", "-") for d in dimensions) or "summary"
    return OUT_DIR / f"{date_slug}_{days}d_{dim_slug}.json"


def summarize(payload: list[dict]) -> str:
    lines = []
    for metric in payload:
        name = metric.get("metricName", "Unknown")
        rows = metric.get("information", [])
        lines.append(f"{name}: {len(rows)} row(s)")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Microsoft Clarity dashboard data")
    parser.add_argument("--days", default="1", choices=sorted(ALLOWED_DAYS), help="Lookback window: 1, 2, or 3 days")
    parser.add_argument(
        "--dimension",
        action="append",
        default=[],
        help="Clarity dimension. Can be passed up to 3 times, for example URL, Source, Device.",
    )
    parser.add_argument("--stdout", action="store_true", help="Print raw JSON instead of saving a file")
    args = parser.parse_args()

    dimensions = args.dimension[:3]
    token = load_env_value(TOKEN_KEY)
    if not token:
        sys.exit(f"Missing {TOKEN_KEY} in {ENV_PATH}")

    payload = fetch_clarity(token, args.days, dimensions)
    if args.stdout:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = output_path(args.days, dimensions)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(path.relative_to(ROOT).as_posix())
    print(summarize(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
