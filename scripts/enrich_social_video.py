#!/usr/bin/env python3
"""
Enriquece itens do Instagram do tipo Reel/vídeo capturados na base de curadoria.

Para cada Reel ainda não processado, este script:
  1. Chama collect_video_research.py para baixar metadados, extrair áudio e
     transcrever via Whisper/OpenRouter (--force-stt, --skip-ai-analysis).
  2. Lê o título real do video.json gerado e renomeia a pasta para
     <slug>--<platform_post_id>.
  3. Chama analyze_learning.py para gerar ai_insights_learning.json e
     final-learning-report.md em português.
  4. Registra o caminho final em enrichment_path no SQLite.

Usage:
    python3 scripts/enrich_social_video.py --dry-run
    python3 scripts/enrich_social_video.py --limit 3
    python3 scripts/enrich_social_video.py --base-dir data/instagram-research/reels
    python3 scripts/enrich_social_video.py --force --limit 1 <URL específica>

Restrições:
  - Não altera o fluxo de captura existente (social_capture_browser.py / social_curation.py).
  - Não processa itens de LinkedIn nem posts de imagem/link do Instagram.
  - Requer OPENROUTER_API_KEY no ambiente ou em .env.
  - Requer yt-dlp e ffmpeg instalados.
"""

from __future__ import annotations

