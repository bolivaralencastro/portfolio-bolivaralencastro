#!/usr/bin/env python3
"""
Configura credenciais para publicar no Instagram via Instagram Graph API.

Fluxo usado:
    1. Gere um User Access Token no Graph API Explorer com:
       business_management, instagram_basic, instagram_content_publish,
       instagram_manage_insights, pages_read_engagement, pages_show_list
    2. Execute este script passando o token curto.
    3. O script troca por token de longa duração, encontra a página conectada
       ao Instagram e salva no .env:
       INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_USER_ID e INSTAGRAM_PAGE_ID.

Usage:
    python3 scripts/instagram_auth.py --short-token EAAB...

Também é possível colar o token via stdin:
    pbpaste | python3 scripts/instagram_auth.py
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
ENV_FILE = ROOT / ".env"
GRAPH_API = "https://graph.facebook.com/v25.0"
DEFAULT_USERNAME = "bolivar.alencastro"


def load_env() -> dict:
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return {**env, **os.environ}


def save_to_env(key: str, value: str):
    content = ENV_FILE.read_text() if ENV_FILE.exists() else ""
    pattern = rf"^#?\s*{re.escape(key)}=.*$"
    new_line = f"{key}={value}"
    if re.search(pattern, content, flags=re.MULTILINE):
        content = re.sub(pattern, new_line, content, flags=re.MULTILINE)
    else:
        content = content.rstrip("\n") + f"\n{new_line}\n"
    ENV_FILE.write_text(content)
    print(f"   ✅ {key} salvo no .env")


def graph_get(path: str, params: dict) -> dict:
    url = f"{GRAPH_API}/{path.lstrip('/')}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=30, context=SSL_CONTEXT) as r:
        return json.loads(r.read())


def exchange_for_long_lived_user_token(short_token: str, app_id: str, app_secret: str) -> str:
    data = graph_get("/oauth/access_token", {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": short_token,
    })
    return data["access_token"]


def find_instagram_account(user_token: str, username: str) -> tuple[str, str, str, str]:
    data = graph_get("/me/accounts", {
        "fields": "id,name,access_token,instagram_business_account{id,username}",
        "access_token": user_token,
    })

    for page in data.get("data", []):
        ig = page.get("instagram_business_account") or {}
        if ig.get("username") == username:
            return page["id"], page["name"], page["access_token"], ig["id"]

    available = [
        {
            "page": page.get("name"),
            "instagram": (page.get("instagram_business_account") or {}).get("username"),
        }
        for page in data.get("data", [])
    ]
    raise ValueError(f"@{username} não encontrado em /me/accounts. Contas disponíveis: {available}")


def main():
    parser = argparse.ArgumentParser(description="Configura token do Instagram Graph API")
    parser.add_argument("--short-token", help="User Access Token curto gerado no Graph API Explorer")
    parser.add_argument("--username", default=DEFAULT_USERNAME, help="Username do Instagram conectado à página")
    args = parser.parse_args()

    env = load_env()
    app_id = env.get("INSTAGRAM_APP_ID", "").strip()
    app_secret = env.get("INSTAGRAM_APP_SECRET", "").strip()

    if not app_id or not app_secret:
        print("❌ Configure INSTAGRAM_APP_ID e INSTAGRAM_APP_SECRET no .env")
        sys.exit(1)

    short_token = (args.short_token or sys.stdin.read()).strip()
    if not short_token:
        print("❌ Informe o token curto via --short-token ou stdin.")
        sys.exit(1)

    try:
        print("🔄 Trocando por token de longa duração...")
        long_user_token = exchange_for_long_lived_user_token(short_token, app_id, app_secret)

        print(f"🔎 Procurando Instagram @{args.username} em /me/accounts...")
        page_id, page_name, page_token, ig_user_id = find_instagram_account(long_user_token, args.username)

        check = graph_get(f"/{ig_user_id}", {
            "fields": "id,username",
            "access_token": page_token,
        })
        if check.get("username") != args.username:
            raise ValueError(f"Conta inesperada retornada pela API: {check}")

    except urllib.error.HTTPError as e:
        print(f"❌ Erro HTTP {e.code}: {e.read().decode(errors='replace')}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ {e}")
        sys.exit(1)

    save_to_env("INSTAGRAM_ACCESS_TOKEN", page_token)
    save_to_env("INSTAGRAM_USER_ID", ig_user_id)
    save_to_env("INSTAGRAM_PAGE_ID", page_id)

    print("\n✅ Credenciais configuradas.")
    print(f"   Página: {page_name} ({page_id})")
    print(f"   Instagram: @{args.username} ({ig_user_id})")


if __name__ == "__main__":
    main()
