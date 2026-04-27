#!/usr/bin/env python3
"""
Configura credenciais para publicar no X (Twitter) via API usando OAuth 1.0a user context.

Fluxo usado:
    1. Ler X_API_KEY e X_API_SECRET do .env
    2. Solicitar request token
    3. Abrir URL de autorizacao no navegador
    4. Receber callback local em localhost:8080
    5. Trocar por access token
    6. Salvar no .env: X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET, X_USER_ID, X_USERNAME

Usage:
    python3 scripts/twitter_auth.py
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import http.server
import os
import re
import secrets
import ssl
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

try:
    import certifi

    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except Exception:
    SSL_CONTEXT = ssl.create_default_context()

ROOT = Path(__file__).parent.parent
ENV_FILE = ROOT / ".env"
REQUEST_TOKEN_URL = "https://api.twitter.com/oauth/request_token"
AUTHORIZE_URL = "https://api.twitter.com/oauth/authorize"
ACCESS_TOKEN_URL = "https://api.twitter.com/oauth/access_token"
DEFAULT_CALLBACK_URL = "http://127.0.0.1:8080/callback"


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


def _sign_hmac_sha1(base_string: str, consumer_secret: str, token_secret: str = "") -> str:
    key = f"{_pct_encode(consumer_secret)}&{_pct_encode(token_secret)}".encode("utf-8")
    digest = hmac.new(key, base_string.encode("utf-8"), hashlib.sha1).digest()
    return base64.b64encode(digest).decode("utf-8")


def _oauth_header(params: dict[str, str]) -> str:
    pairs = []
    for key in sorted(params):
        if key.startswith("oauth_"):
            pairs.append(f'{_pct_encode(key)}="{_pct_encode(params[key])}"')
    return "OAuth " + ", ".join(pairs)


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return {**env, **os.environ}


def save_to_env(key: str, value: str) -> None:
    content = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else ""
    pattern = rf"^#?\s*{re.escape(key)}=.*$"
    new_line = f"{key}={value}"
    if re.search(pattern, content, flags=re.MULTILINE):
        content = re.sub(pattern, new_line, content, flags=re.MULTILINE)
    else:
        content = content.rstrip("\n") + f"\n{new_line}\n"
    ENV_FILE.write_text(content, encoding="utf-8")
    print(f"   Salvo {key} no .env")


def oauth1_post(
    url: str,
    consumer_key: str,
    consumer_secret: str,
    token: str = "",
    token_secret: str = "",
    body_params: dict[str, str] | None = None,
) -> str:
    body_params = body_params or {}
    oauth_params = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_version": "1.0",
    }
    if token:
        oauth_params["oauth_token"] = token

    signature_params = {**oauth_params, **body_params}
    base_string = _signature_base_string("POST", url, signature_params)
    oauth_params["oauth_signature"] = _sign_hmac_sha1(base_string, consumer_secret, token_secret)

    auth_header = _oauth_header(oauth_params)
    body_bytes = urllib.parse.urlencode(body_params).encode("utf-8") if body_params else b""

    req = urllib.request.Request(
        url,
        data=body_bytes,
        method="POST",
        headers={
            "Authorization": auth_header,
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "portfolio-social-bot/1.0",
        },
    )

    with urllib.request.urlopen(req, timeout=30, context=SSL_CONTEXT) as resp:
        return resp.read().decode("utf-8")


def parse_qs_response(payload: str) -> dict[str, str]:
    parsed = urllib.parse.parse_qs(payload, keep_blank_values=True)
    return {k: v[0] for k, v in parsed.items()}


def main() -> None:
    env = load_env()
    api_key = env.get("X_API_KEY", "").strip()
    api_secret = env.get("X_API_SECRET", "").strip()
    callback_url = env.get("X_CALLBACK_URL", DEFAULT_CALLBACK_URL).strip() or DEFAULT_CALLBACK_URL

    if not api_key or not api_secret:
        print("Erro: configure X_API_KEY e X_API_SECRET no .env")
        sys.exit(1)

    callback_data: dict[str, str] = {}
    callback_received = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, _format: str, *_args):
            return

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            token = params.get("oauth_token", [""])[0]
            verifier = params.get("oauth_verifier", [""])[0]
            denied = params.get("denied", [""])[0]

            if denied:
                callback_data["error"] = "Autorizacao negada no X."
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"<h2>Autorizacao negada.</h2>")
                callback_received.set()
                return

            if token and verifier:
                callback_data["oauth_token"] = token
                callback_data["oauth_verifier"] = verifier
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"<h2>Autorizado! Pode fechar esta aba.</h2>")
                callback_received.set()
                return

            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<h2>Callback invalido.</h2>")

    parsed_callback = urllib.parse.urlparse(callback_url)
    host = parsed_callback.hostname or "127.0.0.1"
    port = parsed_callback.port or 8080

    try:
        server = http.server.HTTPServer((host, port), Handler)
    except OSError as exc:
        print(f"Erro ao abrir servidor de callback em {host}:{port}: {exc}")
        sys.exit(1)

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    print("Solicitando request token...")
    raw_request_token = oauth1_post(
        REQUEST_TOKEN_URL,
        consumer_key=api_key,
        consumer_secret=api_secret,
        body_params={"oauth_callback": callback_url},
    )
    request_token_data = parse_qs_response(raw_request_token)

    oauth_token = request_token_data.get("oauth_token", "")
    oauth_token_secret = request_token_data.get("oauth_token_secret", "")

    if not oauth_token or not oauth_token_secret:
        print("Erro: request token invalido recebido do X")
        print(raw_request_token)
        server.shutdown()
        sys.exit(1)

    auth_url = f"{AUTHORIZE_URL}?oauth_token={urllib.parse.quote(oauth_token)}"

    print("\nAbra e autorize no X:")
    print(auth_url)
    print("\nTentando abrir o navegador automaticamente...")
    webbrowser.open(auth_url)

    print("Aguardando callback de autorizacao...")
    callback_received.wait(timeout=300)
    server.shutdown()

    if "error" in callback_data:
        print(f"Erro: {callback_data['error']}")
        sys.exit(1)

    if not callback_data.get("oauth_verifier"):
        print("Erro: timeout aguardando callback. Tente novamente.")
        sys.exit(1)

    if callback_data.get("oauth_token") != oauth_token:
        print("Erro: oauth_token de callback nao confere com request token.")
        sys.exit(1)

    print("Trocando por access token...")
    raw_access_token = oauth1_post(
        ACCESS_TOKEN_URL,
        consumer_key=api_key,
        consumer_secret=api_secret,
        token=oauth_token,
        token_secret=oauth_token_secret,
        body_params={"oauth_verifier": callback_data["oauth_verifier"]},
    )
    access_data = parse_qs_response(raw_access_token)

    access_token = access_data.get("oauth_token", "")
    access_token_secret = access_data.get("oauth_token_secret", "")
    user_id = access_data.get("user_id", "")
    screen_name = access_data.get("screen_name", "")

    if not access_token or not access_token_secret:
        print("Erro: access token invalido recebido do X")
        print(raw_access_token)
        sys.exit(1)

    save_to_env("X_CALLBACK_URL", callback_url)
    save_to_env("X_ACCESS_TOKEN", access_token)
    save_to_env("X_ACCESS_TOKEN_SECRET", access_token_secret)
    if user_id:
        save_to_env("X_USER_ID", user_id)
    if screen_name:
        save_to_env("X_USERNAME", screen_name)

    print("\nAutenticacao concluida com sucesso.")
    if screen_name:
        print(f"Conta conectada: @{screen_name}")
    print("Agora rode: python3 scripts/twitter_post.py --dry-run")


if __name__ == "__main__":
    main()
