#!/usr/bin/env python3
"""
Publica o último post do blog no Instagram.

Detecta automaticamente o post mais recente (por data no HTML),
formata a legenda e publica via Instagram Graph API.
A imagem usada deve ser JPG/PNG em URL pública (Instagram Graph API não
aceita WEBP no image_url).

Pré-requisitos:
    - Conta Instagram Business ou Creator
    - INSTAGRAM_ACCESS_TOKEN e INSTAGRAM_USER_ID no .env
    - O site deve estar publicado (a imagem precisa de URL pública)
    - Gere o token via Facebook Login/Graph API Explorer ou execute instagram_auth.py

Usage:
    python3 scripts/instagram_post.py              # publica último post
    python3 scripts/instagram_post.py --dry-run    # mostra sem publicar
    python3 scripts/instagram_post.py --slug meu-post
"""

import argparse
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = ssl.create_default_context()

ROOT = Path(__file__).parent.parent
BLOG_DIR = ROOT / "blog"
ENV_FILE = ROOT / ".env"
BASE_URL = "https://bolivaralencastro.com.br"
GRAPH_API = "https://graph.facebook.com/v25.0"


def load_env() -> dict:
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return {**env, **os.environ}


def extract_post_meta(html_path: Path) -> dict:
    content = html_path.read_text(encoding="utf-8")

    title_m = re.search(r'<h1[^>]*>(.*?)</h1>', content, re.DOTALL)
    title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip() if title_m else ""

    desc_m = re.search(r'<meta name="description" content="([^"]+)"', content)
    description = desc_m.group(1).strip() if desc_m else ""

    date_m = re.search(r'<time[^>]+datetime="([^"]+)"', content)
    date_str = date_m.group(1) if date_m else "1970-01-01"

    slug = html_path.stem
    url = f"{BASE_URL}/blog/{slug}.html"

    # Imagem: Instagram Graph API exige JPG/PNG acessível por URL pública.
    # Usa raw.githubusercontent.com para evitar atraso de propagação no GitHub Pages.
    image_url = None
    for candidate in ["card.jpg", "cover.jpg", "card.png", "cover.png"]:
        local = ROOT / "assets" / "images" / "blog" / slug / candidate
        if local.exists():
            image_url = (
                "https://raw.githubusercontent.com/"
                f"bolivaralencastro/portfolio-bolivaralencastro/main/assets/images/blog/{slug}/{candidate}"
            )
            break

    return {
        "slug": slug,
        "title": title,
        "description": description,
        "date": date_str,
        "url": url,
        "image_url": image_url,
    }


def find_latest_post() -> Path:
    posts = list(BLOG_DIR.glob("*.html"))
    if not posts:
        print("❌ Nenhum post encontrado em blog/")
        sys.exit(1)

    def post_date(p: Path) -> str:
        content = p.read_text(encoding="utf-8")
        m = re.search(r'<time[^>]+datetime="([^"]+)"', content)
        return m.group(1) if m else "1970-01-01"

    return max(posts, key=post_date)


def format_caption(meta: dict) -> str:
    """Formata a legenda do post. Instagram não renderiza links clicáveis no caption — URL vai no final."""
    return (
        f"{meta['description']}\n\n"
        f"🔗 Link na bio ou acesse:\n"
        f"{meta['url']}\n\n"
        f"#blog #design #product #ai #tech"
    )


def create_media_container(user_id: str, token: str, image_url: str, caption: str) -> str:
    """Cria o container de mídia. Retorna o container_id."""
    params = urllib.parse.urlencode({
        "image_url": image_url,
        "caption": caption,
        "access_token": token,
    }).encode()

    req = urllib.request.Request(
        f"{GRAPH_API}/{user_id}/media",
        data=params,
        method="POST",
    )
    with urllib.request.urlopen(req, context=SSL_CONTEXT) as r:
        data = json.loads(r.read())

    container_id = data.get("id")
    if not container_id:
        raise ValueError(f"Container não criado: {data}")
    return container_id


