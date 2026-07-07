#!/usr/bin/env python3
"""
Configura credenciais para publicar no Threads via Threads API.

Pré-requisito (uma vez, no painel developers.facebook.com):
    1. Adicione o caso de uso "Access the Threads API" a um app Meta
       (ou crie um app novo do tipo Threads).
    2. Em "Threads API > Settings", anote o Threads App ID e o App Secret
       e salve no .env como THREADS_APP_ID e THREADS_APP_SECRET.
    3. Registre a Redirect Callback URL (padrão deste script:
       https://bolivaralencastro.com.br/).
    4. Em "App Roles", adicione a sua conta do Threads como Threads Tester
       e aceite o convite em threads.net > Configurações > Conta >
       Permissões do site.

Fluxo deste script:
    1. Imprime a URL de autorização; abra no navegador e aprove.
    2. O navegador redireciona para a callback com ?code=... na URL.
    3. Cole a URL completa (ou só o code) de volta aqui.
    4. O script troca code -> token curto -> token de 60 dias e salva
       THREADS_ACCESS_TOKEN e THREADS_USER_ID no .env.

Usage:
    python3 scripts/threads_auth.py
    python3 scripts/threads_auth.py --code AQB...
"""

from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
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
AUTH_HOST = "https://threads.net"
GRAPH_HOST = "https://graph.threads.net"
DEFAULT_REDIRECT = "https://bolivaralencastro.com.br/"
SCOPES = "threads_basic,threads_content_publish"


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


def http_get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30, context=SSL_CONTEXT) as r:
        return json.loads(r.read())


def http_post(url: str, payload: dict) -> dict:
    data = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=30, context=SSL_CONTEXT) as r:
        return json.loads(r.read())


def extract_code(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("http"):
        query = urllib.parse.urlparse(raw).query
        params = urllib.parse.parse_qs(query)
        codes = params.get("code")
        if not codes:
            raise ValueError("URL colada não contém ?code=...")
        raw = codes[0]
    # O redirect do Threads anexa #_ ao final do code
    return raw.split("#")[0].strip()


def main():
    parser = argparse.ArgumentParser(description="Configura token da Threads API")
    parser.add_argument("--code", help="Authorization code (ou cole a URL de redirect inteira)")
    parser.add_argument("--redirect-uri", default=DEFAULT_REDIRECT, help="Redirect URI registrada no app")
    args = parser.parse_args()

    env = load_env()
    app_id = env.get("THREADS_APP_ID", "").strip()
    app_secret = env.get("THREADS_APP_SECRET", "").strip()
    if not app_id or not app_secret:
        print("❌ Configure THREADS_APP_ID e THREADS_APP_SECRET no .env (ver docstring).")
        sys.exit(1)

    raw = args.code
    if not raw:
        auth_url = f"{AUTH_HOST}/oauth/authorize?" + urllib.parse.urlencode(
            {
                "client_id": app_id,
                "redirect_uri": args.redirect_uri,
                "scope": SCOPES,
                "response_type": "code",
            }
        )
        print("🔗 Abra no navegador, aprove e copie a URL de redirect:\n")
        print(f"   {auth_url}\n")
        raw = input("Cole aqui a URL de redirect (ou só o code): ")

    try:
        code = extract_code(raw)

        print("🔄 Trocando code por token curto...")
        short = http_post(
            f"{GRAPH_HOST}/oauth/access_token",
            {
                "client_id": app_id,
                "client_secret": app_secret,
                "grant_type": "authorization_code",
                "redirect_uri": args.redirect_uri,
                "code": code,
            },
        )
        short_token = short["access_token"]

        print("🔄 Trocando por token de longa duração (60 dias)...")
        long_data = http_get(
            f"{GRAPH_HOST}/access_token?"
            + urllib.parse.urlencode(
                {
                    "grant_type": "th_exchange_token",
                    "client_secret": app_secret,
                    "access_token": short_token,
                }
            )
        )
        long_token = long_data["access_token"]
        days = int(long_data.get("expires_in", 0)) // 86400

        me = http_get(
            f"{GRAPH_HOST}/v1.0/me?"
            + urllib.parse.urlencode({"fields": "id,username", "access_token": long_token})
        )
    except urllib.error.HTTPError as e:
        print(f"❌ Erro HTTP {e.code}: {e.read().decode(errors='replace')}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ {e}")
        sys.exit(1)

    save_to_env("THREADS_ACCESS_TOKEN", long_token)
    save_to_env("THREADS_USER_ID", me["id"])

    print("\n✅ Credenciais do Threads configuradas.")
    print(f"   Conta: @{me.get('username')} ({me['id']})")
    print(f"   Token válido por ~{days} dias (renove com refresh_meta_tokens.py)")


if __name__ == "__main__":
    main()
