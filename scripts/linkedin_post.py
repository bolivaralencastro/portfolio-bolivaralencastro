#!/usr/bin/env python3
"""
Publica o último post do blog no LinkedIn.

Detecta automaticamente o post mais recente (por data no HTML),
formata o texto e publica via LinkedIn REST Posts API (versão 202503).
Se existir assets/images/blog/<slug>/card.webp, faz upload e publica com imagem.

Usage:
    python3 scripts/linkedin_post.py              # publica último post
    python3 scripts/linkedin_post.py --dry-run    # mostra o texto sem publicar
    python3 scripts/linkedin_post.py --slug meu-post  # publica post específico
"""

import os
import sys
import json
import re
import ssl
import time
import argparse
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from datetime import datetime

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = ssl.create_default_context()

ROOT = Path(__file__).parent.parent
BLOG_DIR = ROOT / "blog"
ENV_FILE = ROOT / ".env"
BASE_URL = "https://bolivaralencastro.com.br"
STATE_DIR = ROOT / ".social_publish_state"
LINKEDIN_STATE_FILE = STATE_DIR / "linkedin_last_publish.json"


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

    title_match = re.search(r'<h1[^>]*>(.*?)</h1>', content, re.DOTALL)
    title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip() if title_match else ""

    desc_match = re.search(r'<meta name="description" content="([^"]+)"', content)
    description = desc_match.group(1).strip() if desc_match else ""

    date_match = re.search(r'<time[^>]+datetime="([^"]+)"', content)
    date_str = date_match.group(1) if date_match else "1970-01-01"

    slug = html_path.stem
    url = f"{BASE_URL}/blog/{slug}.html"

    # Procura card.webp ou cover.webp na pasta de assets do post
    image_path = None
    for candidate in ["card.webp", "cover.webp", "card.jpg", "card.png"]:
        p = ROOT / "assets" / "images" / "blog" / slug / candidate
        if p.exists():
            image_path = p
            break

    return {
        "slug": slug,
        "title": title,
        "description": description,
        "date": date_str,
        "url": url,
        "image_path": image_path,
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


def get_member_urn(token: str, env: dict) -> str:
    """Retorna o URN do membro. Prioriza LINKEDIN_PERSON_URN do .env."""
    urn = env.get("LINKEDIN_PERSON_URN", "").strip()
    if urn:
        return urn

    # Fallback: tenta /v2/me (requer r_liteprofile)
    req = urllib.request.Request(
        "https://api.linkedin.com/v2/me",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Restli-Protocol-Version": "2.0.0",
        },
    )
    try:
        with urllib.request.urlopen(req, context=SSL_CONTEXT) as resp:
            data = json.loads(resp.read())
        member_id = data.get("id", "")
        if member_id:
            return f"urn:li:person:{member_id}"
    except urllib.error.HTTPError:
        pass

    # Fallback: /v2/userinfo (requer openid)
    req2 = urllib.request.Request(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req2, context=SSL_CONTEXT) as resp:
        data = json.loads(resp.read())
    sub = data.get("sub", "")
    if not sub:
        raise ValueError(
            "Não foi possível obter o URN do membro.\n"
            "Adicione LINKEDIN_PERSON_URN=urn:li:person:SEU_ID ao .env"
        )
    return f"urn:li:person:{sub}"


LI_VERSION = "202503"
LI_API = "https://api.linkedin.com/rest"


def _api_headers(token: str, extra: dict | None = None) -> dict:
    h = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "LinkedIn-Version": LI_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
    }
    if extra:
        h.update(extra)
    return h


def register_image_upload(token: str, author_urn: str) -> tuple[str, str]:
    """Registra o upload de imagem e retorna (uploadUrl, image_urn)."""
    payload = {
        "initializeUploadRequest": {
            "owner": author_urn,
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{LI_API}/images?action=initializeUpload",
        data=data,
        headers=_api_headers(token),
        method="POST",
    )
    with urllib.request.urlopen(req, context=SSL_CONTEXT) as resp:
        result = json.loads(resp.read())

    upload_url = result["value"]["uploadUrl"]
    image_urn = result["value"]["image"]
    return upload_url, image_urn


def upload_image(upload_url: str, image_path: Path, token: str):
    """Faz upload binário da imagem para a URL fornecida pelo LinkedIn."""
    mime = "image/webp" if image_path.suffix == ".webp" else "image/jpeg"
    image_data = image_path.read_bytes()
    req = urllib.request.Request(
        upload_url,
        data=image_data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": mime,
        },
        method="PUT",
    )
    with urllib.request.urlopen(req, context=SSL_CONTEXT) as resp:
        resp.read()


def format_post_text(meta: dict) -> str:
    return (
        f"{meta['description']}\n\n"
        f"Novo post no blog 👇\n"
        f"{meta['url']}"
    )


