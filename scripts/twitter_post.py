#!/usr/bin/env python3
"""
Publica conteudo do portfolio no X (Twitter).

Fluxos suportados:
    - blog: detecta o post mais recente ou publica um slug especifico
    - project: publica um projeto especifico ou o HTML mais recentemente modificado
    - page: publica uma pagina avulsa informando o path

Usage:
    python3 scripts/twitter_post.py
    python3 scripts/twitter_post.py --dry-run
    python3 scripts/twitter_post.py --slug meu-post
    python3 scripts/twitter_post.py --kind project --slug keeps-learning-konquest
    python3 scripts/twitter_post.py --path about.html
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html import unescape
from pathlib import Path

try:
    import certifi

    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except Exception:
    SSL_CONTEXT = ssl.create_default_context()

ROOT = Path(__file__).parent.parent
BLOG_DIR = ROOT / "blog"
PROJECTS_DIR = ROOT / "projects"
ENV_FILE = ROOT / ".env"
BASE_URL = "https://bolivaralencastro.com.br"
STATE_DIR = ROOT / ".social_publish_state"
TWITTER_STATE_FILE = STATE_DIR / "twitter_last_publish.json"

TWEET_CREATE_URL = "https://api.twitter.com/2/tweets"
MEDIA_UPLOAD_URL = "https://upload.twitter.com/1.1/media/upload.json"


def _pct_encode(value: str) -> str:
    return urllib.parse.quote(str(value), safe="~-._")


def _normalize_params(params: dict[str, str]) -> str:
    items: list[tuple[str, str]] = []
    for key, value in params.items():
        items.append((_pct_encode(key), _pct_encode(value)))
    items.sort()
    return "&".join(f"{k}={v}" for k, v in items)


def _signature_base_string(method: str, url: str, params: dict[str, str]) -> str:
    parsed = urllib.parse.urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    return "&".join(
        [
            _pct_encode(method.upper()),
            _pct_encode(base_url),
            _pct_encode(_normalize_params(params)),
        ]
    )


def _sign_hmac_sha1(base_string: str, consumer_secret: str, token_secret: str) -> str:
    key = f"{_pct_encode(consumer_secret)}&{_pct_encode(token_secret)}".encode("utf-8")
    digest = hmac.new(key, base_string.encode("utf-8"), hashlib.sha1).digest()
    return base64.b64encode(digest).decode("utf-8")


def _oauth_header(params: dict[str, str]) -> str:
    parts = []
    for key in sorted(params):
        if key.startswith("oauth_"):
            parts.append(f'{_pct_encode(key)}="{_pct_encode(params[key])}"')
    return "OAuth " + ", ".join(parts)


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return {**env, **os.environ}


def _extract_first(pattern: str, content: str) -> str:
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _strip_tags(text: str) -> str:
    return unescape(re.sub(r"<[^>]+>", "", text or "")).strip()


def _resolve_image_path(image_url: str) -> Path | None:
    if not image_url:
        return None
    if not image_url.startswith(BASE_URL):
        return None
    rel = image_url.removeprefix(BASE_URL).lstrip("/")
    if not rel:
        return None
    candidate = ROOT / rel
    return candidate if candidate.exists() else None


def extract_page_meta(html_path: Path, kind: str) -> dict[str, str | Path | None]:
    content = html_path.read_text(encoding="utf-8")

    title = _strip_tags(_extract_first(r"<h1[^>]*>(.*?)</h1>", content))
    if not title:
        title = _strip_tags(_extract_first(r"<title>(.*?)</title>", content))

    description = _extract_first(r'<meta\s+name="description"\s+content="([^"]+)"', content)
    canonical = _extract_first(r'<link\s+rel="canonical"\s+href="([^"]+)"', content)
    date_str = _extract_first(r'<time[^>]+datetime="([^"]+)"', content)
    image_url = _extract_first(r'<meta\s+property="og:image"\s+content="([^"]+)"', content)
    if not image_url:
        image_url = _extract_first(r'<meta\s+name="twitter:image"\s+content="([^"]+)"', content)

    rel_path = html_path.relative_to(ROOT).as_posix()
    slug = html_path.stem

    return {
        "kind": kind,
        "slug": slug,
        "title": title,
        "description": description,
        "date": date_str or "",
        "url": canonical or f"{BASE_URL}/{rel_path}",
        "image_path": _resolve_image_path(image_url),
        "path": rel_path,
    }


def _latest_by_date(directory: Path) -> Path:
    files = list(directory.glob("*.html"))
    if not files:
        print(f"Erro: nenhum HTML encontrado em {directory.relative_to(ROOT)}/")
        sys.exit(1)

    def sort_key(path: Path) -> str:
        content = path.read_text(encoding="utf-8")
        date_str = _extract_first(r'<time[^>]+datetime="([^"]+)"', content)
        return date_str or "1970-01-01"

    return max(files, key=sort_key)


def _latest_by_mtime(directory: Path) -> Path:
    files = list(directory.glob("*.html"))
    if not files:
        print(f"Erro: nenhum HTML encontrado em {directory.relative_to(ROOT)}/")
        sys.exit(1)
    return max(files, key=lambda path: path.stat().st_mtime)


def resolve_content_path(kind: str, slug: str | None, rel_path: str | None) -> tuple[Path, str]:
    if rel_path:
        target = (ROOT / rel_path).resolve()
        try:
            target.relative_to(ROOT)
        except ValueError:
            print(f"Erro: path fora do repositorio: {rel_path}")
            sys.exit(1)
        if not target.exists() or target.suffix != ".html":
            print(f"Erro: HTML nao encontrado: {rel_path}")
            sys.exit(1)

        resolved_kind = "page"
        if target.parent == BLOG_DIR:
            resolved_kind = "blog"
        elif target.parent == PROJECTS_DIR:
            resolved_kind = "project"
        return target, resolved_kind

    if kind == "blog":
        if slug:
            target = BLOG_DIR / f"{slug}.html"
            if not target.exists():
                print(f"Erro: post nao encontrado: {target}")
                sys.exit(1)
            return target, kind
        return _latest_by_date(BLOG_DIR), kind

    if kind == "project":
        if slug:
            target = PROJECTS_DIR / f"{slug}.html"
            if not target.exists():
                print(f"Erro: projeto nao encontrado: {target}")
                sys.exit(1)
            return target, kind
        return _latest_by_mtime(PROJECTS_DIR), kind

    if kind == "page":
        if not slug:
            print("Erro: use --path para paginas avulsas ou informe um arquivo HTML na raiz.")
            sys.exit(1)
        target = ROOT / f"{slug}.html"
        if not target.exists():
            print(f"Erro: pagina nao encontrada: {target.relative_to(ROOT)}")
            sys.exit(1)
        return target, kind

    # auto
    if slug:
        blog_target = BLOG_DIR / f"{slug}.html"
        if blog_target.exists():
            return blog_target, "blog"
        project_target = PROJECTS_DIR / f"{slug}.html"
        if project_target.exists():
            return project_target, "project"
        root_target = ROOT / f"{slug}.html"
        if root_target.exists():
            return root_target, "page"
        print(f"Erro: slug nao encontrado em blog/, projects/ ou raiz: {slug}")
        sys.exit(1)

    return _latest_by_date(BLOG_DIR), "blog"


def compose_tweet_text(meta: dict[str, str | Path | None], max_len: int = 280) -> str:
    kind = str(meta.get("kind", "")).strip()
    title = str(meta.get("title", "")).strip()
    description = re.sub(r"\s+", " ", str(meta.get("description", "")).strip())
    url = str(meta.get("url", "")).strip()

    if kind == "blog":
        primary = description or title
        return _trim_tweet(primary, url, max_len=max_len)

    if kind == "project":
        parts = []
        if title:
            parts.append(title)
        if description:
            parts.append(description)
        parts.append("Projeto no portfolio:")
        return _trim_tweet_blocks(parts, url, max_len=max_len)

    parts = []
    if title:
        parts.append(title)
    if description:
        parts.append(description)
    if not parts:
        return url
    return _trim_tweet_blocks(parts, url, max_len=max_len)


def _trim_tweet(text: str, url: str, max_len: int = 280) -> str:
    clean = re.sub(r"\s+", " ", (text or "").strip())
    if not clean:
        return url[:max_len]

    base = f"{clean}\n\n{url}"
    if len(base) <= max_len:
        return base

    reserved = len(url) + 2
    room = max_len - reserved
    if room <= 4:
        return url[:max_len]

    short = clean[: room - 3].rstrip()
    return f"{short}...\n\n{url}"


def _trim_tweet_blocks(blocks: list[str], url: str, max_len: int = 280) -> str:
    normalized = [re.sub(r"\s+", " ", block.strip()) for block in blocks if block and block.strip()]
    if not normalized:
        return url[:max_len]

    base = "\n".join(normalized) + f"\n\n{url}"
    if len(base) <= max_len:
        return base

    text = " ".join(normalized)
    return _trim_tweet(text, url, max_len=max_len)


def build_publish_signature(meta: dict[str, str | Path | None]) -> str:
    return "|".join(
        [
            str(meta.get("kind", "")),
            str(meta.get("path", "")),
            str(meta.get("url", "")),
            str(meta.get("description", "")),
        ]
    )


def is_recent_duplicate(signature: str, window_seconds: int = 3600) -> bool:
    if not TWITTER_STATE_FILE.exists():
        return False
    try:
        data = json.loads(TWITTER_STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False

    last_sig = data.get("signature", "")
    last_ts = int(data.get("timestamp", 0))
    if not last_sig or not last_ts:
        return False
    return last_sig == signature and (time.time() - last_ts) <= window_seconds


def save_publish_state(signature: str, tweet_id: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "signature": signature,
        "timestamp": int(time.time()),
        "tweet_id": tweet_id,
    }
    TWITTER_STATE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_oauth1_authorization(
    method: str,
    url: str,
    consumer_key: str,
    consumer_secret: str,
    access_token: str,
    access_token_secret: str,
    extra_signature_params: dict[str, str] | None = None,
) -> str:
    oauth_params = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": access_token,
        "oauth_version": "1.0",
    }

    signature_params = dict(oauth_params)
    if extra_signature_params:
        signature_params.update(extra_signature_params)

    base_string = _signature_base_string(method, url, signature_params)
    oauth_params["oauth_signature"] = _sign_hmac_sha1(base_string, consumer_secret, access_token_secret)
    return _oauth_header(oauth_params)


def upload_media(
    image_path: Path,
    consumer_key: str,
    consumer_secret: str,
    access_token: str,
    access_token_secret: str,
) -> str:
    boundary = "----PortfolioSocialBot" + secrets.token_hex(8)
    file_data = image_path.read_bytes()

    if image_path.suffix.lower() == ".png":
        mime_type = "image/png"
    elif image_path.suffix.lower() == ".webp":
        mime_type = "image/webp"
    else:
        mime_type = "image/jpeg"

    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="media"; filename="{image_path.name}"\r\n'
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode("utf-8")
    tail = f"\r\n--{boundary}--\r\n".encode("utf-8")
    body = head + file_data + tail

    auth = build_oauth1_authorization(
        method="POST",
        url=MEDIA_UPLOAD_URL,
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
    )

    req = urllib.request.Request(
        MEDIA_UPLOAD_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": auth,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "portfolio-social-bot/1.0",
        },
    )

    with urllib.request.urlopen(req, timeout=60, context=SSL_CONTEXT) as resp:
        result = json.loads(resp.read())

    media_id = result.get("media_id_string")
    if not media_id:
        raise ValueError(f"Upload de media falhou: {result}")
    return media_id


def create_tweet(
    text: str,
    media_id: str | None,
    consumer_key: str,
    consumer_secret: str,
    access_token: str,
    access_token_secret: str,
) -> dict:
    payload: dict = {"text": text}
    if media_id:
        payload["media"] = {"media_ids": [media_id]}

    body_bytes = json.dumps(payload).encode("utf-8")

    auth = build_oauth1_authorization(
        method="POST",
        url=TWEET_CREATE_URL,
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
    )

    req = urllib.request.Request(
        TWEET_CREATE_URL,
        data=body_bytes,
        method="POST",
        headers={
            "Authorization": auth,
            "Content-Type": "application/json",
            "User-Agent": "portfolio-social-bot/1.0",
        },
    )

    with urllib.request.urlopen(req, timeout=30, context=SSL_CONTEXT) as resp:
        return json.loads(resp.read())


def main() -> None:
    parser = argparse.ArgumentParser(description="Publica conteudo do portfolio no X (Twitter)")
    parser.add_argument("--dry-run", action="store_true", help="Mostra o texto sem publicar")
    parser.add_argument(
        "--kind",
        choices=["auto", "blog", "project", "page"],
        default="auto",
        help="Tipo de conteudo a publicar",
    )
    parser.add_argument("--slug", help="Slug do blog/projeto ou nome do HTML da raiz sem extensao")
    parser.add_argument("--path", help="Path relativo do HTML, ex: about.html ou projects/keeps-learning-konquest.html")
    args = parser.parse_args()

    env = load_env()
    api_key = env.get("X_API_KEY", "").strip()
    api_secret = env.get("X_API_SECRET", "").strip()
    access_token = env.get("X_ACCESS_TOKEN", "").strip()
    access_token_secret = env.get("X_ACCESS_TOKEN_SECRET", "").strip()
    username = env.get("X_USERNAME", "").strip()

    if not (api_key and api_secret and access_token and access_token_secret):
        print("Erro: faltam credenciais. Rode primeiro: python3 scripts/twitter_auth.py")
        sys.exit(1)

    html_path, resolved_kind = resolve_content_path(args.kind, args.slug, args.path)
    meta = extract_page_meta(html_path, resolved_kind)
    tweet_text = compose_tweet_text(meta)

    print(f"\nTipo: {meta['kind']}")
    print(f"Arquivo: {meta['path']}")
    print(f"Titulo: {meta['title']}")
    if meta["date"]:
        print(f"Data: {meta['date']}")
    print(f"URL:  {meta['url']}")
    print(f"Conta X: @{username}" if username else "Conta X: (usuario nao identificado no .env)")
    if meta["image_path"]:
        print(f"Imagem: {meta['image_path']}")
    else:
        print("Imagem: nenhuma (sera publicado sem media)")

    print("\n--- Tweet ---")
    print(tweet_text)
    print("------------")
    print(f"Tamanho: {len(tweet_text)} caracteres")

    if args.dry_run:
        print("\nDry run: nada foi publicado.")
        return

    signature = build_publish_signature(meta)
    if is_recent_duplicate(signature):
        print("\nPublicacao bloqueada: conteudo identico ja foi publicado recentemente.")
        print("Use --dry-run para revisar ou aguarde a janela de seguranca expirar.")
        sys.exit(1)

    media_id = None
    try:
        if meta["image_path"]:
            print("\nEnviando imagem...")
            media_id = upload_media(
                image_path=Path(meta["image_path"]),
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_token_secret,
            )
            print(f"Media ID: {media_id}")

        print("Publicando tweet...")
        result = create_tweet(
            text=tweet_text,
            media_id=media_id,
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
        )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        print(f"Erro HTTP {exc.code}: {body}")
        sys.exit(1)
    except Exception as exc:
        print(f"Erro: {exc}")
        sys.exit(1)

    tweet_id = str(result.get("id_str") or result.get("id") or "")
    if not tweet_id:
        print(f"Erro: resposta inesperada da API: {result}")
        sys.exit(1)

    save_publish_state(signature, tweet_id)
    link = f"https://x.com/{username}/status/{tweet_id}" if username else f"https://x.com/i/web/status/{tweet_id}"

    print("\nPublicado com sucesso.")
    print(f"Tweet ID: {tweet_id}")
    print(f"Ver em: {link}")


if __name__ == "__main__":
    main()
