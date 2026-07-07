#!/usr/bin/env python3
"""
Refresh Meta API tokens before they expire.

Instagram token: valid 60 days, refresh anytime via ig_refresh_token.
Facebook Page token: permanent (derived from long-lived User token).

Run monthly via cron or manually:
  python3 scripts/refresh_meta_tokens.py
"""

import os
import re
import sys
import requests
from pathlib import Path
from datetime import datetime

ENV_PATH = Path(__file__).parent.parent / ".env"


def load_env():
    env = {}
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"')
    return env


def update_env(key, value):
    content = ENV_PATH.read_text()
    pattern = rf'^({re.escape(key)}=)(.*)$'
    new_content = re.sub(pattern, rf'\g<1>{value}', content, flags=re.MULTILINE)
    ENV_PATH.write_text(new_content)
    print(f"  Updated {key} in .env")


def refresh_instagram_token(env):
    print("\n[Instagram] Refreshing access token...")
    token = env.get("INSTAGRAM_ACCESS_TOKEN")
    if not token:
        print("  ERROR: INSTAGRAM_ACCESS_TOKEN not found in .env")
        return False

    resp = requests.get(
        "https://graph.instagram.com/refresh_access_token",
        params={"grant_type": "ig_refresh_token", "access_token": token}
    )
    data = resp.json()

    if "access_token" in data:
        new_token = data["access_token"]
        expires_in = data.get("expires_in", 0)
        days = expires_in // 86400
        update_env("INSTAGRAM_ACCESS_TOKEN", new_token)
        print(f"  OK — new token valid for {days} days")
        return True
    else:
        print(f"  ERROR: {data}")
        return False


def verify_instagram_token(env):
    print("\n[Instagram] Verifying token...")
    token = env.get("INSTAGRAM_ACCESS_TOKEN")
    resp = requests.get(
        "https://graph.instagram.com/v22.0/me",
        params={"fields": "id,username,account_type", "access_token": token}
    )
    data = resp.json()
    if "username" in data:
        print(f"  OK — @{data['username']} ({data.get('account_type')})")
        return True
    print(f"  ERROR: {data}")
    return False


def refresh_threads_token(env):
    print("\n[Threads] Refreshing access token...")
    token = env.get("THREADS_ACCESS_TOKEN")
    if not token:
        print("  SKIP — THREADS_ACCESS_TOKEN not set (run threads_auth.py)")
        return None

    resp = requests.get(
        "https://graph.threads.net/refresh_access_token",
        params={"grant_type": "th_refresh_token", "access_token": token}
    )
    data = resp.json()
    if "access_token" in data:
        update_env("THREADS_ACCESS_TOKEN", data["access_token"])
        days = data.get("expires_in", 0) // 86400
        print(f"  OK — new token valid for {days} days")
        return True
    print(f"  ERROR: {data}")
    return False


def verify_threads_token(env):
    print("\n[Threads] Verifying token...")
    token = env.get("THREADS_ACCESS_TOKEN")
    if not token:
        print("  SKIP — THREADS_ACCESS_TOKEN not set")
        return None
    resp = requests.get(
        "https://graph.threads.net/v1.0/me",
        params={"fields": "id,username", "access_token": token}
    )
    data = resp.json()
    if "username" in data:
        print(f"  OK — @{data['username']}")
        return True
    print(f"  ERROR: {data}")
    return False


def verify_facebook_page_token(env):
    print("\n[Facebook Page] Verifying token...")
    token = env.get("FACEBOOK_PAGE_ACCESS_TOKEN")
    page_id = env.get("FACEBOOK_PAGE_ID")
    if not token or not page_id:
        print("  SKIP — FACEBOOK_PAGE_ACCESS_TOKEN or FACEBOOK_PAGE_ID not set")
        return False

    resp = requests.get(
        f"https://graph.facebook.com/v22.0/{page_id}",
        params={"fields": "name,fan_count", "access_token": token}
    )
    data = resp.json()
    if "name" in data:
        print(f"  OK — {data['name']} ({data.get('fan_count', '?')} fãs)")
        return True
    print(f"  ERROR: {data}")
    return False


def verify_pixel(env):
    print("\n[Meta Pixel] Verifying...")
    pixel_id = env.get("META_PIXEL_ID")
    token = env.get("FACEBOOK_PAGE_ACCESS_TOKEN")
    if not pixel_id or not token:
        print("  SKIP — META_PIXEL_ID or token not set")
        return False

    resp = requests.get(
        f"https://graph.facebook.com/v22.0/{pixel_id}",
        params={"fields": "id,name,last_fired_time", "access_token": token}
    )
    data = resp.json()
    if "id" in data:
        last_fired = data.get("last_fired_time", "nunca")
        print(f"  OK — Pixel {pixel_id} | last fired: {last_fired}")
        return True
    print(f"  ERROR: {data}")
    return False


if __name__ == "__main__":
    print(f"Meta Token Refresh — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"ENV: {ENV_PATH}")

    env = load_env()

    ok_ig = refresh_instagram_token(env)
    ok_th = refresh_threads_token(env)
    if ok_ig or ok_th:
        env = load_env()  # reload with new tokens

    verify_instagram_token(env)
    verify_threads_token(env)
    verify_facebook_page_token(env)
    verify_pixel(env)

    print("\nDone.")
    sys.exit(0 if ok_ig else 1)
