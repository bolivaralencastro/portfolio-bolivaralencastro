#!/usr/bin/env python3
"""Notify IndexNow (Bing, Yandex, Seznam, Naver...) about pages changed in a commit range.

Run it AFTER the push has been deployed: the search engines fetch the key file
(<key>.txt at the site root) to confirm ownership. Without --send it only prints
what would be submitted.

    python3 scripts/indexnow_submit.py                 # dry run, last commit
    python3 scripts/indexnow_submit.py --send          # submit URLs changed in HEAD~1..HEAD
    python3 scripts/indexnow_submit.py --range origin/main~3..origin/main --send
    python3 scripts/indexnow_submit.py --all --send    # every URL in sitemap.xml
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.request

BASE_URL = "https://bolivaralencastro.com.br"
ENDPOINT = "https://api.indexnow.org/IndexNow"
MAX_URLS = 10000  # IndexNow limit per request
KEY_FILE_PATTERN = re.compile(r"^[0-9a-f]{32}\.txt$")


def tls_context() -> ssl.SSLContext:
    """Verified TLS context. python.org builds on macOS ship without CA roots, so fall back to the system bundle."""
    context = ssl.create_default_context()
    if context.cert_store_stats().get("x509_ca"):
        return context
    for cafile in ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt"):
        if pathlib.Path(cafile).is_file():
            return ssl.create_default_context(cafile=cafile)
    return context


def find_key(repo_root: pathlib.Path) -> str:
    candidates = [p for p in repo_root.iterdir() if p.is_file() and KEY_FILE_PATTERN.match(p.name)]
    if len(candidates) != 1:
        sys.exit(f"Expected exactly one IndexNow key file (<32 hex>.txt) at the repo root, found {len(candidates)}")
    key = candidates[0].read_text(encoding="utf-8").strip()
    if key != candidates[0].stem:
        sys.exit(f"{candidates[0].name}: file content must equal the key in its name")
    return key


def sitemap_urls(repo_root: pathlib.Path) -> list[str]:
    content = (repo_root / "sitemap.xml").read_text(encoding="utf-8")
    return re.findall(r"<loc>([^<]+)</loc>", content)


def url_to_rel(url: str) -> str:
    rel = url.removeprefix(BASE_URL).lstrip("/")
    return rel + "index.html" if not rel or rel.endswith("/") else rel


def changed_files(repo_root: pathlib.Path, revision_range: str) -> set[str]:
    out = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=AM", revision_range],
        cwd=repo_root, capture_output=True, text=True, check=True,
    ).stdout
    return set(out.split())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--range", default="HEAD~1..HEAD", help="git revision range with the published changes")
    parser.add_argument("--all", action="store_true", help="submit every URL in sitemap.xml")
    parser.add_argument("--send", action="store_true", help="actually call the IndexNow API (default: dry run)")
    args = parser.parse_args()

    repo_root = pathlib.Path(__file__).resolve().parent.parent
    key = find_key(repo_root)
    urls = sitemap_urls(repo_root)
    if not args.all:
        changed = changed_files(repo_root, args.range)
        urls = [url for url in urls if url_to_rel(url) in changed]
    urls = urls[:MAX_URLS]

    if not urls:
        print("No indexable pages changed; nothing to submit.")
        return 0
    print(f"{len(urls)} URL(s):")
    for url in urls:
        print(f"  {url}")
    if not args.send:
        print("Dry run: pass --send to submit.")
        return 0

    payload = json.dumps(
        {"host": BASE_URL.removeprefix("https://"), "key": key, "keyLocation": f"{BASE_URL}/{key}.txt", "urlList": urls}
    ).encode("utf-8")
    request = urllib.request.Request(
        ENDPOINT, data=payload, headers={"Content-Type": "application/json; charset=utf-8"}, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=30, context=tls_context()) as response:
            print(f"IndexNow responded HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        print(f"IndexNow rejected the submission: HTTP {exc.code} {exc.reason}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Could not reach IndexNow: {exc.reason}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