def publish_container(user_id: str, token: str, container_id: str) -> str:
    """Publica o container. Retorna o media_id do post publicado."""
    params = urllib.parse.urlencode({
        "creation_id": container_id,
        "access_token": token,
    }).encode()

    req = urllib.request.Request(
        f"{GRAPH_API}/{user_id}/media_publish",
        data=params,
        method="POST",
    )
    with urllib.request.urlopen(req, context=SSL_CONTEXT) as r:
        data = json.loads(r.read())

    media_id = data.get("id")
    if not media_id:
        raise ValueError(f"Publicação falhou: {data}")
    return media_id


def get_media_permalink(media_id: str, token: str) -> str | None:
    """Obtém o permalink real do post publicado."""
    params = urllib.parse.urlencode({
        "fields": "permalink",
        "access_token": token,
    })
    req = urllib.request.Request(
        f"{GRAPH_API}/{media_id}?{params}",
        method="GET",
    )
    with urllib.request.urlopen(req, context=SSL_CONTEXT) as r:
        data = json.loads(r.read())
    return data.get("permalink")


def check_container_status(container_id: str, token: str) -> str:
    """Verifica se o container está pronto para publicar."""
    params = urllib.parse.urlencode({
        "fields": "status_code,status",
        "access_token": token,
    })
    req = urllib.request.Request(
        f"{GRAPH_API}/{container_id}?{params}",
        method="GET",
    )
    with urllib.request.urlopen(req, context=SSL_CONTEXT) as r:
        data = json.loads(r.read())
    return data.get("status_code", "UNKNOWN")


def main():
    parser = argparse.ArgumentParser(description="Publica post do blog no Instagram")
    parser.add_argument("--dry-run", action="store_true", help="Mostra sem publicar")
    parser.add_argument("--slug", help="Slug do post específico")
    args = parser.parse_args()

    env = load_env()
    token = env.get("INSTAGRAM_ACCESS_TOKEN", "").strip()
    user_id = env.get("INSTAGRAM_USER_ID", "").strip()

    if not token or not user_id:
        print("❌ Credenciais não encontradas no .env")
        print("   Execute primeiro: python3 scripts/instagram_auth.py")
        sys.exit(1)

    if args.slug:
        post_path = BLOG_DIR / f"{args.slug}.html"
        if not post_path.exists():
            print(f"❌ Post não encontrado: {post_path}")
            sys.exit(1)
    else:
        post_path = find_latest_post()

    meta = extract_post_meta(post_path)
    caption = format_caption(meta)

    print(f"\n📝 Post: {meta['title']}")
    print(f"📅 Data: {meta['date']}")
    print(f"🔗 URL:  {meta['url']}")
    if meta["image_url"]:
        print(f"🖼️  Imagem: {meta['image_url']}")
    else:
        print("❌ Nenhuma imagem encontrada — Instagram exige imagem.")
        print("   Gere card.jpg com: python3 scripts/generate_post_images.py blog/<slug>.html --only card")
        print("   (o script agora gera card.webp + card.jpg automaticamente)")
        sys.exit(1)

    print(f"\n--- Legenda ---\n{caption}\n---------------\n")

    if args.dry_run:
        print("🔍 Dry run: nada publicado.")
        return

    print("🔄 Criando container de mídia...")
    try:
        container_id = create_media_container(user_id, token, meta["image_url"], caption)
        print(f"   Container ID: {container_id}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"❌ Erro ao criar container HTTP {e.code}: {body}")
        if "190" in body:
            print("   Token expirado. Rode: python3 scripts/instagram_auth.py")
        sys.exit(1)

    # Aguarda container ficar pronto (pode levar alguns segundos)
    import time
    for attempt in range(10):
        status = check_container_status(container_id, token)
        if status == "FINISHED":
            break
        elif status == "ERROR":
            print(f"❌ Container com erro de processamento.")
            sys.exit(1)
        print(f"   Status: {status} — aguardando...")
        time.sleep(3)

    print("📤 Publicando...")
    try:
        media_id = publish_container(user_id, token, container_id)
        permalink = get_media_permalink(media_id, token)
        print(f"\n✅ Publicado com sucesso!")
        print(f"   Media ID: {media_id}")
        if permalink:
            print(f"   Ver em: {permalink}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"❌ Erro ao publicar HTTP {e.code}: {body}")
        sys.exit(1)


if __name__ == "__main__":
    main()
