#!/usr/bin/env python3
"""
Import a public Behance project into this static portfolio.

Example:
    python scripts/import_behance_project.py \
      "https://www.behance.net/gallery/120196573/Anis-Crua" \
      --slug anis-crua \
      --title "Anis Crua" \
      --tags "Fotografia · Musica · Retrato" \
      --summary "Ensaio fotografico para Anis Crua." \
      --story "Anis Crua e uma sequencia fotografica construida em torno de presenca, corpo e musica." \
      --photography
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PROJECTS_DIR = ROOT / "projects"
PROJECT_ASSETS_DIR = ROOT / "assets" / "images" / "projects"
BUILD_SCRIPT = ROOT / "scripts" / "build_site_metadata.py"
VALIDATE_SCRIPT = ROOT / "scripts" / "validate_site.py"
BASE_URL = "https://bolivaralencastro.com.br"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
)

BEHANCE_SIZE_PREFERENCE = {
    "1400_webp": ["1400_webp", "1400", "fs_webp", "max_3840_webp", "disp"],
    "fs_webp": ["fs_webp", "1400_webp", "1400", "max_3840_webp", "disp"],
    "max_3840_webp": ["max_3840_webp", "fs_webp", "1400_webp", "1400", "disp"],
}


@dataclass(frozen=True)
class SourceImage:
    url: str
    key: str
    order: int
    variant: str


@dataclass(frozen=True)
class OutputImage:
    filename: str
    width: int
    height: int


def fetch_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def download_file(url: str, destination: Path) -> None:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Referer": "https://www.behance.net/",
        },
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        destination.write_bytes(response.read())


def clean_text(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r"<[^>]+>", "", value)
    return re.sub(r"\s+", " ", value).strip()


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value).strip("-").lower()
    return slug or "behance-project"


def extract_meta(content: str, name: str) -> str:
    patterns = [
        rf'<meta[^>]+property=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']',
        rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']{re.escape(name)}["\']',
        rf'<meta[^>]+name=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']',
        rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']{re.escape(name)}["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return clean_text(match.group(1))
    return ""


def extract_title(content: str, fallback_url: str) -> str:
    title = extract_meta(content, "og:title")
    if not title:
        match = re.search(r"<title[^>]*>(.*?)</title>", content, re.IGNORECASE | re.DOTALL)
        title = clean_text(match.group(1)) if match else ""
    title = re.sub(r"\s*::\s*Behance\s*$", "", title).strip()
    if title:
        return title
    path_slug = Path(urllib.parse.urlsplit(fallback_url).path.rstrip("/")).name
    return path_slug.replace("-", " ").title()


def extract_behance_images(content: str, preferred_size: str, max_images: int | None) -> list[SourceImage]:
    url_pattern = re.compile(r"https?://[^\"'<>\\ ]+", re.IGNORECASE)
    grouped: dict[str, list[SourceImage]] = {}

    for match in url_pattern.finditer(content):
        raw_url = html.unescape(match.group(0)).replace("\\u0026", "&")
        raw_url = raw_url.replace("\\/", "/")
        if "mir-s3-cdn-cf.behance.net/project_modules" not in raw_url:
            continue
        if not re.search(r"\.(?:jpg|jpeg|png|webp)(?:\?|$)", raw_url, re.IGNORECASE):
            continue

        parsed = urllib.parse.urlsplit(raw_url)
        parts = parsed.path.split("/")
        try:
            idx = parts.index("project_modules")
            variant = parts[idx + 1]
            filename = parts[idx + 2]
        except (ValueError, IndexError):
            continue
        if "source" in variant.lower():
            continue

        key = filename.lower()
        grouped.setdefault(key, []).append(
            SourceImage(url=raw_url, key=key, order=match.start(), variant=variant)
        )

    preference = BEHANCE_SIZE_PREFERENCE[preferred_size]
    selected: list[SourceImage] = []
    for candidates in grouped.values():
        candidates = sorted(candidates, key=lambda item: item.order)
        best = min(
            candidates,
            key=lambda item: (
                preference.index(item.variant) if item.variant in preference else len(preference),
                item.order,
            ),
        )
        selected.append(best)

    selected.sort(key=lambda item: item.order)
    if max_images is not None:
        selected = selected[:max_images]
    return selected


def run_command(args: list[str], cwd: Path = ROOT) -> str:
    completed = subprocess.run(
        args,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.strip()


def require_magick() -> None:
    if shutil.which("magick") is None:
        raise RuntimeError("ImageMagick nao encontrado. Instale ou coloque `magick` no PATH.")


def identify_dimensions(path: Path) -> tuple[int, int]:
    output = run_command(["magick", "identify", "-format", "%w %h", str(path)])
    width, height = output.split()
    return int(width), int(height)


def convert_content_image(source: Path, destination: Path, max_width: int, quality: int) -> OutputImage:
    args = ["magick", str(source), "-auto-orient"]
    if max_width > 0:
        args.extend(["-resize", f"{max_width}x{max_width}>"])
    args.extend(["-strip", "-quality", str(quality), str(destination)])
    run_command(args)
    width, height = identify_dimensions(destination)
    return OutputImage(destination.name, width, height)


def create_cropped_variant(source: Path, destination: Path, width: int, height: int, quality: int) -> None:
    run_command(
        [
            "magick",
            str(source),
            "-auto-orient",
            "-resize",
            f"{width}x{height}^",
            "-gravity",
            "center",
            "-extent",
            f"{width}x{height}",
            "-strip",
            "-quality",
            str(quality),
            str(destination),
        ]
    )


def create_assets(
    source_images: list[SourceImage],
    slug: str,
    title: str,
    assets_dir: Path,
    max_width: int,
    quality: int,
) -> list[OutputImage]:
    if assets_dir.exists() and any(assets_dir.iterdir()):
        raise FileExistsError(f"Diretorio de assets ja existe e nao esta vazio: {assets_dir}")
    assets_dir.mkdir(parents=True, exist_ok=True)

    safe_prefix = slugify(title) or slug
    outputs: list[OutputImage] = []
    with tempfile.TemporaryDirectory(prefix=f"{slug}-behance-") as tmp_name:
        tmp_dir = Path(tmp_name)
        for idx, source_image in enumerate(source_images, start=1):
            suffix = Path(urllib.parse.urlsplit(source_image.url).path).suffix or ".jpg"
            raw_path = tmp_dir / f"source-{idx:02d}{suffix}"
            download_file(source_image.url, raw_path)
            output_path = assets_dir / f"{safe_prefix}-{idx:02d}.webp"
            outputs.append(convert_content_image(raw_path, output_path, max_width, quality))

    if not outputs:
        raise RuntimeError("Nenhuma imagem foi convertida.")

    first_image = assets_dir / outputs[0].filename
    run_command(["magick", str(first_image), "-strip", "-quality", str(quality), str(assets_dir / "cover.webp")])
    create_cropped_variant(first_image, assets_dir / "card.webp", 960, 540, quality)
    create_cropped_variant(first_image, assets_dir / "card-720.webp", 720, 405, quality)
    create_cropped_variant(first_image, assets_dir / "card-480.webp", 480, 270, quality)
    create_cropped_variant(first_image, assets_dir / "og.webp", 1200, 630, quality)
    return outputs


def paragraph_html(paragraphs: list[str]) -> str:
    return "\n".join(f"          <p>{html.escape(p.strip())}</p>" for p in paragraphs if p.strip())


def build_project_html(
    slug: str,
    title: str,
    summary: str,
    tags: str,
    behance_url: str,
    images: list[OutputImage],
    image_prefix_alt: str,
    story: list[str],
) -> str:
    canonical = f"{BASE_URL}/projects/{slug}.html"
    image_base = f"/assets/images/projects/{slug}"
    absolute_og = f"{BASE_URL}/assets/images/projects/{slug}/og.webp"
    json_ld = {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": title,
        "description": summary,
        "url": canonical,
        "author": {"@type": "Person", "name": "Bolivar Alencastro"},
        "isBasedOn": behance_url,
    }

    figures = []
    for idx, image in enumerate(images, start=1):
        loading = ' decoding="async" fetchpriority="high"' if idx == 1 else ' loading="lazy" decoding="async"'
        alt = (
            f"{image_prefix_alt}, imagem de abertura"
            if idx == 1
            else f"{image_prefix_alt}, imagem {idx}"
        )
        figures.append(
            "        <figure>\n"
            f'          <img src="{image_base}/{image.filename}" alt="{html.escape(alt)}" '
            f'width="{image.width}" height="{image.height}"{loading}>\n'
            "        </figure>"
        )

    story_paragraphs = story or [
        (
            f"{title} reune uma sequencia visual selecionada para leitura em pagina, "
            "com uma imagem por vez e respiro entre cada entrada."
        )
    ]

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(title)} - Bolivar Alencastro</title>
  <meta name="description" content="{html.escape(summary)}">
  <link rel="stylesheet" href="/style.css">
  <noscript><link rel="stylesheet" href="/assets/css/nojs-nav.css"></noscript>
  <link rel="canonical" href="{canonical}">
  <meta property="og:title" content="{html.escape(title)} - Bolivar Alencastro">
  <meta property="og:description" content="{html.escape(summary)}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:type" content="article">
  <meta property="og:image" content="{absolute_og}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{html.escape(title)} - Bolivar Alencastro">
  <meta name="twitter:description" content="{html.escape(summary)}">
  <meta name="twitter:image" content="{absolute_og}">
  <script type="application/ld+json">
  {json.dumps(json_ld, ensure_ascii=False, indent=2)}
  </script>
  <meta name="view-transition" content="same-origin">
  <script src="/assets/js/lightbox.js" defer></script>
</head>
<body>
  <div class="grain"></div>
  <a href="#main" class="skip-link">Pular para o conteudo</a>

  <header class="grid">
    <div class="brand col-7"><a href="/" class="brand-link"><span class="brand-mark" aria-hidden="true"><span class="dot dot-blue"></span></span><strong>Bolivar Alencastro</strong></a></div>
    <nav class="col-5" aria-label="Navegacao principal">
      <ul>
        <li><a href="/">Home</a></li>
        <li><a href="/about.html">About</a></li>
        <li><a href="/projects.html" aria-current="page">Projects</a></li>
        <li><a href="/blog.html">Blog</a></li>
        <li><a href="/now.html">Now</a></li>
      </ul>
    </nav>
  </header>

  <main id="main" class="grid h-entry">
    <h1 class="p-name col-9">{html.escape(title)}</h1>
    <p class="meta col-3">{html.escape(tags)}</p>

    <article class="e-content grid col-12 section-block">
      <div class="project-column col-8">
        <div class="project-story">
{paragraph_html(story_paragraphs)}
        </div>
      </div>

      <section class="photo-sequence col-12" aria-label="Sequencia visual {html.escape(title)}">
{chr(10).join(figures)}
      </section>

      <div class="project-column col-8">
        <div class="project-reference">
          <p>Arquivo original: <a href="{html.escape(behance_url)}" rel="noopener noreferrer" target="_blank">{html.escape(title)} no Behance</a>.</p>
        </div>
        <!-- AUTO:project-author-card:start -->
        <!-- AUTO:project-author-card:end -->
      </div>
    </article>
    <!-- AUTO:project-related-projects:start -->
    <!-- AUTO:project-related-projects:end -->
  </main>
</body>
</html>
"""


