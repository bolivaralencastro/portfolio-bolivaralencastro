#!/usr/bin/env python3
"""
Publica um carrossel do Instagram via Graph API.

Uso:
    python3 scripts/instagram_carousel_post.py assets/images/social/instagram/veganismo-horizonte-moral --dry-run
    python3 scripts/instagram_carousel_post.py assets/images/social/instagram/veganismo-horizonte-moral --ref <git-ref>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import subprocess
import sys
import time
from email.utils import parsedate_to_datetime
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
GRAPH_API = "https://graph.facebook.com/v25.0"
DEFAULT_REPO = "bolivaralencastro/portfolio-bolivaralencastro"


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return {**env, **os.environ}


def detect_git_ref() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()


def collect_slide_paths(carousel_dir: Path) -> list[Path]:
    pattern = re.compile(r"^slide-\d{2}\.(jpg|png)$", re.IGNORECASE)
    slides = sorted(path for path in carousel_dir.iterdir() if path.is_file() and pattern.match(path.name))
    if not slides:
        raise FileNotFoundError(f"Nenhum slide encontrado em {carousel_dir}")
    return slides


def read_caption(carousel_dir: Path) -> str:
    caption_path = carousel_dir / "caption.txt"
    if not caption_path.exists():
        raise FileNotFoundError(f"Legenda não encontrada: {caption_path}")
    return caption_path.read_text(encoding="utf-8").strip()


def build_raw_github_url(repo: str, ref: str, path: Path) -> str:
    relative = path.relative_to(ROOT).as_posix()
    return f"https://raw.githubusercontent.com/{repo}/{ref}/{relative}"


def retry_delay(error: urllib.error.HTTPError, attempt: int) -> float | None:
    if error.code in {429, 500, 502, 503, 504}:
        retry_after = error.headers.get("Retry-After")
        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                try:
                    target = parsedate_to_datetime(retry_after).timestamp()
                    return max(1.0, target - time.time())
                except Exception:
                    pass
        return min(30.0, 2.0 * attempt)
    return None


def request_json(url: str, method: str = "GET", payload: dict[str, str] | None = None, retries: int = 5) -> dict:
    data = None
    if payload is not None:
        data = urllib.parse.urlencode(payload).encode()

    for attempt in range(1, retries + 1):
        req = urllib.request.Request(url, data=data, method=method)
        try:
            with urllib.request.urlopen(req, context=SSL_CONTEXT) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            delay = retry_delay(error, attempt)
            if delay is None or attempt >= retries:
                raise
            body = error.read().decode(errors="replace")
            print(f"   HTTP {error.code} na tentativa {attempt}/{retries}; retry em {delay:.0f}s: {body}")
            time.sleep(delay)

    raise RuntimeError("Falha inesperada ao requisitar JSON")


def create_image_container(user_id: str, token: str, image_url: str) -> str:
    data = request_json(
        f"{GRAPH_API}/{user_id}/media",
        method="POST",
        payload={
            "image_url": image_url,
            "is_carousel_item": "true",
            "access_token": token,
        },
    )
    container_id = data.get("id")
    if not container_id:
        raise RuntimeError(f"Falha ao criar container do slide: {data}")
    return container_id


def create_carousel_container(user_id: str, token: str, children: list[str], caption: str) -> str:
    data = request_json(
        f"{GRAPH_API}/{user_id}/media",
        method="POST",
        payload={
            "media_type": "CAROUSEL",
            "children": ",".join(children),
            "caption": caption,
            "access_token": token,
        },
    )
    container_id = data.get("id")
    if not container_id:
        raise RuntimeError(f"Falha ao criar container do carrossel: {data}")
    return container_id


def check_container_status(container_id: str, token: str) -> str:
    data = request_json(
        f"{GRAPH_API}/{container_id}?{urllib.parse.urlencode({'fields': 'status_code,status', 'access_token': token})}"
    )
    return data.get("status_code", "UNKNOWN")


def wait_until_finished(container_id: str, token: str, label: str) -> None:
    for attempt in range(15):
        status = check_container_status(container_id, token)
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"{label} ficou com status ERROR")
        print(f"   {label}: {status} ({attempt + 1}/15)")
        time.sleep(3)
    raise RuntimeError(f"{label} não finalizou a tempo")


def publish_container(user_id: str, token: str, container_id: str) -> str:
    data = request_json(
        f"{GRAPH_API}/{user_id}/media_publish",
        method="POST",
        payload={
            "creation_id": container_id,
            "access_token": token,
        },
    )
    media_id = data.get("id")
    if not media_id:
        raise RuntimeError(f"Falha ao publicar container: {data}")
    return media_id


def get_media_permalink(media_id: str, token: str) -> str | None:
    data = request_json(
        f"{GRAPH_API}/{media_id}?{urllib.parse.urlencode({'fields': 'permalink', 'access_token': token})}"
    )
    return data.get("permalink")


def verify_public_urls(urls: list[str]) -> None:
    for url in urls:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, context=SSL_CONTEXT) as response:
            if response.status >= 400:
                raise RuntimeError(f"URL pública inválida: {url}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Publica um carrossel no Instagram")
    parser.add_argument("carousel_dir", help="Diretório com slide-*.jpg e caption.txt")
    parser.add_argument("--ref", help="Git ref público para construir URLs raw do GitHub")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="owner/repo do GitHub")
    parser.add_argument("--dry-run", action="store_true", help="Só mostra o payload")
    parser.add_argument("--skip-url-check", action="store_true", help="Pula verificação HEAD das URLs")
    args = parser.parse_args()

    env = load_env()
    token = env.get("INSTAGRAM_ACCESS_TOKEN", "").strip()
    user_id = env.get("INSTAGRAM_USER_ID", "").strip()
    if not token or not user_id:
        print("❌ Credenciais de Instagram ausentes no .env")
        sys.exit(1)

    carousel_dir = (ROOT / args.carousel_dir).resolve() if not Path(args.carousel_dir).is_absolute() else Path(args.carousel_dir)
    slides = collect_slide_paths(carousel_dir)
    caption = read_caption(carousel_dir)
    ref = args.ref or detect_git_ref()
    slide_urls = [build_raw_github_url(args.repo, ref, slide) for slide in slides]

    print(f"\n🖼️  Carrossel: {carousel_dir.relative_to(ROOT)}")
    print(f"🔖 Ref público: {ref}")
    print(f"📚 Slides: {len(slides)}")
    for idx, url in enumerate(slide_urls, start=1):
        print(f"   {idx:02d}. {url}")
    print(f"\n--- Legenda ---\n{caption}\n---------------\n")

    if not args.skip_url_check:
        print("🔎 Verificando URLs públicas...")
        verify_public_urls(slide_urls)
        print("   URLs OK")

    if args.dry_run:
        print("🔍 Dry run: nada publicado.")
        return

    child_ids: list[str] = []
    try:
        print("🔄 Criando containers dos slides...")
        for idx, url in enumerate(slide_urls, start=1):
            child_id = create_image_container(user_id, token, url)
            print(f"   Slide {idx:02d}: {child_id}")
            wait_until_finished(child_id, token, f"slide {idx:02d}")
            child_ids.append(child_id)
            time.sleep(2)

        print("🧩 Criando container do carrossel...")
        carousel_id = create_carousel_container(user_id, token, child_ids, caption)
        print(f"   Carousel ID: {carousel_id}")
        wait_until_finished(carousel_id, token, "carrossel")

        print("📤 Publicando carrossel...")
        media_id = publish_container(user_id, token, carousel_id)
        permalink = get_media_permalink(media_id, token)
        print("\n✅ Publicado com sucesso!")
        print(f"   Media ID: {media_id}")
        if permalink:
            print(f"   Ver em: {permalink}")
    except urllib.error.HTTPError as error:
        body = error.read().decode()
        print(f"❌ Erro HTTP {error.code}: {body}")
        sys.exit(1)
    except Exception as error:  # pragma: no cover - script utilitário
        print(f"❌ {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
