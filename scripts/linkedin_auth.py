#!/usr/bin/env python3
"""
LinkedIn OAuth 2.0 — one-time auth flow.
Saves the access token to .env for use by linkedin_post.py.

Usage:
    python3 scripts/linkedin_auth.py
"""

import os
import re
import sys
import ssl
import urllib.parse
import urllib.request
import json
import http.server
import threading
import webbrowser
from pathlib import Path

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = ssl.create_default_context()

ROOT = Path(__file__).parent.parent
ENV_FILE = ROOT / ".env"


def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


def save_token(token: str):
    content = ENV_FILE.read_text()
    # Garante que cada chave começa numa linha nova
    content = content.rstrip("\n") + "\n"
    if re.search(r"^#?\s*LINKEDIN_ACCESS_TOKEN=", content, re.MULTILINE):
        content = re.sub(r"#?\s*LINKEDIN_ACCESS_TOKEN=.*", f"LINKEDIN_ACCESS_TOKEN={token}", content)
    else:
        content += f"LINKEDIN_ACCESS_TOKEN={token}\n"
    ENV_FILE.write_text(content)
    print(f"✅ Token salvo em .env")


def exchange_code(code: str, env: dict) -> str:
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": env["LINKEDIN_REDIRECT_URI"],
        "client_id": env["LINKEDIN_CLIENT_ID"],
        "client_secret": env["LINKEDIN_CLIENT_SECRET"],
    }).encode()

    req = urllib.request.Request(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, context=SSL_CONTEXT) as resp:
        result = json.loads(resp.read())
    return result["access_token"]


def main():
    env = load_env()
    required = ["LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET", "LINKEDIN_REDIRECT_URI"]
    missing = [k for k in required if not env.get(k)]
    if missing:
        print(f"❌ Faltam variáveis no .env: {', '.join(missing)}")
        sys.exit(1)

    auth_code = [None]
    shutdown_event = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # silencia logs do servidor

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            if "code" in params:
                auth_code[0] = params["code"][0]
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"<h2>Autenticado! Pode fechar esta aba.</h2>")
                threading.Thread(target=shutdown_event.set).start()
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Erro: code nao encontrado.")

    server = http.server.HTTPServer(("localhost", 8080), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    scope = "openid profile w_member_social"
    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization?"
        + urllib.parse.urlencode({
            "response_type": "code",
            "client_id": env["LINKEDIN_CLIENT_ID"],
            "redirect_uri": env["LINKEDIN_REDIRECT_URI"],
            "scope": scope,
        })
    )

    print(f"\n🔗 Abrindo navegador para autorização...\n{auth_url}\n")
    webbrowser.open(auth_url)

    print("⏳ Aguardando callback...")
    shutdown_event.wait(timeout=120)
    server.shutdown()

    if not auth_code[0]:
        print("❌ Timeout: nenhum código recebido.")
        sys.exit(1)

    print("🔄 Trocando código por token...")
    token = exchange_code(auth_code[0], env)
    save_token(token)
    print("\n✅ Pronto! Agora rode: python3 scripts/linkedin_post.py")


if __name__ == "__main__":
    main()