def add_photography_project(slug: str) -> bool:
    href = f'    "/projects/{slug}.html",'
    content = BUILD_SCRIPT.read_text(encoding="utf-8")
    if href in content:
        return False
    marker = "PHOTOGRAPHY_PROJECT_HREFS = {\n"
    if marker not in content:
        raise RuntimeError("Nao encontrei PHOTOGRAPHY_PROJECT_HREFS em build_site_metadata.py")
    content = content.replace(marker, marker + href + "\n", 1)
    BUILD_SCRIPT.write_text(content, encoding="utf-8", newline="\n")
    return True


def import_project(args: argparse.Namespace) -> dict:
    require_magick()
    content = fetch_text(args.url)
    title = args.title or extract_title(content, args.url)
    slug = args.slug or slugify(title)
    summary = args.summary or extract_meta(content, "description") or f"Projeto {title}."
    tags = args.tags or "Projeto"

    project_path = PROJECTS_DIR / f"{slug}.html"
    assets_dir = PROJECT_ASSETS_DIR / slug
    if not args.force:
        if project_path.exists():
            raise FileExistsError(f"Projeto ja existe: {project_path}. Use --force para sobrescrever.")
        if assets_dir.exists() and any(assets_dir.iterdir()):
            raise FileExistsError(f"Assets ja existem: {assets_dir}. Use --force para sobrescrever.")
    if args.force:
        if project_path.exists():
            project_path.unlink()
        if assets_dir.exists():
            shutil.rmtree(assets_dir)

    source_images = extract_behance_images(content, args.behance_size, args.max_images)
    if not source_images:
        raise RuntimeError("Nao encontrei imagens de projeto no HTML do Behance.")

    if args.dry_run:
        return {
            "slug": slug,
            "title": title,
            "summary": summary,
            "image_count": len(source_images),
            "images": [image.url for image in source_images],
        }

    outputs = create_assets(
        source_images,
        slug=slug,
        title=title,
        assets_dir=assets_dir,
        max_width=args.content_max_width,
        quality=args.quality,
    )
    image_prefix_alt = args.alt_prefix or f"Imagem do projeto {title}"
    project_html = build_project_html(
        slug=slug,
        title=title,
        summary=summary,
        tags=tags,
        behance_url=args.url,
        images=outputs,
        image_prefix_alt=image_prefix_alt,
        story=args.story,
    )
    project_path.write_text(project_html, encoding="utf-8", newline="\n")

    photography_registered = add_photography_project(slug) if args.photography else False

    build_output = ""
    validate_output = ""
    if not args.no_build:
        build_output = run_command([sys.executable, str(BUILD_SCRIPT)])
        validate_output = run_command([sys.executable, str(VALIDATE_SCRIPT)])

    return {
        "slug": slug,
        "title": title,
        "project_path": str(project_path.relative_to(ROOT)),
        "assets_dir": str(assets_dir.relative_to(ROOT)),
        "image_count": len(outputs),
        "photography_registered": photography_registered,
        "build_output": build_output,
        "validate_output": validate_output,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Importa um projeto publico do Behance para /projects.")
    parser.add_argument("url", help="URL publica do projeto no Behance.")
    parser.add_argument("--slug", help="Slug final em projects/<slug>.html.")
    parser.add_argument("--title", help="Titulo editorial do projeto.")
    parser.add_argument("--summary", help="Meta description do projeto.")
    parser.add_argument("--tags", help='Linha de tags, ex: "Fotografia · Retrato".')
    parser.add_argument(
        "--story",
        action="append",
        default=[],
        help="Paragrafo editorial. Pode repetir para criar varios paragrafos.",
    )
    parser.add_argument("--alt-prefix", help="Prefixo dos textos alternativos das imagens.")
    parser.add_argument("--photography", action="store_true", help="Marca o projeto como fotografia na listagem.")
    parser.add_argument("--max-images", type=int, help="Limite de imagens importadas.")
    parser.add_argument(
        "--behance-size",
        choices=sorted(BEHANCE_SIZE_PREFERENCE),
        default="1400_webp",
        help="Tamanho preferido das imagens extraidas do Behance.",
    )
    parser.add_argument(
        "--content-max-width",
        type=int,
        default=1600,
        help="Largura maxima das imagens de conteudo. Use 0 para preservar.",
    )
    parser.add_argument("--quality", type=int, default=86, help="Qualidade WebP/JPEG gerada.")
    parser.add_argument("--force", action="store_true", help="Sobrescreve projeto/assets existentes.")
    parser.add_argument("--dry-run", action="store_true", help="Mostra o que seria importado sem escrever arquivos.")
    parser.add_argument("--no-build", action="store_true", help="Nao roda build_site_metadata/validate_site.")
    args = parser.parse_args()

    try:
        result = import_project(args)
    except (OSError, RuntimeError, urllib.error.URLError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
