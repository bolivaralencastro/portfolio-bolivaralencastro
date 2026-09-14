#!/usr/bin/env python3
"""Create responsive WebP derivatives for editorial images already in use.

The metadata build advertises ``-720.webp`` and ``-960.webp`` siblings when
they exist. This utility intentionally discovers only images referenced by a
public HTML page, so unpublished material under ``assets/`` is never copied
into additional deployable files.
"""

from __future__ import annotations

import argparse
import pathlib
import re

from PIL import Image


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
IMAGE_SOURCE = re.compile(r'''<img\b[^>]*\bsrc=["'](/assets/images/blog/[^"']+\.webp)["']''', re.IGNORECASE)
DERIVATIVE = re.compile(r"-(?:720|960)\.webp$", re.IGNORECASE)
TARGET_WIDTHS = (720, 960)


def referenced_images() -> set[pathlib.Path]:
    images: set[pathlib.Path] = set()
    for page in REPO_ROOT.rglob("*.html"):
        if any(part in {".git", ".referencias"} for part in page.parts):
            continue
        for source in IMAGE_SOURCE.findall(page.read_text(encoding="utf-8")):
            image = REPO_ROOT / source.lstrip("/")
            if image.is_file() and not DERIVATIVE.search(image.name):
                images.add(image)
    return images


def create_derivative(source: pathlib.Path, width: int, quality: int, check: bool) -> bool:
    target = source.with_name(f"{source.stem}-{width}.webp")
    with Image.open(source) as image:
        source_width, source_height = image.size
        if source_width <= width:
            return False
        expected_height = round(source_height * width / source_width)
        if target.is_file():
            try:
                with Image.open(target) as existing:
                    if existing.size == (width, expected_height):
                        return False
            except OSError:
                # A partially written or otherwise invalid derivative must not
                # block the source image from being made responsive again.
                pass
        if check:
            print(f"Missing or outdated: {target.relative_to(REPO_ROOT)}")
            return True
        resized = image.convert("RGB").resize((width, expected_height), Image.Resampling.LANCZOS)
        resized.save(target, "WEBP", quality=quality, method=6)
        print(f"Created: {target.relative_to(REPO_ROOT)}")
        return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Report missing derivatives without writing files.")
    parser.add_argument("--quality", type=int, default=82, help="WebP quality (default: 82).")
    args = parser.parse_args()
    if not 1 <= args.quality <= 100:
        parser.error("--quality must be between 1 and 100")

    changed = 0
    for source in sorted(referenced_images()):
        for width in TARGET_WIDTHS:
            changed += create_derivative(source, width, args.quality, args.check)
    if args.check and changed:
        return 1
    print(f"{'Would update' if args.check else 'Updated'} {changed} responsive derivative(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
