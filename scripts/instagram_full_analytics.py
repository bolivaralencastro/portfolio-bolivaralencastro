#!/usr/bin/env python3
"""
Coleta analytics completos do Instagram para todas as publicacoes.

Uso:
    /usr/local/bin/python3 scripts/instagram_full_analytics.py

Saidas:
    data/instagram_analytics/latest.json
    data/instagram_analytics/latest.csv
"""

from __future__ import annotations

import csv
import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
OUT_DIR = ROOT / "data" / "instagram_analytics"
OUT_JSON = OUT_DIR / "latest.json"
OUT_CSV = OUT_DIR / "latest.csv"

# Metricas estaveis que ja funcionam nesta conta.
INSIGHT_METRICS = ["reach", "saved", "shares", "total_interactions"]


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
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip()

    for key, value in os.environ.items():
        env[key] = value
    return env


def get_json(url: str, ctx: ssl.SSLContext) -> tuple[int, dict]:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body)
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"raw": body}
        return err.code, parsed


def fetch_all_media(user_id: str, token: str, ctx: ssl.SSLContext) -> list[dict]:
    fields = "id,caption,media_type,media_product_type,timestamp,permalink,like_count,comments_count"
    params = urllib.parse.urlencode({"fields": fields, "limit": "50", "access_token": token})
    next_url = f"https://graph.facebook.com/v25.0/{user_id}/media?{params}"

    media: list[dict] = []
    while next_url:
        status, payload = get_json(next_url, ctx)
        if status != 200:
            raise RuntimeError(f"Falha ao listar midias (HTTP {status}): {payload}")

        media.extend(payload.get("data", []))
        next_url = (payload.get("paging") or {}).get("next")

    return media


def fetch_media_insights(media_id: str, token: str, ctx: ssl.SSLContext) -> dict[str, int | None]:
    """Busca insights com fallback por metrica individual.

    Posts legados de 2021-2022 nao suportam 'shares' nem 'total_interactions'
    mas respondem corretamente para 'reach' e 'saved'. Tentamos todos juntos
    primeiro (mais eficiente) e, em caso de erro 400, tentamos cada metrica
    individualmente para recuperar o maximo possivel.
    """
    values: dict[str, int | None] = {metric: None for metric in INSIGHT_METRICS}

    def _extract(payload: dict) -> None:
        for row in payload.get("data", []):
            name = row.get("name")
            if name not in values:
                continue
            entries = row.get("values") or []
            values[name] = entries[0].get("value") if entries else None

    # Tentativa 1: todas as metricas de uma vez.
    params = urllib.parse.urlencode({"metric": ",".join(INSIGHT_METRICS), "access_token": token})
    url = f"https://graph.facebook.com/v25.0/{media_id}/insights?{params}"
    status, payload = get_json(url, ctx)

    if status == 200:
        _extract(payload)
        return values

    # Tentativa 2: cada metrica individualmente (fallback para posts legados).
    any_ok = False
    last_error_status = status
    for metric in INSIGHT_METRICS:
        params_single = urllib.parse.urlencode({"metric": metric, "access_token": token})
        url_single = f"https://graph.facebook.com/v25.0/{media_id}/insights?{params_single}"
        s, p = get_json(url_single, ctx)
        if s == 200:
            _extract(p)
            any_ok = True
        else:
            last_error_status = s

    if not any_ok:
        values["_error"] = last_error_status

    return values


def aggregate(rows: list[dict]) -> dict:
    summary = {
        "total_publicacoes": len(rows),
        "por_tipo": {},
        "totais_metricas": {metric: 0 for metric in INSIGHT_METRICS},
        "posts_com_erro_insights": 0,
    }

    by_type: dict[str, int] = {}
    for row in rows:
        media_type = row.get("media_type") or "UNKNOWN"
        by_type[media_type] = by_type.get(media_type, 0) + 1

        if row.get("insights_error"):
            summary["posts_com_erro_insights"] += 1

        for metric in INSIGHT_METRICS:
            value = row.get(metric)
            if isinstance(value, int):
                summary["totais_metricas"][metric] += value

    summary["por_tipo"] = by_type

    for metric in ["reach", "total_interactions", "saved", "shares"]:
        ranked = sorted(
            rows,
            key=lambda item: item.get(metric) if isinstance(item.get(metric), int) else -1,
            reverse=True,
        )
        summary[f"top3_{metric}"] = [
            {
                "id": item.get("id"),
                "timestamp": item.get("timestamp"),
                "permalink": item.get("permalink"),
                metric: item.get(metric),
            }
            for item in ranked[:3]
        ]

    return summary


def to_csv(rows: list[dict], file_path: Path) -> None:
    fieldnames = [
        "id",
        "timestamp",
        "media_type",
        "media_product_type",
        "permalink",
        "like_count",
        "comments_count",
        "reach",
        "saved",
        "shares",
        "total_interactions",
        "insights_error",
    ]
    with file_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def main() -> None:
    env = load_env()
    token = env.get("INSTAGRAM_ACCESS_TOKEN", "").strip()
    user_id = env.get("INSTAGRAM_USER_ID", "").strip()
    if not token or not user_id:
        raise RuntimeError("Credenciais ausentes: INSTAGRAM_ACCESS_TOKEN e/ou INSTAGRAM_USER_ID")

    ctx = ssl_context()
    media_items = fetch_all_media(user_id=user_id, token=token, ctx=ctx)

    rows: list[dict] = []
    for item in media_items:
        media_id = item.get("id")
        if not media_id:
            continue
        insights = fetch_media_insights(media_id=media_id, token=token, ctx=ctx)
        row = {
            "id": media_id,
            "timestamp": item.get("timestamp"),
            "media_type": item.get("media_type"),
            "media_product_type": item.get("media_product_type"),
            "permalink": item.get("permalink"),
            "like_count": item.get("like_count"),
            "comments_count": item.get("comments_count"),
            "caption": item.get("caption", ""),
            "reach": insights.get("reach"),
            "saved": insights.get("saved"),
            "shares": insights.get("shares"),
            "total_interactions": insights.get("total_interactions"),
            "insights_error": insights.get("_error"),
        }
        rows.append(row)

    rows.sort(key=lambda item: item.get("timestamp") or "", reverse=True)
    summary = aggregate(rows)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": INSIGHT_METRICS,
        "summary": summary,
        "publicacoes": rows,
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    to_csv(rows, OUT_CSV)

    print("Instagram analytics completo gerado com sucesso.")
    print(f"- Publicacoes analisadas: {summary['total_publicacoes']}")
    print(f"- Tipos: {summary['por_tipo']}")
    print(f"- Totais: {summary['totais_metricas']}")
    print(f"- Com erro de insights: {summary['posts_com_erro_insights']}")
    print(f"- JSON: {OUT_JSON}")
    print(f"- CSV:  {OUT_CSV}")


if __name__ == "__main__":
    main()