import argparse
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
COLLECT_SCRIPT = ROOT / "youtube-research" / "scripts" / "collect_video_research.py"
ANALYZE_SCRIPT = ROOT / "youtube-research" / "scripts" / "analyze_learning.py"
DEFAULT_BASE_DIR = ROOT / "data" / "instagram-research" / "reels"
DEFAULT_MODEL = "deepseek/deepseek-v4-pro"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_env() -> None:
    """Carrega variáveis do .env se existir (sem dependência de python-dotenv)."""
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
    """Converte texto em slug filesystem-safe."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_-]+", "-", text)
    text = text.strip("-")
    return text[:max_length].rstrip("-")


def reel_id_from_url(url: str) -> str:
    """Extrai o ID de um Reel a partir da URL. Retorna string vazia se não encontrar."""
    m = re.search(r"instagram\.com/(?:reel|p|tv)/([^/?#]+)", url)
    return m.group(1) if m else ""


def is_video_url(url: str) -> bool:
    """Retorna True se a URL for de um Reel, vídeo (IGTV) ou post do Instagram."""
    return bool(re.search(r"instagram\.com/(reel|tv)/", url))


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def query_video_items(con: Any, force: bool = False, url_filter: str = "") -> list[dict]:
    """
    Retorna itens do Instagram que são Reels/vídeos ainda não enriquecidos.

    Reels são identificados pelo padrão de URL (/reel/ ou /tv/), já que
    social_capture_browser.py salva kind='saved' para todos os itens.
    """
    conditions = ["source = 'instagram'"]
    if url_filter:
        # Para reprocessamento manual, aceita a URL explicitamente mesmo se for /p/.
        conditions.append("url = :url_filter")
    else:
        conditions.append("(url LIKE '%instagram.com/reel/%' OR url LIKE '%instagram.com/tv/%')")
    if not force:
        conditions.append("enrichment_path IS NULL")
        conditions.append("enrichment_error IS NULL")
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
    """Atualiza enrichment_path ou enrichment_error no banco."""
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

def _run_subprocess(cmd: list[str], label: str, verbose: bool = False) -> subprocess.CompletedProcess:
    """Executa subprocesso e retorna resultado. Levanta RuntimeError em falha."""
    if verbose:
        print(f"  → {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, capture_output=not verbose, text=True)
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "")[-1200:]
        raise RuntimeError(f"{label} falhou (exit {result.returncode}): {err}")
    return result


def enrich_item(
    item: dict,
    base_dir: Path,
    model: str,
    verbose: bool = False,
    cookies_from_browser: str = "",
    cookies_file: str = "",
) -> str:
    """
    Enriquece um único item do Instagram.

    Fluxo:
    1. Coleta em pasta temporária <base_dir>/<platform_post_id>/
    2. Lê video.json para obter o título real
    3. Renomeia para <slug>--<post_id>/
    4. Roda analyze_learning.py
    5. Retorna o caminho final (relativo ao ROOT)

    Levanta RuntimeError em qualquer falha.
    """
    post_id = item.get("platform_post_id") or reel_id_from_url(item["url"])
    if not post_id:
        raise RuntimeError("Não foi possível determinar o ID do post a partir da URL.")

    base_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = base_dir / post_id

    # Se a pasta temporária existir de uma tentativa anterior, remove para recomeçar limpo
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)

    # --- Passo 1: collect_video_research.py ---
    print(f"  [collect] Coletando {item['url']}")
    collect_cmd = [
        sys.executable,
        str(COLLECT_SCRIPT),
        item["url"],
        "--output-dir", str(tmp_dir),
        "--force-stt",
        "--skip-ai-analysis",
    ]
    if cookies_from_browser:
        collect_cmd += ["--cookies-from-browser", cookies_from_browser]
    if cookies_file:
        collect_cmd += ["--cookies-file", cookies_file]
    _run_subprocess(collect_cmd, label="collect_video_research", verbose=verbose)

    # --- Passo 2: Ler título do video.json ---
    video_json_path = tmp_dir / "video.json"
    title = ""
    if video_json_path.exists():
        try:
            video_data = json.loads(video_json_path.read_text(encoding="utf-8"))
            title = video_data.get("title") or ""
        except Exception:
            pass

    # Fallback: usar título da DB ou URL
    if not title:
        title = item.get("title") or post_id

    # --- Passo 3: Renomear para pasta legível ---
    slug = slugify(title)
    folder_name = f"{slug}--{post_id}" if slug else post_id
    final_dir = base_dir / folder_name

    if final_dir.exists() and final_dir != tmp_dir:
        shutil.rmtree(final_dir)
    tmp_dir.rename(final_dir)
    print(f"  [collect] Pasta: {final_dir.relative_to(ROOT)}")

    # --- Passo 4: analyze_learning.py ---
    print(f"  [analyze] Analisando em {final_dir.relative_to(ROOT)}")
    _run_subprocess(
        [
            sys.executable,
            str(ANALYZE_SCRIPT),
            str(final_dir),
            "--model",
            model,
        ],
        label="analyze_learning",
        verbose=verbose,
    )

    report_path = final_dir / "final-learning-report.md"
    if report_path.exists():
        print(f"  [analyze] Relatório: {report_path.relative_to(ROOT)}")
    else:
        print(f"  [analyze] Aviso: final-learning-report.md não foi gerado.")

    return str(final_dir.relative_to(ROOT))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Enriquece itens Reel/vídeo do Instagram com transcript e análise em português."
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
        help=f"Pasta base para os artefatos gerados. Padrão: {DEFAULT_BASE_DIR}",
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
        "--verbose",
        action="store_true",
        help="Mostra os comandos executados.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Modelo OpenRouter para analyze_learning.py. Padrão: {DEFAULT_MODEL}",
    )
    parser.add_argument(
        "--cookies-from-browser",
        default="",
        help=(
            "Passa --cookies-from-browser ao coletor de vídeo. "
            "Ex.: chrome ou chrome:/tmp/chrome-social-capture"
        ),
    )
    parser.add_argument(
        "--cookies-file",
        default="",
        help="Passa --cookies-file ao coletor de vídeo.",
    )
    return parser.parse_args()


def main() -> None:
    load_env()
    args = parse_args()
    base_dir = Path(args.base_dir)

    # Importação local para não criar dependência circular
    sys.path.insert(0, str(ROOT / "scripts"))
    import social_curation

    con = social_curation.connect()

    items = query_video_items(con, force=args.force, url_filter=args.url)

    if not items:
        print("Nenhum item Reel/vídeo pendente de enriquecimento encontrado.")
        return

    if args.limit > 0:
        items = items[: args.limit]

    print(f"Itens encontrados: {len(items)}")

    if args.dry_run:
        for i, item in enumerate(items, 1):
            post_id = item.get("platform_post_id") or reel_id_from_url(item["url"])
            title = item.get("title") or "(sem título)"
            print(f"  {i}. [{post_id}] {title[:70]} — {item['url']}")
        print("\nModo --dry-run: nenhum processamento realizado.")
        return

    ok = 0
    failed = 0
    for i, item in enumerate(items, 1):
        post_id = item.get("platform_post_id") or reel_id_from_url(item["url"])
        title = item.get("title") or "(sem título)"
        print(f"\n[{i}/{len(items)}] {title[:60]} [{post_id}]")

        try:
            final_path = enrich_item(
                item,
                base_dir,
                model=args.model,
                verbose=args.verbose,
                cookies_from_browser=args.cookies_from_browser,
                cookies_file=args.cookies_file,
            )
            update_db(con, item["fingerprint"], path=final_path)
            print(f"  ✓ Salvo em: {final_path}")
            ok += 1
        except Exception as exc:
            error_msg = str(exc)
            print(f"  ✗ Erro: {error_msg[:200]}")
            update_db(con, item["fingerprint"], error=error_msg)
            failed += 1

    print(f"\nConcluído: {ok} enriquecido(s), {failed} com erro(s).")
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
