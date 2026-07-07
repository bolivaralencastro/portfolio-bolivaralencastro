#!/usr/bin/env python3
"""
Publica no Threads via Threads API (texto, imagem única ou carrossel).

Modos:
    # Texto puro (o primeiro link do texto vira card clicável)
    python3 scripts/threads_post.py --text "..." --dry-run

    # Carrossel/imagem a partir de um diretório com caption.txt + slide-NN.jpg
    python3 scripts/threads_post.py assets/images/social/threads/meu-post --dry-run

    # Reusando slides já commitados em outro diretório do repo
    python3 scripts/threads_post.py assets/images/social/threads/meu-post \
        --slides-dir assets/images/social/instagram/meu-post

Pré-requisitos:
    - THREADS_ACCESS_TOKEN e THREADS_USER_ID no .env (gere com threads_auth.py)
    - Slides commitados e pushados (as URLs públicas vêm do raw do GitHub)

Limite do Threads: 500 caracteres de texto por post.
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:
    import certifi

    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = ssl.create_default_context()

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
GRAPH_API = "https://graph.threads.net/v1.0"
DEFAULT_REPO = "bolivaralencastro/portfolio-bolivaralencastro"
TEXT_LIMIT = 500


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


def detect_git_ref() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def collect_slide_paths(slides_dir: Path) -> list[Path]:
    pattern = re.compile(r"^slide-\d{2}\.(jpg|png)$", re.IGNORECASE)
    slides = sorted(p for p in slides_dir.iterdir() if pattern.match(p.name))
    return slides


def build_raw_github_url(repo: str, ref: str, path: Path) -> str:
    rel = path.resolve().relative_to(ROOT)
    return f"https://raw.githubusercontent.com/{repo}/{ref}/{rel.as_posix()}"


def graph_post(path: str, payload: dict) -> dict:
    data = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(f"{GRAPH_API}/{path.lstrip('/')}", data=data, method="POST")
    with urllib.request.urlopen(req, timeout=60, context=SSL_CONTEXT) as r:
        return json.loads(r.read())


def graph_get(path: str, params: dict) -> dict:
    url = f"{GRAPH_API}/{path.lstrip('/')}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=30, context=SSL_CONTEXT) as r:
        return json.loads(r.read())


def wait_container(container_id: str, token: str, label: str, attempts: int = 15):
    for attempt in range(1, attempts + 1):
        data = graph_get(container_id, {"fields": "status,error_message", "access_token": token})
        status = data.get("status")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"{label}: {data.get('error_message', data)}")
        print(f"   {label}: {status} ({attempt}/{attempts})")
        time.sleep(4)
    raise TimeoutError(f"{label}: container não finalizou a tempo")


def check_public_urls(urls: list[str]):
    print("🔎 Verificando URLs públicas...")
    for url in urls:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=30, context=SSL_CONTEXT) as r:
            if r.status != 200:
                raise RuntimeError(f"URL não pública ({r.status}): {url}")
    print("   URLs OK")


def main():
    parser = argparse.ArgumentParser(description="Publica no Threads")
    parser.add_argument("content_dir", nargs="?", help="Diretório com caption.txt (e slide-NN.jpg, salvo --slides-dir)")
    parser.add_argument("--text", help="Texto do post (modo texto puro, sem imagens)")
    parser.add_argument("--slides-dir", help="Diretório alternativo (repo-relativo) de onde ler os slides")
    parser.add_argument("--ref", help="Git ref público para URLs raw do GitHub")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="owner/repo do GitHub")
    parser.add_argument("--dry-run", action="store_true", help="Só mostra o payload")
    parser.add_argument("--skip-url-check", action="store_true", help="Pula verificação HEAD das URLs")
    args = parser.parse_args()

    env = load_env()
    token = env.get("THREADS_ACCESS_TOKEN", "").strip()
    user_id = env.get("THREADS_USER_ID", "").strip()
    if not args.dry_run and (not token or not user_id):
        print("❌ THREADS_ACCESS_TOKEN/THREADS_USER_ID ausentes no .env — rode threads_auth.py")
        sys.exit(1)

    slides: list[Path] = []
    if args.text and not args.content_dir:
        text = args.text.strip()
    elif args.content_dir:
        content_dir = (ROOT / args.content_dir).resolve() if not Path(args.content_dir).is_absolute() else Path(args.content_dir)
        caption_path = content_dir / "caption.txt"
        if not caption_path.exists():
            print(f"❌ Legenda não encontrada: {caption_path}")
            sys.exit(1)
        text = caption_path.read_text(encoding="utf-8").strip()
        slides_dir = (ROOT / args.slides_dir).resolve() if args.slides_dir else content_dir
        slides = collect_slide_paths(slides_dir)
    else:
        print("❌ Informe um diretório de conteúdo ou --text")
        sys.exit(1)

    if len(text) > TEXT_LIMIT:
        print(f"❌ Texto com {len(text)} caracteres — o limite do Threads é {TEXT_LIMIT}.")
        sys.exit(1)

    slide_urls: list[str] = []
    if slides:
        ref = args.ref or detect_git_ref()
        slide_urls = [build_raw_github_url(args.repo, ref, s) for s in slides]
        print(f"🧵 Threads: {len(slides)} imagem(ns) | ref {ref[:12]}")
        for i, url in enumerate(slide_urls, 1):
            print(f"   {i:02d}. {url}")
    else:
        print("🧵 Threads: post de texto")

    print(f"\n--- Texto ({len(text)}/{TEXT_LIMIT}) ---\n{text}\n---------------\n")

    if args.dry_run:
        print("🔍 Dry run: nada publicado.")
        return

    try:
        if slide_urls and not args.skip_url_check:
            check_public_urls(slide_urls)

        if not slide_urls:
            creation = graph_post(
                f"{user_id}/threads",
                {"media_type": "TEXT", "text": text, "access_token": token},
            )
            container_id = creation["id"]
        elif len(slide_urls) == 1:
            creation = graph_post(
                f"{user_id}/threads",
                {"media_type": "IMAGE", "image_url": slide_urls[0], "text": text, "access_token": token},
            )
            container_id = creation["id"]
        else:
            print("🔄 Criando containers dos slides...")
            children: list[str] = []
            for i, url in enumerate(slide_urls, 1):
                item = graph_post(
                    f"{user_id}/threads",
                    {
                        "media_type": "IMAGE",
                        "image_url": url,
                        "is_carousel_item": "true",
                        "access_token": token,
                    },
                )
                wait_container(item["id"], token, f"slide {i:02d}")
                print(f"   Slide {i:02d}: {item['id']}")
                children.append(item["id"])

            print("🧩 Criando container do carrossel...")
            creation = graph_post(
                f"{user_id}/threads",
                {
                    "media_type": "CAROUSEL",
                    "children": ",".join(children),
                    "text": text,
                    "access_token": token,
                },
            )
            container_id = creation["id"]

        wait_container(container_id, token, "container")
        print("📤 Publicando...")
        published = graph_post(
            f"{user_id}/threads_publish",
            {"creation_id": container_id, "access_token": token},
        )
        media_id = published["id"]
        info = graph_get(media_id, {"fields": "permalink", "access_token": token})
        print("\n✅ Publicado com sucesso!")
        print(f"   Media ID: {media_id}")
        print(f"   Ver em: {info.get('permalink', '(permalink indisponível)')}")
    except urllib.error.HTTPError as e:
        print(f"❌ Erro HTTP {e.code}: {e.read().decode(errors='replace')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
