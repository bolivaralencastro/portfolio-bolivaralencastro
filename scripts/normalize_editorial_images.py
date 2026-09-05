#!/usr/bin/env python3
"""Audit/normalize referenced editorial images; Pillow is needed only for --write.

Preserves composition, backs up replaced originals outside assets/, and prints
social URL mappings for review. HTML references must be updated separately.
"""

import argparse
import json
from pathlib import Path
import shutil

from image_metadata import image_metadata
from validate_site import iter_public_pages, parse_page, local_asset_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Optimize assets and create JPEG social variants")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    pages = [parse_page(path, root) for path in iter_public_pages(root)]
    images = set()
    social = set()
    for page in pages:
        for image in page.images:
            if image.src:
                target = local_asset_path(root, page, image.src)
                if target and target.is_file() and target.suffix.lower() != ".svg":
                    images.add(target)
        for reference in filter(None, (page.og_image, page.twitter_image)):
            target = local_asset_path(root, page, reference)
            if target and target.is_file():
                social.add(target)
    oversized = sorted(path for path in images if path.stat().st_size >= 500_000 or image_metadata(path)[1] >= 2000)
    mappings = {}
    for path in sorted(social):
        if image_metadata(path) == ("JPEG", 1200, 630) and path.stat().st_size < 300_000:
            continue
        name = "og.jpg" if path.stem == "og" and path.suffix.lower() != ".jpg" else path.stem + "-og.jpg"
        target = path.with_name(name)
        if target.exists() and (image_metadata(target) != ("JPEG", 1200, 630) or target.stat().st_size >= 300_000):
            raise RuntimeError(f"Refusing to overwrite existing social variant: {target}")
        mappings[path] = target
    if args.write:
        from PIL import Image, ImageOps
        from blog_image_workflow import open_rgb_image, save_image

        for path, target in mappings.items():
            if target.exists():
                continue
            image = ImageOps.pad(open_rgb_image(path), (1200, 630), method=Image.Resampling.LANCZOS, color="white")
            for quality in range(90, 39, -5):
                save_image(image, target, quality)
                if target.stat().st_size < 300_000:
                    break
            if target.stat().st_size >= 300_000:
                raise RuntimeError(f"Could not meet social image budget: {target}")
        for path in oversized:
            backup = root / ".referencias" / "asset-normalization" / path.relative_to(root)
            if not backup.exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, backup)
            image = open_rgb_image(backup)
            if image.width >= 2000:
                image = image.resize((1920, round(image.height * 1920 / image.width)), Image.Resampling.LANCZOS)
            for attempt in range(10):
                for quality in range(90, 59, -5):
                    save_image(image, path, quality)
                    if path.stat().st_size < 500_000:
                        break
                if path.stat().st_size < 500_000:
                    break
                image = image.resize((round(image.width * 0.85), round(image.height * 0.85)), Image.Resampling.LANCZOS)
            if path.stat().st_size >= 500_000:
                raise RuntimeError(f"Could not meet editorial image budget: {path}")
    print(json.dumps({
        "optimized": [str(path.relative_to(root)) for path in oversized],
        "social": {"/" + str(path.relative_to(root)): "/" + str(target.relative_to(root)) for path, target in mappings.items()},
        "written": args.write,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
