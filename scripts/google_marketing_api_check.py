#!/usr/bin/env python3
"""Check local OAuth access to Google Tag Manager and GA Admin APIs."""

from __future__ import annotations

import json
import subprocess
import sys


ENDPOINTS = {
    "gtm_accounts": "https://tagmanager.googleapis.com/tagmanager/v2/accounts",
    "ga_accounts": "https://analyticsadmin.googleapis.com/v1beta/accounts",
}


def access_token(kind: str) -> str:
    command = ["gcloud", "auth", "print-access-token"]
    if kind == "adc":
        command = ["gcloud", "auth", "application-default", "print-access-token"]

    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        sys.exit("gcloud was not found in PATH.")
    except subprocess.CalledProcessError as error:
        stderr = error.stderr.strip()
        sys.exit(f"Could not get {kind} access token: {stderr}")

    return result.stdout.strip()


def fetch_json(url: str, token: str) -> tuple[int, dict]:
    command = [
        "curl",
        "-sS",
        "-w",
        "\n%{http_code}",
        "-H",
        f"Authorization: Bearer {token}",
        url,
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        sys.exit("curl was not found in PATH.")
    except subprocess.CalledProcessError as error:
        stderr = error.stderr.strip()
        sys.exit(f"Could not call {url}: {stderr}")

    body, _, status_text = result.stdout.rpartition("\n")
    status = int(status_text)
    try:
        payload = json.loads(body or "{}")
    except json.JSONDecodeError:
        payload = {"error": {"message": body}}
    return status, payload


def summarize(name: str, status: int, payload: dict) -> None:
    if status == 200:
        key = "account" if name == "gtm_accounts" else "accounts"
        count = len(payload.get(key, []))
        print(f"OK {name}: HTTP {status}, {count} account(s) visible")
        return

    error = payload.get("error", {})
    reason = error.get("status") or error.get("message") or "unknown error"
    print(f"FAIL {name}: HTTP {status}, {reason}")


def main() -> int:
    mode = "gcloud"
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    if mode not in {"gcloud", "adc"}:
        sys.exit("Usage: scripts/google_marketing_api_check.py [gcloud|adc]")

    token = access_token(mode)
    print(f"Using {mode} token from gcloud.")

    exit_code = 0
    for name, url in ENDPOINTS.items():
        status, payload = fetch_json(url, token)
        summarize(name, status, payload)
        if status != 200:
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