def build_publish_signature(author_urn: str, meta: dict) -> str:
    """Assinatura estável para detectar repost acidental do mesmo conteúdo."""
    return "|".join(
        [
            author_urn,
            meta.get("slug", ""),
            meta.get("url", ""),
            meta.get("description", ""),
        ]
    )


def is_recent_duplicate(signature: str, window_seconds: int = 3600) -> bool:
    """Retorna True se o último publish local tiver a mesma assinatura em janela recente."""
    if not LINKEDIN_STATE_FILE.exists():
        return False
    try:
        data = json.loads(LINKEDIN_STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False

    last_sig = data.get("signature", "")
    last_ts = int(data.get("timestamp", 0))
    if not last_sig or not last_ts:
        return False

    return last_sig == signature and (time.time() - last_ts) <= window_seconds


def save_publish_state(signature: str, share_urn: str):
    """Salva estado local do último publish para evitar duplicações acidentais."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "signature": signature,
        "timestamp": int(time.time()),
        "share_urn": share_urn,
    }
    LINKEDIN_STATE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def publish_post(token: str, author_urn: str, meta: dict, image_urn: str | None = None) -> str:
    """Publica o post e retorna o URN do share criado."""
    payload: dict = {
        "author": author_urn,
        "commentary": format_post_text(meta),
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    if image_urn:
        # Publica com imagem
        payload["content"] = {"media": {"id": image_urn}}
    else:
        # Publica com card de artigo (link preview automático)
        payload["content"] = {
            "article": {
                "source": meta["url"],
                "title": meta["title"],
                "description": meta["description"],
            }
        }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{LI_API}/posts",
        data=data,
        headers=_api_headers(token),
        method="POST",
    )
    with urllib.request.urlopen(req, context=SSL_CONTEXT) as resp:
        resp.read()
        share_urn = resp.headers.get("x-restli-id", "")
    return share_urn


def main():
    parser = argparse.ArgumentParser(description="Publica post do blog no LinkedIn")
    parser.add_argument("--dry-run", action="store_true", help="Mostra o texto sem publicar")
    parser.add_argument("--slug", help="Slug do post específico (ex: meu-post)")
    parser.add_argument(
        "--allow-duplicate",
        action="store_true",
        help="Permite publicar conteúdo idêntico ao último post recente",
    )
    args = parser.parse_args()

    env = load_env()
    token = env.get("LINKEDIN_ACCESS_TOKEN", "").strip()

    if not token:
        print("❌ LINKEDIN_ACCESS_TOKEN não encontrado no .env")
        print("   Execute primeiro: python3 scripts/linkedin_auth.py")
        sys.exit(1)

    if args.slug:
        post_path = BLOG_DIR / f"{args.slug}.html"
        if not post_path.exists():
            print(f"❌ Post não encontrado: {post_path}")
            sys.exit(1)
    else:
        post_path = find_latest_post()

    meta = extract_post_meta(post_path)

    print(f"\n📝 Post: {meta['title']}")
    print(f"📅 Data: {meta['date']}")
    print(f"🔗 URL:  {meta['url']}")
    if meta["image_path"]:
        print(f"🖼️  Imagem: {meta['image_path'].relative_to(ROOT)}")
    else:
        print(f"🖼️  Imagem: não encontrada (usará card de link)")
    print(f"\n--- Texto da publicação ---\n{format_post_text(meta)}\n---------------------------\n")

    if args.dry_run:
        print("🔍 Dry run: nada publicado.")
        return

    print("🔄 Obtendo URN do membro...")
    try:
        author_urn = get_member_urn(token, env)
    except Exception as e:
        print(f"❌ Erro ao obter URN: {e}")
        print("   O token pode ter expirado. Rode: python3 scripts/linkedin_auth.py")
        sys.exit(1)

    print(f"👤 Author: {author_urn}")

    signature = build_publish_signature(author_urn, meta)
    if not args.allow_duplicate and is_recent_duplicate(signature):
        print("⚠️  Publicação bloqueada para evitar duplicata acidental.")
        print("   Use --allow-duplicate se quiser publicar o mesmo conteúdo novamente.")
        sys.exit(1)

    image_urn = None
    if meta["image_path"]:
        print("🖼️  Registrando upload de imagem...")
        try:
            upload_url, image_urn = register_image_upload(token, author_urn)
            print("⬆️  Enviando imagem...")
            upload_image(upload_url, meta["image_path"], token)
            print(f"✅ Imagem enviada: {image_urn}")
        except Exception as e:
            print(f"⚠️  Falha no upload da imagem ({e}). Publicando como artigo...")
            image_urn = None

    print("📤 Publicando...")
    try:
        share_urn = publish_post(token, author_urn, meta, image_urn)
        save_publish_state(signature, share_urn)
        print(f"\n✅ Publicado com sucesso!")
        if share_urn:
            print(f"   URN: {share_urn}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"❌ Erro HTTP {e.code}: {body}")
        if e.code == 401:
            print("   Token expirado. Rode: python3 scripts/linkedin_auth.py")
        sys.exit(1)


if __name__ == "__main__":
    main()
