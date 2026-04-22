#!/usr/bin/env python3
"""Compose blog image triptychs and convert assets to WebP.

This script is intentionally narrow:
- compose exactly three images side by side
- preserve the full image content
- normalize EXIF orientation
- resize to a common height to avoid white bars
- convert images to WebP for blog usage
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image, ImageOps


VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def open_rgb_image(path: Path) -> Image.Image:
    with Image.open(path) as image:
        normalized = ImageOps.exif_transpose(image)
        return normalized.convert("RGB")


def resize_to_height(image: Image.Image, target_height: int) -> Image.Image:
    if image.height == target_height:
        return image.copy()
    width = round(image.width * (target_height / image.height))
    return image.resize((width, target_height), Image.Resampling.LANCZOS)


def save_image(image: Image.Image, output_path: Path, quality: int) -> None:
    ensure_parent(output_path)
    suffix = output_path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        image.save(output_path, format="JPEG", quality=quality, optimize=True)
        return
    if suffix == ".png":
        image.save(output_path, format="PNG", optimize=True)
        return
    if suffix == ".webp":
        image.save(output_path, format="WEBP", quality=quality, method=6)
        return
    raise ValueError(f"Unsupported output format: {output_path.suffix}")


def compose_triptych(
    inputs: Sequence[Path],
    output_path: Path,
    *,
    target_height: int | None,
    quality: int,
) -> Path:
    if len(inputs) != 3:
        raise ValueError("Triptych composition requires exactly three input images.")

    images = [open_rgb_image(path) for path in inputs]
    resolved_height = target_height or max(image.height for image in images)
    resized = [resize_to_height(image, resolved_height) for image in images]

    total_width = sum(image.width for image in resized)
    canvas = Image.new("RGB", (total_width, resolved_height), "white")

    offset_x = 0
    for image in resized:
        canvas.paste(image, (offset_x, 0))
        offset_x += image.width

    save_image(canvas, output_path, quality)
    return output_path


def convert_to_webp(
    input_path: Path,
    *,
    output_path: Path | None,
    max_width: int | None,
    quality: int,
    delete_source: bool,
) -> Path:
    image = open_rgb_image(input_path)

    if max_width and image.width > max_width:
        new_height = round(image.height * (max_width / image.width))
        image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)

    resolved_output = output_path or input_path.with_suffix(".webp")
    save_image(image, resolved_output, quality)

    if delete_source and input_path != resolved_output and input_path.exists():
        input_path.unlink()

    return resolved_output


def iter_source_images(directory: Path) -> Iterable[Path]:
    for path in sorted(directory.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in VALID_EXTENSIONS:
            continue
        yield path


def batch_triptychs(
    directory: Path,
    *,
    output_prefix: str,
    output_format: str,
    quality: int,
    target_height: int | None,
    start_index: int,
    delete_sources: bool,
) -> list[Path]:
    source_images = list(iter_source_images(directory))
    if len(source_images) < 3:
        raise ValueError("Need at least three source images to build triptychs.")

    remainder = len(source_images) % 3
    if remainder:
        raise ValueError(
            f"Found {len(source_images)} source images in {directory}; "
            "the count must be divisible by 3 for batch mode."
        )

    outputs: list[Path] = []
    for offset in range(0, len(source_images), 3):
        group = source_images[offset : offset + 3]
        output_name = f"{output_prefix}-{start_index + (offset // 3):02d}.{output_format}"
        output_path = directory / output_name
        outputs.append(
            compose_triptych(
                group,
                output_path,
                target_height=target_height,
                quality=quality,
            )
        )
        if delete_sources:
            for source in group:
                source.unlink()
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compose blog image triptychs and convert assets to WebP."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    compose_parser = subparsers.add_parser(
        "compose-triptych",
        help="Compose exactly three images side by side without cropping.",
    )
    compose_parser.add_argument("inputs", nargs=3, type=Path, help="Three source image paths.")
    compose_parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output file path (.jpg, .png, or .webp).",
    )
    compose_parser.add_argument(
        "--target-height",
        type=int,
        default=None,
        help="Optional explicit output height. Defaults to the tallest source image.",
    )
    compose_parser.add_argument("--quality", type=int, default=92)

    batch_parser = subparsers.add_parser(
        "batch-triptychs",
        help="Compose all images in a directory into sorted groups of three.",
    )
    batch_parser.add_argument("--dir", required=True, type=Path, dest="directory")
    batch_parser.add_argument("--output-prefix", required=True)
    batch_parser.add_argument(
        "--output-format",
        default="jpg",
        choices=["jpg", "png", "webp"],
    )
    batch_parser.add_argument("--target-height", type=int, default=None)
    batch_parser.add_argument("--quality", type=int, default=92)
    batch_parser.add_argument("--start-index", type=int, default=1)
    batch_parser.add_argument("--delete-sources", action="store_true")

    webp_parser = subparsers.add_parser(
        "to-webp",
        help="Convert one or more images to WebP, optionally resizing width.",
    )
    webp_parser.add_argument("inputs", nargs="+", type=Path)
    webp_parser.add_argument("--max-width", type=int, default=2400)
    webp_parser.add_argument("--quality", type=int, default=84)
    webp_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional output directory. Defaults to each source directory.",
    )
    webp_parser.add_argument("--delete-sources", action="store_true")

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.command == "compose-triptych":
        output = compose_triptych(
            args.inputs,
            args.output,
            target_height=args.target_height,
            quality=args.quality,
        )
        print(output)
        return 0

    if args.command == "batch-triptychs":
        outputs = batch_triptychs(
            args.directory,
            output_prefix=args.output_prefix,
            output_format=args.output_format,
            quality=args.quality,
            target_height=args.target_height,
            start_index=args.start_index,
            delete_sources=args.delete_sources,
        )
        for output in outputs:
            print(output)
        return 0

    if args.command == "to-webp":
        for input_path in args.inputs:
            output_path = None
            if args.output_dir is not None:
                output_path = args.output_dir / input_path.with_suffix(".webp").name
            converted = convert_to_webp(
                input_path,
                output_path=output_path,
                max_width=args.max_width,
                quality=args.quality,
                delete_source=args.delete_sources,
            )
            print(converted)
        return 0

    raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
