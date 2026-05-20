#!/usr/bin/env python3
"""
Enriquece posts de imagem/carrossel do Instagram capturados na base de curadoria.

Para cada post /p/ ainda não processado, este script:
  1. Usa yt-dlp para detectar o tipo de mídia (imagem vs vídeo).
     — Posts de vídeo são marcados para ignorar (já cobertos por enrich_social_video.py).
  2. Baixa todas as imagens do carrossel com yt-dlp (--yes-playlist).
  3. Salva post.json com os metadados do post.
  4. Chama analyze_images.py para gerar ai_insights_images.json e final-image-report.md.
  5. Registra o caminho final em enrichment_path no SQLite.

Usage:
    python3 scripts/enrich_social_image.py --dry-run
    python3 scripts/enrich_social_image.py --limit 3
    python3 scripts/enrich_social_image.py --url https://www.instagram.com/p/XYZ/
    python3 scripts/enrich_social_image.py --use-browser-cookies --limit 5

Pré-requisitos:
  - OPENROUTER_API_KEY no .env ou no ambiente.
  - yt-dlp instalado (pip install yt-dlp).
  - Para posts privados/salvos: Chrome aberto com a conta logada e usar --use-browser-cookies.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent.parent
ANALYZE_SCRIPT = ROOT / "youtube-research" / "scripts" / "analyze_images.py"
DEFAULT_BASE_DIR = ROOT / "data" / "instagram-research" / "posts"

VIDEO_EXTENSIONS = {".mp4", ".m4v", ".webm", ".mkv", ".mov", ".avi"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    with env_path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def slugify(text: str, max_length: int = 60) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_-]+", "-", text)
    text = text.strip("-")
    return text[:max_length].rstrip("-")


def post_id_from_url(url: str) -> str:
    m = re.search(r"instagram\.com/(?:p|reel|tv)/([^/?#]+)", url)
    return m.group(1) if m else ""


def run_subprocess(cmd: list[str], label: str, verbose: bool = False) -> subprocess.CompletedProcess:
    if verbose:
        print(f"  → {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, capture_output=not verbose, text=True)
    if result.returncode != 0:
        err = (result.stderr or "")[-800:]
        raise RuntimeError(f"{label} falhou (exit {result.returncode}): {err}")
    return result


# ---------------------------------------------------------------------------
# yt-dlp helpers
# ---------------------------------------------------------------------------

YT_DLP_CMD = [sys.executable, "-m", "yt_dlp"]


def _yt_dlp_base(url: str, cookies: bool) -> list[str]:
    cmd = list(YT_DLP_CMD)
    if cookies:
        cmd += ["--cookies-from-browser", "chrome"]
    cmd += [url]
    return cmd


def _yt_cookie_args(
    use_browser_cookies: bool,
    cookies_from_browser: str = "",
    cookies_file: str = "",
) -> list[str]:
    args: list[str] = []
    browser_value = (cookies_from_browser or "").strip()
    file_value = (cookies_file or "").strip()
    if use_browser_cookies or browser_value:
        args += ["--cookies-from-browser", browser_value or "chrome"]
    if file_value:
        args += ["--cookies", file_value]
    return args


def fetch_metadata(
    url: str,
    cookies: bool,
    cookies_from_browser: str = "",
    cookies_file: str = "",
) -> dict[str, Any]:
    """Retorna o JSON de metadados do yt-dlp sem baixar nada."""
    cmd = list(YT_DLP_CMD) + ["--no-playlist", "--skip-download", "--dump-single-json"]
    cmd += _yt_cookie_args(cookies, cookies_from_browser, cookies_file)
    cmd += [url]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp metadata falhou: {(result.stderr or '')[-500:]}")
    return json.loads(result.stdout or "{}")


def is_video_metadata(info: dict) -> bool:
    """Retorna True se o post for vídeo (Reel/IGTV), False se for imagem/carrossel."""
    # yt-dlp usa 'vcodec' para indicar presença de vídeo
    vcodec = info.get("vcodec") or ""
    if vcodec and vcodec != "none":
        return True
    # Fallback: olhar extensão esperada
    ext = info.get("ext") or ""
    if ext in ("mp4", "m4v", "webm"):
        return True
    # Carrossel: yt-dlp retorna _type=playlist com entries
    if info.get("_type") == "playlist":
        entries = info.get("entries") or []
        if entries:
            first = entries[0] or {}
            first_ext = first.get("ext") or ""
            if first_ext in ("mp4", "m4v", "webm"):
                return True
    return False


def download_slides(
    url: str,
    slides_dir: Path,
    cookies: bool,
    verbose: bool,
    cookies_from_browser: str = "",
    cookies_file: str = "",
) -> list[Path]:
    """
    Baixa todas as imagens do post (suporta carrossel via --yes-playlist).
    Retorna lista de arquivos baixados.
    """
    slides_dir.mkdir(parents=True, exist_ok=True)
    cmd = list(YT_DLP_CMD) + [
        "--yes-playlist",
        "-o", str(slides_dir / "%(playlist_index)02d-%(id)s.%(ext)s"),
    ]
    cmd += _yt_cookie_args(cookies, cookies_from_browser, cookies_file)
    cmd += [url]
    run_subprocess(cmd, label="yt-dlp download", verbose=verbose)

    # Coleta arquivos baixados
    files = sorted(slides_dir.iterdir())
    images = [f for f in files if f.suffix.lower() in IMAGE_EXTENSIONS]
    videos = [f for f in files if f.suffix.lower() in VIDEO_EXTENSIONS]
    return images, videos


def _fetch_page_html(url: str) -> str:
    cmd = ["curl", "-L", "-A", "Mozilla/5.0", url]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"curl falhou ao baixar HTML ({result.returncode}): {(result.stderr or '')[-300:]}")
    return result.stdout or ""


def _extract_og_meta(page_html: str) -> dict[str, str]:
    keys = {
        "image": "og:image",
        "title": "og:title",
        "description": "og:description",
        "url": "og:url",
    }
    out: dict[str, str] = {}
    for out_key, prop in keys.items():
        match = re.search(
            rf'<meta[^>]+property="{re.escape(prop)}"[^>]+content="([^"]+)"',
            page_html,
            flags=re.IGNORECASE,
        )
        if match:
            out[out_key] = html.unescape(match.group(1))
    return out


def _download_og_image(url: str, slides_dir: Path, verbose: bool) -> tuple[list[Path], dict[str, str]]:
    page_html = _fetch_page_html(url)
    og = _extract_og_meta(page_html)
    image_url = (og.get("image") or "").strip()
    if not image_url:
        return [], og

    slides_dir.mkdir(parents=True, exist_ok=True)
    out_path = slides_dir / "01-og-image.jpg"
    cmd = ["curl", "-L", image_url, "-o", str(out_path)]
    if verbose:
        print(f"  → {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=not verbose, text=True)
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "")[-300:]
        raise RuntimeError(f"Falha ao baixar og:image: {err}")
    if not out_path.exists() or out_path.stat().st_size == 0:
        raise RuntimeError("Falha ao baixar og:image: arquivo vazio")
    return [out_path], og


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def query_image_items(con: Any, force: bool, url_filter: str) -> list[dict]:
    """
    Retorna itens do Instagram com URL /p/ ainda não enriquecidos.
    Inclui tanto posts de imagem quanto carrosseis.
    """
    conditions = [
        "source = 'instagram'",
        "url LIKE '%instagram.com/p/%'",
    ]
    if not force:
        conditions.append("enrichment_path IS NULL")
        conditions.append("enrichment_error IS NULL")
    if url_filter:
        conditions.append("url = :url_filter")

    sql = f"""
        SELECT fingerprint, url, title, author, author_handle, platform_post_id, text, date
        FROM social_items
        WHERE {" AND ".join(conditions)}
        ORDER BY date DESC
    """
    params: dict = {}
    if url_filter:
        params["url_filter"] = url_filter
    rows = con.execute(sql, params).fetchall()
    cols = ["fingerprint", "url", "title", "author", "author_handle",
            "platform_post_id", "text", "date"]
    return [dict(zip(cols, row)) for row in rows]


def update_db(con: Any, fingerprint: str, *, path: str | None = None, error: str | None = None) -> None:
    if path is not None:
        con.execute(
            "UPDATE social_items SET enrichment_path = ?, enrichment_error = NULL WHERE fingerprint = ?",
            (path, fingerprint),
        )
    elif error is not None:
        con.execute(
            "UPDATE social_items SET enrichment_error = ? WHERE fingerprint = ?",
            (error[:500], fingerprint),
        )
    con.commit()


# ---------------------------------------------------------------------------
# Core enrichment
# ---------------------------------------------------------------------------

def enrich_item(
    item: dict,
    base_dir: Path,
    cookies: bool,
    verbose: bool,
    model: str,
    require_carousel: bool = False,
    cookies_from_browser: str = "",
    cookies_file: str = "",
) -> str:
    """
    Enriquece um único post de imagem/carrossel do Instagram.

    Fluxo:
    1. Detecta tipo via yt-dlp metadata
    2. Se vídeo → levanta VideoPostError (para skip)
    3. Baixa imagens em pasta temporária
    4. Salva post.json
    5. Renomeia pasta para <slug>--<post_id>
    6. Executa analyze_images.py
    7. Retorna caminho relativo ao ROOT
    """
    post_id = item.get("platform_post_id") or post_id_from_url(item["url"])
    if not post_id:
        raise RuntimeError("Não foi possível determinar o ID do post.")

    base_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = base_dir / post_id

    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)

    # --- Passo 1: detectar tipo ---
    print(f"  [detect] Verificando tipo de mídia…")
    og_meta: dict[str, str] = {}
    info: dict[str, Any] = {}
    try:
        info = fetch_metadata(
            item["url"],
            cookies,
            cookies_from_browser=cookies_from_browser,
            cookies_file=cookies_file,
        )
    except RuntimeError as exc:
        err_text = str(exc)
        if "There is no video in this post" in err_text or "No video formats found" in err_text:
            print("  [detect] yt-dlp não retornou formatos para imagem; usando fallback og:image")
            info = {}
        else:
            raise RuntimeError(f"Não foi possível ler metadados: {exc}") from exc

    if is_video_metadata(info):
        raise _VideoPostError("post de vídeo — use enrich_social_video.py")

    expected_images = 0
    if info.get("_type") == "playlist":
        entries = [e for e in (info.get("entries") or []) if isinstance(e, dict)]
        expected_images = len(entries)

    # --- Passo 2: baixar imagens ---
    print(f"  [download] Baixando slides de {item['url']}")
    tmp_dir.mkdir(parents=True)
    slides_dir = tmp_dir / "slides"
    try:
        images, videos = download_slides(
            item["url"],
            slides_dir,
            cookies,
            verbose,
            cookies_from_browser=cookies_from_browser,
            cookies_file=cookies_file,
        )
    except RuntimeError as exc:
        print(f"  [download] yt-dlp falhou ({str(exc)[:140]}), tentando fallback por og:image")
        images, videos = [], []

    used_og_fallback = False
    if not images:
        if videos:
            raise _VideoPostError("apenas vídeos baixados — post de vídeo")
        print("  [download] yt-dlp não trouxe imagens; tentando fallback por og:image")
        fallback_images, og_meta = _download_og_image(item["url"], slides_dir, verbose)
        images = fallback_images
        used_og_fallback = bool(images)
        if not images:
            raise RuntimeError("Nenhuma imagem baixada. O post pode ser privado ou indisponível.")

    if require_carousel:
        if expected_images <= 1:
            raise RuntimeError(
                "Validação de carrossel exigida, mas metadados não confirmaram múltiplos slides. "
                "Use cookies válidos e tente novamente."
            )
        if used_og_fallback:
            raise RuntimeError(
                "Validação de carrossel falhou: fallback og:image não representa o carrossel completo."
            )
        if len(images) < expected_images:
            raise RuntimeError(
                f"Validação de carrossel falhou: baixado(s) {len(images)} de {expected_images} slide(s)."
            )

    print(f"  [download] {len(images)} imagem(ns) baixada(s)")

    # --- Passo 3: salvar post.json ---
    post_data = {
        "id": info.get("id") or post_id,
        "title": info.get("title") or info.get("fulltitle") or og_meta.get("title") or item.get("title") or "",
        "uploader": info.get("uploader") or info.get("channel") or item.get("author") or "",
        "uploader_id": info.get("uploader_id") or item.get("author_handle") or "",
        "description": info.get("description") or og_meta.get("description") or item.get("text") or "",
        "url": info.get("webpage_url") or og_meta.get("url") or item.get("url") or "",
        "timestamp": info.get("timestamp"),
        "like_count": info.get("like_count"),
        "comment_count": info.get("comment_count"),
        "n_slides": len(images),
        "platform": "instagram",
        "source_url": item["url"],
        "image_source": "yt-dlp" if info else "og:image",
    }
    (tmp_dir / "post.json").write_text(
        json.dumps(post_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # --- Passo 4: renomear para pasta legível ---
    title = post_data.get("title") or ""
    slug = slugify(title) if title else ""
    folder_name = f"{slug}--{post_id}" if slug else post_id
    final_dir = base_dir / folder_name

    if final_dir.exists() and final_dir != tmp_dir:
        shutil.rmtree(final_dir)
    tmp_dir.rename(final_dir)
    print(f"  [download] Pasta: {final_dir.relative_to(ROOT)}")

    # --- Passo 5: analyze_images.py ---
    print(f"  [analyze] Analisando imagens com visão…")
    result = subprocess.run(
        [sys.executable, str(ANALYZE_SCRIPT), str(final_dir), "--model", model],
        capture_output=not verbose,
        text=True,
    )
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "")[-600:]
        raise RuntimeError(f"analyze_images falhou: {err}")

    if verbose and result.stdout:
        for line in result.stdout.strip().splitlines():
            print(f"    {line}")

    report_path = final_dir / "final-image-report.md"
    if report_path.exists():
        print(f"  [analyze] Relatório: {report_path.relative_to(ROOT)}")
    else:
        print("  [analyze] Aviso: final-image-report.md não foi gerado.")

    return str(final_dir.relative_to(ROOT))


class _VideoPostError(Exception):
    """Sinaliza que o post é de vídeo e deve ser ignorado por este script."""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Enriquece posts de imagem/carrossel do Instagram com análise visual em português."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Lista os itens que seriam processados sem executar nada.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Número máximo de itens a processar. 0 = todos.",
    )
    parser.add_argument(
        "--base-dir",
        default=str(DEFAULT_BASE_DIR),
        help=f"Pasta base para artefatos. Padrão: {DEFAULT_BASE_DIR}",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocessa itens que já têm enrichment_path ou enrichment_error.",
    )
    parser.add_argument(
        "--url",
        default="",
        help="Filtra por URL específica (útil para testar um único item).",
    )
    parser.add_argument(
        "--use-browser-cookies",
        action="store_true",
        help=(
            "Passa --cookies-from-browser chrome ao yt-dlp. "
            "Necessário para posts privados/salvos. Requer Chrome com a conta logada."
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Mostra os comandos executados.",
    )
    parser.add_argument(
        "--model",
        default="openai/gpt-4.1-mini",
        help="Modelo de visão no OpenRouter para analyze_images.py.",
    )
    parser.add_argument(
        "--require-carousel",
        action="store_true",
        help=(
            "Exige carrossel completo (metadados + todos os slides) para posts /p/. "
            "Falha quando cai em fallback og:image ou quando o total de imagens é incompleto."
        ),
    )
    parser.add_argument(
        "--cookies-from-browser",
        default="",
        help=(
            "Valor explícito de --cookies-from-browser para yt-dlp. "
            "Ex.: chrome ou chrome:/tmp/chrome-social-capture"
        ),
    )
    parser.add_argument(
        "--cookies-file",
        default="",
        help="Arquivo Netscape de cookies para yt-dlp (--cookies).",
    )
    return parser.parse_args()


def main() -> None:
    load_env()
    args = parse_args()
    base_dir = Path(args.base_dir)

    sys.path.insert(0, str(ROOT / "scripts"))
    import social_curation

    con = social_curation.connect()
    items = query_image_items(con, force=args.force, url_filter=args.url)

    if not items:
        print("Nenhum post /p/ pendente de enriquecimento encontrado.")
        return

    if args.limit > 0:
        items = items[: args.limit]

    print(f"Itens encontrados: {len(items)}")

    if args.dry_run:
        for i, item in enumerate(items, 1):
            post_id = item.get("platform_post_id") or post_id_from_url(item["url"])
            title = item.get("title") or "(sem título)"
            print(f"  {i}. [{post_id}] {title[:70]} — {item['url']}")
        print("\nModo --dry-run: nenhum processamento realizado.")
        return

    ok = 0
    skipped = 0
    failed = 0

    for i, item in enumerate(items, 1):
        post_id = item.get("platform_post_id") or post_id_from_url(item["url"])
        title = item.get("title") or "(sem título)"
        print(f"\n[{i}/{len(items)}] {title[:60]} [{post_id}]")

        try:
            final_path = enrich_item(
                item,
                base_dir,
                cookies=args.use_browser_cookies,
                verbose=args.verbose,
                model=args.model,
                require_carousel=args.require_carousel,
                cookies_from_browser=args.cookies_from_browser,
                cookies_file=args.cookies_file,
            )
            update_db(con, item["fingerprint"], path=final_path)
            print(f"  ✓ Salvo em: {final_path}")
            ok += 1

        except _VideoPostError as exc:
            # Marca como vídeo para não reprocessar; sem bloco de erro visível
            update_db(con, item["fingerprint"], error=f"SKIP:video — {exc}")
            print(f"  → Pulado (vídeo): {exc}")
            skipped += 1

        except Exception as exc:
            error_msg = str(exc)
            print(f"  ✗ Erro: {error_msg[:200]}")
            update_db(con, item["fingerprint"], error=error_msg)
            failed += 1

    print(f"\nConcluído: {ok} enriquecido(s), {skipped} pulado(s) como vídeo, {failed} com erro(s).")
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
