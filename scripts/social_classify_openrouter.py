#!/usr/bin/env python3
"""
Classifica itens de curadoria social com OpenRouter e salva no SQLite.

Fluxo esperado (semanal):
    1) python3 scripts/social_capture_browser.py all
    2) python3 scripts/social_classify_openrouter.py --limit 80
    3) python3 scripts/social_curation.py report --days 7 --only-classified
    4) python3 scripts/social_curation.py report --days 7 --label ai-tools

Requer:
    - OPENROUTER_API_KEY no .env ou no ambiente
Opcional:
    - OPENROUTER_MODEL (default: openai/gpt-4.1-mini)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from social_curation import connect  # noqa: E402


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-4.1-mini"
DEFAULT_LABELS = [
    "ai-tools",
    "design",
    "produto",
    "negocios",
    "programacao",
    "criatividade",
    "sociedade",
    "misc",
]

try:
    import certifi

    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = ssl.create_default_context()


def load_env_file() -> dict[str, str]:
    env_path = ROOT / ".env"
    values: dict[str, str] = {}
    if not env_path.exists():
        return values
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def get_config() -> tuple[str, str]:
    env_file = load_env_file()
    api_key = os.environ.get("OPENROUTER_API_KEY") or env_file.get("OPENROUTER_API_KEY", "")
    model = os.environ.get("OPENROUTER_MODEL") or env_file.get("OPENROUTER_MODEL", DEFAULT_MODEL)
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY ausente no ambiente/.env")
    return api_key.strip(), model.strip()


def build_prompt(item: dict[str, Any], labels: list[str]) -> str:
    payload = {
        "source": item["source"],
        "kind": item["kind"],
        "url": item["url"],
        "title": item.get("title") or "",
        "text": item.get("text") or "",
        "author": item.get("author") or "",
        "author_handle": item.get("author_handle") or "",
    }
    labels_str = ", ".join(labels)
    return (
        "Classifique o item abaixo em APENAS um rótulo permitido. "
        f"Rótulos permitidos: {labels_str}. "
        "Retorne JSON puro no formato: "
        '{"label":"...","score":0.0,"reason":"..."}. '
        "score entre 0 e 1. reason curta (ate 180 chars) em pt-BR. "
        "Se conteúdo for insuficiente, use label 'misc' e score baixo.\n\n"
        f"ITEM:\n{json.dumps(payload, ensure_ascii=False)}"
    )


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError(f"Resposta sem JSON: {text[:200]}")
    return json.loads(match.group(0))


def classify_item(
    api_key: str,
    model: str,
    item: dict[str, Any],
    labels: list[str],
    timeout: int = 60,
) -> tuple[str, float, str]:
    prompt = build_prompt(item, labels)
    body = {
        "model": model,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": "Voce classifica links para curadoria editorial em pt-BR com saida JSON estrita.",
            },
            {"role": "user", "content": prompt},
        ],
    }
    req = urllib.request.Request(
        OPENROUTER_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CONTEXT) as response:
            data = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Erro HTTP {exc.code}: {exc.read().decode(errors='replace')}") from exc

    choices = data.get("choices") or []
    if not choices:
        raise ValueError(f"Resposta sem choices: {data}")

    content = choices[0].get("message", {}).get("content", "")
    parsed = extract_json(content)

    label = str(parsed.get("label") or "misc").strip().lower()
    if label not in labels:
        label = "misc"

    try:
        score = float(parsed.get("score", 0.0))
    except (TypeError, ValueError):
        score = 0.0
    score = max(0.0, min(1.0, score))

    reason = str(parsed.get("reason") or "").strip()
    if len(reason) > 180:
        reason = reason[:177].rstrip() + "..."

    return label, score, reason


def fetch_candidates(
    con,
    limit: int,
    days: int,
    source: str | None,
    kind: str | None,
    overwrite: bool,
):
    since = (datetime.now(UTC) - timedelta(days=days)).date().isoformat()
    clauses = ["(COALESCE(date, '') = '' OR date >= ?)"]
    params: list[Any] = [since]

    if source:
        clauses.append("source = ?")
        params.append(source)
    if kind:
        clauses.append("kind = ?")
        params.append(kind)
    if not overwrite:
        clauses.append("COALESCE(ai_label, '') = ''")

    where_sql = " AND ".join(clauses)
    query = f"""
        SELECT id, source, kind, url, title, text, author, author_handle
        FROM social_items
        WHERE {where_sql}
        ORDER BY COALESCE(date, '0000-00-00') DESC, id DESC
        LIMIT ?
    """
    params.append(limit)
    rows = con.execute(query, params).fetchall()
    keys = ["id", "source", "kind", "url", "title", "text", "author", "author_handle"]
    return [dict(zip(keys, row)) for row in rows]


def save_classification(con, item_id: int, label: str, score: float, reason: str, model: str) -> None:
    con.execute(
        """
        UPDATE social_items
        SET ai_label = ?,
            ai_score = ?,
            ai_reason = ?,
            ai_model = ?,
            ai_classified_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (label, score, reason, model, item_id),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Classifica itens de curadoria via OpenRouter")
    parser.add_argument("--limit", type=int, default=80)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--source", choices=["linkedin", "instagram"])
    parser.add_argument("--kind", default="saved")
    parser.add_argument("--labels", help="Lista de labels separadas por virgula")
    parser.add_argument("--overwrite", action="store_true", help="Reclassifica itens que ja possuem label")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--delay-ms", type=int, default=500)
    args = parser.parse_args()

    labels = [part.strip().lower() for part in (args.labels.split(",") if args.labels else DEFAULT_LABELS) if part.strip()]
    if "misc" not in labels:
        labels.append("misc")

    api_key, model = get_config()
    con = connect()

    items = fetch_candidates(
        con,
        limit=args.limit,
        days=args.days,
        source=args.source,
        kind=args.kind,
        overwrite=args.overwrite,
    )
    if not items:
        print("Nenhum item para classificar com os filtros atuais.")
        con.close()
        return

    print(f"Classificando {len(items)} item(ns) com modelo {model}...")
    updated = 0
    for idx, item in enumerate(items, start=1):
        try:
            label, score, reason = classify_item(api_key, model, item, labels)
        except Exception as exc:
            print(f"[{idx}/{len(items)}] ERRO id={item['id']} url={item['url']} -> {exc}")
            continue

        preview = f"[{idx}/{len(items)}] id={item['id']} -> {label} ({score:.2f})"
        if reason:
            preview += f" | {reason}"
        print(preview)

        if not args.dry_run:
            save_classification(con, item["id"], label, score, reason, model)
            updated += 1

        if args.delay_ms > 0 and idx < len(items):
            time.sleep(args.delay_ms / 1000)

    if not args.dry_run:
        con.commit()
        print(f"Concluido. Itens classificados: {updated}")
    else:
        print("Dry-run: nenhuma classificacao foi salva.")
    con.close()


if __name__ == "__main__":
    main()
