#!/usr/bin/env python3
"""
Diagnostica permissões de API para métricas em Instagram e LinkedIn.

Uso:
    python3 scripts/social_api_diagnostics.py

O script NÃO altera nada nas contas/apps. Ele apenas testa endpoints de leitura
com as credenciais do .env e imprime um relatório objetivo do que está liberado
ou bloqueado.
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"


def ssl_context() -> ssl.SSLContext:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()

    for k, v in os.environ.items():
        env[k] = v
    return env


def get_json(url: str, headers: dict[str, str] | None = None, ctx: ssl.SSLContext | None = None) -> tuple[int, dict]:
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            return resp.status, payload
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {"raw": body}
        return e.code, payload


def check_instagram(env: dict[str, str], ctx: ssl.SSLContext) -> dict:
    token = env.get("INSTAGRAM_ACCESS_TOKEN", "").strip()
    user_id = env.get("INSTAGRAM_USER_ID", "").strip()

    report: dict = {
        "credentials": bool(token and user_id),
        "media_list": None,
        "latest_media": None,
        "insights": None,
    }

    if not report["credentials"]:
        return report

    media_params = urllib.parse.urlencode(
        {
            "fields": "id,timestamp,permalink,media_type,like_count,comments_count",
            "limit": "3",
            "access_token": token,
        }
    )
    media_url = f"https://graph.facebook.com/v25.0/{user_id}/media?{media_params}"
    status, data = get_json(media_url, ctx=ctx)
    report["media_list"] = {"status": status, "data": data}

    if status != 200:
        return report

    items = data.get("data", [])
    if not items:
        return report

    latest = items[0]
    report["latest_media"] = latest
    media_id = latest.get("id")
    if not media_id:
        return report

    insights_params = urllib.parse.urlencode(
        {
                "metric": "reach,saved,shares,total_interactions",
            "access_token": token,
        }
    )
    insights_url = f"https://graph.facebook.com/v25.0/{media_id}/insights?{insights_params}"
    istatus, insights_data = get_json(insights_url, ctx=ctx)
    report["insights"] = {"status": istatus, "data": insights_data}

    return report


def check_linkedin(env: dict[str, str], ctx: ssl.SSLContext) -> dict:
    token = env.get("LINKEDIN_ACCESS_TOKEN", "").strip()
    author_urn = env.get("LINKEDIN_PERSON_URN", "").strip()

    report: dict = {
        "credentials": bool(token and author_urn),
        "posts_by_author": None,
        "posts_endpoint_used": None,
    }

    if not report["credentials"]:
        return report

    headers_rest = {
        "Authorization": f"Bearer {token}",
        "LinkedIn-Version": "202503",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    params = urllib.parse.urlencode(
        {
            "q": "author",
            "author": author_urn,
            "count": "3",
            "sortBy": "LAST_MODIFIED",
        }
    )
    posts_url = f"https://api.linkedin.com/rest/posts?{params}"
    pstatus, pdata = get_json(posts_url, headers=headers_rest, ctx=ctx)

    if pstatus == 403:
        # rest/posts requer Community Management API (produto restrito).
        # Tenta endpoint legado ugcPosts com w_member_social.
        person_id = author_urn.split(":")[-1] if ":" in author_urn else author_urn
        encoded_author = urllib.parse.quote(author_urn, safe="")
        ugc_params = urllib.parse.urlencode(
            {"q": "authors", "authors": f"List({author_urn})", "count": "3"}
        )
        ugc_url = f"https://api.linkedin.com/v2/ugcPosts?{ugc_params}"
        headers_v2 = {
            "Authorization": f"Bearer {token}",
            "X-Restli-Protocol-Version": "2.0.0",
        }
        u_status, u_data = get_json(ugc_url, headers=headers_v2, ctx=ctx)
        if u_status == 200:
            report["posts_by_author"] = {"status": u_status, "data": u_data}
            report["posts_endpoint_used"] = "v2/ugcPosts"
        else:
            # Ambos os endpoints bloqueados; registra o erro do REST (mais descritivo).
            report["posts_by_author"] = {"status": pstatus, "data": pdata}
            report["posts_endpoint_used"] = "rest/posts (Community Management API required)"
    else:
        report["posts_by_author"] = {"status": pstatus, "data": pdata}
        report["posts_endpoint_used"] = "rest/posts"

    return report


def summarize(instagram: dict, linkedin: dict):
    print("\n=== Social API Diagnostics ===\n")

    print("[Instagram]")
    if not instagram["credentials"]:
        print("- Credenciais ausentes: INSTAGRAM_ACCESS_TOKEN e/ou INSTAGRAM_USER_ID")
    else:
        media = instagram.get("media_list")
        if media and media["status"] == 200:
            items = media["data"].get("data", [])
            print(f"- Listagem de mídia: OK ({len(items)} item(ns) retornados)")
            latest = instagram.get("latest_media") or {}
            if latest:
                print(
                    "- Post mais recente: "
                    f"id={latest.get('id')} likes={latest.get('like_count')} comments={latest.get('comments_count')}"
                )
        else:
            print(f"- Listagem de mídia: FALHA (HTTP {media['status'] if media else 'N/A'})")
            if media:
                print(f"  Detalhe: {json.dumps(media['data'], ensure_ascii=False)}")

        insights = instagram.get("insights")
        if not insights:
            print("- Insights de post: não testado (sem mídia recente)")
        elif insights["status"] == 200:
            rows = insights["data"].get("data", [])
            pairs = []
            for row in rows:
                values = row.get("values") or []
                value = values[0].get("value") if values else None
                pairs.append(f"{row.get('name')}={value}")
            print(f"- Insights de post: OK ({', '.join(pairs) if pairs else 'sem linhas'})")
        else:
            print(f"- Insights de post: FALHA (HTTP {insights['status']})")
            print(f"  Detalhe: {json.dumps(insights['data'], ensure_ascii=False)}")
            print("  Ação sugerida: revisar permissões do app no Meta e regenerar token com novos scopes.")

    print("\n[LinkedIn]")
    if not linkedin["credentials"]:
        print("- Credenciais ausentes: LINKEDIN_ACCESS_TOKEN e/ou LINKEDIN_PERSON_URN")
    else:
        posts = linkedin.get("posts_by_author")
        endpoint_used = linkedin.get("posts_endpoint_used", "")
        if posts and posts["status"] == 200:
            elements = posts["data"].get("elements", []) or posts["data"].get("elements", [])
            count = len(elements)
            print(f"- Busca de posts do autor: OK via {endpoint_used} ({count} item(ns) retornados)")
        else:
            print(f"- Busca de posts do autor: FALHA (HTTP {posts['status'] if posts else 'N/A'})")
            if posts:
                print(f"  Detalhe: {json.dumps(posts['data'], ensure_ascii=False)}")
            if "Community Management API" in (endpoint_used or ""):
                print("  Nota: leitura de posts requer o produto 'Community Management API' (aprovação LinkedIn necessária).")
                print("  Publicação via linkedin_post.py continua funcional com 'Share on LinkedIn' (w_member_social).")
            else:
                print("  Ação sugerida: habilitar produto/permissões de leitura para endpoint REST posts e renovar token.")

    print("\nResumo:")
    ig_ok = bool(instagram.get("insights") and instagram["insights"]["status"] == 200)
    li_ok = bool(linkedin.get("posts_by_author") and linkedin["posts_by_author"]["status"] == 200)
    print(f"- Instagram insights avançados: {'OK' if ig_ok else 'BLOQUEADO — adicionar instagram_manage_insights no app Meta + regenerar token'}")
    li_endpoint = linkedin.get("posts_endpoint_used", "")
    if li_ok:
        print(f"- LinkedIn leitura de posts: OK (via {li_endpoint})")
    elif "Community Management API" in (li_endpoint or ""):
        print("- LinkedIn leitura de posts: BLOQUEADO (analytics) — publicação está OK")
    else:
        print("- LinkedIn leitura de posts/analytics: BLOQUEADO")


def main():
    env = load_env()
    ctx = ssl_context()
    instagram = check_instagram(env, ctx)
    linkedin = check_linkedin(env, ctx)
    summarize(instagram, linkedin)


if __name__ == "__main__":
    main()
