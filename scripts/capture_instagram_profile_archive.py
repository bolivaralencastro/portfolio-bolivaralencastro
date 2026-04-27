#!/usr/bin/env /usr/local/bin/python3
"""Capture all photos and tagged people from a public Instagram profile.

This script uses an authenticated Chrome session exposed via DevTools Protocol.
It fetches the full profile feed through in-page requests, downloads every image
from every post, and writes a local archive manifest.

Usage:
    /usr/local/bin/python3 scripts/capture_instagram_profile_archive.py boli.alen
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import ssl
import sys
import urllib.parse
import urllib.request
from pathlib import Path

try:
    import certifi

    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except Exception:
    SSL_CONTEXT = ssl.create_default_context()

try:
    from PIL import Image
except Exception as exc:  # pragma: no cover - environment dependency
    raise SystemExit(f"Pillow is required: {exc}")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.social_capture_browser import CDP  # noqa: E402


def get_instagram_page_ws(username: str, port: int) -> str:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as response:
        pages = json.loads(response.read())

    profile_url = f"https://www.instagram.com/{username}/"
    fallback = None
    for page in pages:
        if page.get("type") != "page":
            continue
        url = page.get("url") or ""
        ws = page.get("webSocketDebuggerUrl")
        if not ws:
            continue
        if url.startswith(profile_url):
            return ws
        if "instagram.com" in url and fallback is None:
            fallback = ws

    if fallback:
        return fallback

    raise RuntimeError(
        "No Instagram Chrome tab found. Open Chrome with --remote-debugging-port=9333, "
        f"log in to Instagram, and open https://www.instagram.com/{username}/"
    )


def fetch_profile_feed(cdp: CDP, username: str, max_pages: int) -> dict:
    expression = f"""
    (async () => {{
      const headers = {{'x-ig-app-id': '936619743392459'}};
      const profileResp = await fetch(
        'https://www.instagram.com/api/v1/users/web_profile_info/?username={username}',
        {{ credentials: 'include', headers }}
      );
      const profile = await profileResp.json();
      const user = profile?.data?.user || null;
      const userId = user?.id || null;
      const pages = [];
      let nextMax = null;
      for (let page = 0; page < {max_pages}; page++) {{
        let url = `https://i.instagram.com/api/v1/feed/user/${{userId}}/?count=24`;
        if (nextMax) url += `&max_id=${{encodeURIComponent(nextMax)}}`;
        const resp = await fetch(url, {{ credentials: 'include', headers }});
        const data = await resp.json();
        pages.push({{
          page,
          status: resp.status,
          items: data.items || [],
          next_max_id: data.next_max_id || null
        }});
        if (!data.next_max_id) break;
        nextMax = data.next_max_id;
      }}
      return {{
        fetchedAt: new Date().toISOString(),
        user: user ? {{
          id: user.id,
          username: user.username,
          full_name: user.full_name,
          biography: user.biography,
          edge_followed_by: user.edge_followed_by?.count || 0,
          edge_follow: user.edge_follow?.count || 0,
          posts_count: user.edge_owner_to_timeline_media?.count || 0,
        }} : null,
        pages,
      }};
    }})()
    """
    return cdp.evaluate(expression, timeout_ms=240000)


def best_image_url(media: dict) -> str | None:
    candidates = media.get("image_versions2", {}).get("candidates", [])
    if not candidates:
        return None
    best = max(candidates, key=lambda item: (item.get("width", 0) * item.get("height", 0), item.get("width", 0)))
    return best.get("url")


def gather_post_records(feed_payload: dict) -> list[dict]:
    posts: list[dict] = []
    seen_codes: set[str] = set()

    for page in feed_payload.get("pages", []):
        for item in page.get("items", []):
            code = item.get("code") or item.get("media_code") or str(item.get("pk") or "")
            if not code or code in seen_codes:
                continue
            seen_codes.add(code)

            tagged_users: set[str] = set()
            image_entries: list[dict] = []

            def harvest(media: dict, image_index: int, carousel_index: int | None = None) -> int:
                image_url = best_image_url(media)
                if image_url:
                    image_entries.append(
                        {
                            "index": image_index,
                            "carousel_index": carousel_index,
                            "source_url": image_url,
                        }
                    )
                    image_index += 1

                for tag in media.get("usertags", {}).get("in", []):
                    username = tag.get("user", {}).get("username")
                    if username:
                        tagged_users.add(username)
                for tag in media.get("sponsor_tags", {}).get("in", []):
                    username = tag.get("user", {}).get("username")
                    if username:
                        tagged_users.add(username)
                return image_index

            next_index = 1
            next_index = harvest(item, next_index)
            for child_idx, child in enumerate(item.get("carousel_media", []) or [], start=1):
                next_index = harvest(child, next_index, carousel_index=child_idx)

            caption = ""
            caption_text = item.get("caption") or {}
            if isinstance(caption_text, dict):
                caption = caption_text.get("text") or ""

            posts.append(
                {
                    "code": code,
                    "pk": str(item.get("pk") or ""),
                    "post_url": f"https://www.instagram.com/p/{code}/",
                    "taken_at": item.get("taken_at"),
                    "caption": caption,
                    "tagged_users": sorted(tagged_users),
                    "image_count": len(image_entries),
                    "images": image_entries,
                }
            )

    return posts


def guess_extension(url: str) -> str:
    path = urllib.parse.urlparse(url).path.lower()
    if path.endswith(".png"):
        return ".png"
    if path.endswith(".webp"):
        return ".webp"
    return ".jpg"


def download_binary(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"user-agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=60, context=SSL_CONTEXT) as response:
        destination.write_bytes(response.read())


def image_size(path: Path) -> tuple[int | None, int | None]:
    try:
        with Image.open(path) as img:
            return img.size
    except Exception:
        return None, None


def write_archive(username: str, payload: dict, posts: list[dict], output_root: Path) -> Path:
    archive_root = output_root / username
    images_root = archive_root / "images"
    images_root.mkdir(parents=True, exist_ok=True)

    tagged_index: dict[str, list[str]] = {}

    for post_idx, post in enumerate(posts, start=1):
        post_dir = images_root / post["code"]
        post_dir.mkdir(parents=True, exist_ok=True)

        for username_tag in post["tagged_users"]:
            tagged_index.setdefault(username_tag, []).append(post["code"])

        for image in post["images"]:
            extension = guess_extension(image["source_url"])
            file_name = f"{post_idx:03d}_{post['code']}_{image['index']:02d}{extension}"
            local_path = post_dir / file_name
            if not local_path.exists():
                download_binary(image["source_url"], local_path)
            width, height = image_size(local_path)
            image["local_path"] = local_path.relative_to(ROOT).as_posix()
            image["width"] = width
            image["height"] = height

    manifest = {
        "fetched_at": payload.get("fetchedAt") or dt.datetime.now(dt.timezone.utc).isoformat(),
        "profile": payload.get("user") or {},
        "total_posts_captured": len(posts),
        "total_images_captured": sum(post["image_count"] for post in posts),
        "unique_tagged_people": sorted(tagged_index),
        "posts": posts,
    }

    manifest_path = archive_root / "manifest.json"
    tagged_index_path = archive_root / "tagged_people.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    tagged_index_path.write_text(json.dumps(tagged_index, ensure_ascii=False, indent=2), encoding="utf-8")
    return archive_root


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture an Instagram profile archive via authenticated Chrome session")
    parser.add_argument("username", help="Instagram username, without @")
    parser.add_argument("--port", type=int, default=9333, help="Chrome remote debugging port")
    parser.add_argument(
        "--output-root",
        default=str(ROOT / "data" / "instagram_profile_archives"),
        help="Directory where manifest and images will be stored",
    )
    parser.add_argument("--max-pages", type=int, default=10, help="Safety cap for paginated feed requests")
    args = parser.parse_args()

    ws_url = get_instagram_page_ws(args.username, args.port)
    cdp = CDP(ws_url)
    cdp.call("Page.enable")
    cdp.call("Runtime.enable")

    feed_payload = fetch_profile_feed(cdp, args.username, args.max_pages)
    posts = gather_post_records(feed_payload)
    archive_root = write_archive(args.username, feed_payload, posts, Path(args.output_root))

    unique_tagged = sorted({name for post in posts for name in post["tagged_users"]})
    print(f"Archive saved to: {archive_root}")
    print(f"Posts captured: {len(posts)}")
    print(f"Images captured: {sum(post['image_count'] for post in posts)}")
    print(f"Unique tagged people: {len(unique_tagged)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())