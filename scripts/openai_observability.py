#!/usr/bin/env python3
"""
Probe e observabilidade local para requests da OpenAI.

Objetivos:
    - executar requests pequenos para validar a conta e o modelo
    - persistir request, response e usage em SQLite local
    - calcular custo estimado quando as taxas forem informadas
    - manter um rastro profissional e revisavel sem depender de logs soltos

Exemplos:
    python3 scripts/openai_observability.py probe \
        --model gpt-5.4-mini \
        --prompt "Reply with exactly one word: ok"

    python3 scripts/openai_observability.py probe \
        --model gpt-image-2 \
        --mode image \
        --prompt "Create a portrait of a man with soft studio light" \
        --input-image /path/to/reference.png

    python3 scripts/openai_observability.py summary --limit 10
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sqlite3
import sys
import time
import ssl
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
DB_PATH = Path(
    os.environ.get(
        "OPENAI_OBSERVABILITY_DB_PATH",
        str(ROOT / "data" / "openai-observability.sqlite"),
    )
)
GENERATED_IMAGE_DIR = ROOT / "data" / "generated-images"

TEXT_MODEL_PRICING = {
    "gpt-5.4-mini": {
        "input_rate_usd_per_1m": 0.75,
        "output_rate_usd_per_1m": 4.50,
        "source": "OpenAI model page",
    },
    "gpt-5.4": {
        "input_rate_usd_per_1m": 2.50,
        "output_rate_usd_per_1m": 15.00,
        "source": "OpenAI model page",
    },
    "gpt-5.5": {
        "input_rate_usd_per_1m": 5.00,
        "output_rate_usd_per_1m": 30.00,
        "source": "OpenAI model page",
    },
}

try:
    import certifi

    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = ssl.create_default_context()


def load_env_file() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_FILE.exists():
        return values

    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def get_api_key() -> str:
    env_values = load_env_file()
    key = os.environ.get("OPENAI_API_KEY") or env_values.get("OPENAI_API_KEY") or ""
    return key.strip()


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def stable_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json_argument(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    candidate = Path(raw)
    if candidate.exists():
        return json.loads(candidate.read_text(encoding="utf-8"))
    return json.loads(raw)


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def format_brl(value: float | None) -> str:
    if value is None:
        return "indisponivel"
    return f"R${value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fetch_bcb_usd_brl(days_back: int = 7) -> dict[str, Any] | None:
    end = datetime.now(UTC).date()
    start = end - timedelta(days=days_back)
    url = (
        "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
        "CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?"
        f"@moeda='USD'&@dataInicial='{start.strftime('%m-%d-%Y')}'&@dataFinalCotacao='{end.strftime('%m-%d-%Y')}'"
        "&$top=1&$orderby=dataHoraCotacao%20desc&$format=json&$select=cotacaoVenda,dataHoraCotacao"
    )
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    values = payload.get("value") or []
    if not values:
        return None
    latest = values[0]
    return {
        "usd_brl": float(latest["cotacaoVenda"]),
        "quoted_at": latest["dataHoraCotacao"],
        "source": "Banco Central do Brasil PTAX",
    }


def ensure_columns(con: sqlite3.Connection) -> None:
    existing = {
        row["name"]
        for row in con.execute("PRAGMA table_info(openai_requests)").fetchall()
    }
    additions = {
        "request_surface": "TEXT",
        "playground_session_id": "TEXT",
        "billing_classification": "TEXT",
        "free_usage_eligible": "INTEGER",
        "free_usage_confirmed": "INTEGER",
        "cost_estimate_brl": "REAL",
        "fx_rate_usd_brl": "REAL",
        "fx_source": "TEXT",
        "fx_quoted_at": "TEXT",
    }
    for column, ddl_type in additions.items():
        if column not in existing:
            con.execute(f"ALTER TABLE openai_requests ADD COLUMN {column} {ddl_type}")
    con.commit()


def init_db(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS openai_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recorded_at TEXT NOT NULL,
            project_name TEXT,
            run_label TEXT,
            mode TEXT NOT NULL,
            model TEXT NOT NULL,
            request_hash TEXT NOT NULL,
            prompt TEXT,
            prompt_hash TEXT,
            input_payload_json TEXT,
            request_json TEXT NOT NULL,
            response_id TEXT,
            response_json TEXT,
            usage_json TEXT,
            latency_ms INTEGER,
            status TEXT NOT NULL,
            cost_estimate_usd REAL,
            pricing_json TEXT,
            output_text TEXT,
            output_path TEXT,
            error_json TEXT,
            sdk_version TEXT,
            python_version TEXT,
            metadata_json TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_openai_requests_recorded_at
        ON openai_requests(recorded_at);

        CREATE INDEX IF NOT EXISTS idx_openai_requests_model
        ON openai_requests(model);

        CREATE INDEX IF NOT EXISTS idx_openai_requests_status
        ON openai_requests(status);

        CREATE INDEX IF NOT EXISTS idx_openai_requests_request_hash
        ON openai_requests(request_hash);
        """
    )
    con.commit()
    ensure_columns(con)


def get_openai_client():
    from openai import OpenAI

    api_key = get_api_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY ausente no ambiente ou no .env")
    return OpenAI(api_key=api_key)


def resolve_pricing(
    *,
    mode: str,
    model: str,
    input_rate_usd_per_1m: float | None,
    output_rate_usd_per_1m: float | None,
    cost_per_image_usd: float | None,
) -> dict[str, Any]:
    if mode == "text":
        default = TEXT_MODEL_PRICING.get(model, {})
        resolved_input = input_rate_usd_per_1m
        resolved_output = output_rate_usd_per_1m
        if resolved_input is None:
            resolved_input = default.get("input_rate_usd_per_1m")
        if resolved_output is None:
            resolved_output = default.get("output_rate_usd_per_1m")
        return {
            "mode": mode,
            "model": model,
            "input_rate_usd_per_1m": resolved_input,
            "output_rate_usd_per_1m": resolved_output,
            "source": default.get("source") if default else "manual",
        }

    return {
        "mode": mode,
        "model": model,
        "cost_per_image_usd": cost_per_image_usd,
        "source": "manual",
    }


def bool_to_int(value: bool | None) -> int | None:
    if value is None:
        return None
    return 1 if value else 0


def estimate_cost(
    usage: dict[str, Any] | None,
    *,
    mode: str,
    model: str,
    input_rate_usd_per_1m: float | None,
    output_rate_usd_per_1m: float | None,
    cost_per_image_usd: float | None,
    image_count: int | None,
) -> float | None:
    pricing = resolve_pricing(
        mode=mode,
        model=model,
        input_rate_usd_per_1m=input_rate_usd_per_1m,
        output_rate_usd_per_1m=output_rate_usd_per_1m,
        cost_per_image_usd=cost_per_image_usd,
    )

    if mode == "image":
        if pricing.get("cost_per_image_usd") is None:
            return None
        return float(pricing["cost_per_image_usd"]) * float(image_count or 1)

    if not usage:
        return None
    if pricing.get("input_rate_usd_per_1m") is None and pricing.get("output_rate_usd_per_1m") is None:
        return None

    total = 0.0
    input_tokens = float(usage.get("input_tokens") or 0.0)
    output_tokens = float(usage.get("output_tokens") or 0.0)

    if pricing.get("input_rate_usd_per_1m") is not None:
        total += input_tokens * float(pricing["input_rate_usd_per_1m"]) / 1_000_000
    if pricing.get("output_rate_usd_per_1m") is not None:
        total += output_tokens * float(pricing["output_rate_usd_per_1m"]) / 1_000_000
    return total


def build_request_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.mode == "text":
        return {
            "model": args.model,
            "input": args.prompt,
            "max_output_tokens": args.max_output_tokens,
        }

    if args.mode == "image":
        return {
            "model": args.model,
            "prompt": args.prompt,
            "size": args.size,
            "quality": args.quality,
            "background": args.background,
            "moderation": args.moderation,
            "n": args.n,
            "input_images": [
                {
                    "path": str(Path(raw_path).expanduser().resolve()),
                    "sha256": file_sha256(Path(raw_path).expanduser().resolve()),
                }
                for raw_path in args.input_image or []
            ],
        }

    raise ValueError(f"Modo nao suportado: {args.mode}")


def default_image_output_path(*, model: str, request_hash: str, recorded_at: str) -> Path:
    stamp = recorded_at.replace(":", "").replace("-", "").replace("+00:00", "Z")
    return GENERATED_IMAGE_DIR / model / f"{stamp}-{request_hash[:12]}.png"


def estimate_latency_seconds(*, mode: str, image_count: int | None, model: str) -> dict[str, Any]:
    if mode != "image":
        return {
            "estimated_seconds": 12,
            "confidence": "medium",
            "basis": "text baseline",
        }

    refs = image_count or 0
    if refs >= 4:
        return {
            "estimated_seconds": 90,
            "confidence": "medium",
            "basis": "image edit with 4+ references",
        }
    if refs >= 2:
        return {
            "estimated_seconds": 75,
            "confidence": "medium",
            "basis": "image edit with 2-3 references",
        }
    return {
        "estimated_seconds": 60,
        "confidence": "medium",
        "basis": f"single image generation baseline for {model}",
    }


def record_row(con: sqlite3.Connection, row: dict[str, Any]) -> None:
    keys = sorted(row.keys())
    placeholders = ", ".join("?" for _ in keys)
    columns = ", ".join(keys)
    con.execute(
        f"INSERT INTO openai_requests ({columns}) VALUES ({placeholders})",
        [row[key] for key in keys],
    )
    con.commit()


def probe(args: argparse.Namespace) -> None:
    client = get_openai_client()
    con = connect()
    init_db(con)

    request_payload = build_request_payload(args)
    request_hash = sha256_text(stable_json(request_payload))
    metadata = args.metadata or {}
    prompt_hash = sha256_text(args.prompt.strip())
    run_started_at = utc_now()
    started = time.perf_counter()
    status = "completed"
    response_json: dict[str, Any] | None = None
    usage_json: dict[str, Any] | None = None
    response_text: str | None = None
    response_id: str | None = None
    error_json: dict[str, Any] | None = None
    output_path: str | None = None
    fx = None
    cost_estimate_usd = None
    cost_estimate_brl = None
    pricing_json = resolve_pricing(
        mode=args.mode,
        model=args.model,
        input_rate_usd_per_1m=args.input_rate_usd_per_1m,
        output_rate_usd_per_1m=args.output_rate_usd_per_1m,
        cost_per_image_usd=args.cost_per_image_usd,
    )
    image_count = len(request_payload.get("input_images") or []) if args.mode == "image" else None
    latency_estimate = estimate_latency_seconds(mode=args.mode, image_count=image_count, model=args.model)
    billing_classification = args.billing_classification
    if billing_classification is None:
        billing_classification = "free_or_paid_unknown" if args.request_surface == "playground" else "unknown"
    default_output_path = None
    if args.mode == "image" and not args.output:
        default_output_path = default_image_output_path(
            model=args.model,
            request_hash=request_hash,
            recorded_at=run_started_at,
        )

    print(
        json.dumps(
            {
                "eta_seconds": latency_estimate["estimated_seconds"],
                "eta_confidence": latency_estimate["confidence"],
                "eta_basis": latency_estimate["basis"],
                "request_surface": args.request_surface,
                "mode": args.mode,
                "model": args.model,
                "reference_images": image_count or 0,
            },
            ensure_ascii=False,
        )
    )

    try:
        if args.mode == "text":
            response = client.responses.create(
                model=args.model,
                input=args.prompt,
                max_output_tokens=args.max_output_tokens,
            )
            response_json = response.model_dump()
            usage_json = getattr(response, "usage", None).model_dump() if getattr(response, "usage", None) else None
            response_text = getattr(response, "output_text", None)
            response_id = getattr(response, "id", None)
        else:
            if args.model != "gpt-image-2":
                raise ValueError("modo image neste script está preparado para gpt-image-2")
            image_paths = [Path(path).expanduser().resolve() for path in args.input_image or []]
            image_kwargs: dict[str, Any] = {
                "model": args.model,
                "prompt": args.prompt,
                "size": args.size,
                "quality": args.quality,
            }
            if image_paths:
                image_kwargs["image"] = [path.open("rb") for path in image_paths]
                if args.background is not None:
                    image_kwargs["background"] = args.background
                if args.moderation is not None:
                    image_kwargs["moderation"] = args.moderation
                response = client.images.edit(**image_kwargs)
                for handle in image_kwargs["image"]:
                    handle.close()
            else:
                if args.background is not None:
                    image_kwargs["background"] = args.background
                if args.moderation is not None:
                    image_kwargs["moderation"] = args.moderation
                response = client.images.generate(**image_kwargs)
            response_json = response.model_dump()
            usage_json = getattr(response, "usage", None).model_dump() if getattr(response, "usage", None) else None
            response_id = getattr(response, "id", None)
            image_item = None
            if getattr(response, "data", None):
                image_item = response.data[0]
            if image_item:
                candidate_output = args.output or str(default_output_path) if default_output_path else args.output
                if candidate_output:
                    output_path = str(Path(candidate_output).expanduser().resolve())
                else:
                    output_path = None
            if image_item and output_path:
                image_b64 = getattr(image_item, "b64_json", None)
                if image_b64:
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    Path(output_path).write_bytes(base64.b64decode(image_b64))
    except Exception as exc:  # pragma: no cover - surfaced to the user
        status = "failed"
        error_json = {
            "type": exc.__class__.__name__,
            "message": str(exc),
        }
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        cost_estimate_usd = estimate_cost(
            usage_json,
            mode=args.mode,
            model=args.model,
            input_rate_usd_per_1m=args.input_rate_usd_per_1m,
            output_rate_usd_per_1m=args.output_rate_usd_per_1m,
            cost_per_image_usd=args.cost_per_image_usd,
            image_count=image_count,
        )
        try:
            fx = fetch_bcb_usd_brl()
        except Exception:
            fx = None
        if cost_estimate_usd is not None and fx is not None:
            cost_estimate_brl = cost_estimate_usd * fx["usd_brl"]
        row = {
            "recorded_at": utc_now(),
            "project_name": args.project_name,
            "run_label": args.run_label,
            "mode": args.mode,
            "model": args.model,
            "request_hash": request_hash,
            "request_surface": args.request_surface,
            "playground_session_id": args.playground_session_id,
            "prompt": args.prompt,
            "prompt_hash": prompt_hash,
            "input_payload_json": stable_json(request_payload.get("input_images") or request_payload.get("input") or {}),
            "request_json": stable_json(request_payload),
            "response_id": response_id,
            "response_json": stable_json(response_json) if response_json else None,
            "usage_json": stable_json(usage_json) if usage_json else None,
            "latency_ms": elapsed_ms,
            "status": status,
            "cost_estimate_usd": cost_estimate_usd,
            "cost_estimate_brl": cost_estimate_brl,
            "fx_rate_usd_brl": fx["usd_brl"] if fx else None,
            "fx_source": fx["source"] if fx else None,
            "fx_quoted_at": fx["quoted_at"] if fx else None,
            "billing_classification": billing_classification,
            "free_usage_eligible": bool_to_int(args.free_usage_eligible),
            "free_usage_confirmed": bool_to_int(args.free_usage_confirmed),
            "pricing_json": stable_json(pricing_json),
            "output_text": response_text,
            "output_path": output_path,
            "error_json": stable_json(error_json),
            "sdk_version": args.sdk_version,
            "python_version": args.python_version,
            "metadata_json": stable_json(metadata) if metadata else None,
        }
        record_row(con, row)
        print(json.dumps(row, ensure_ascii=False, indent=2))
        raise

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    row = {
        "recorded_at": utc_now(),
        "project_name": args.project_name,
        "run_label": args.run_label,
        "mode": args.mode,
        "model": args.model,
        "request_hash": request_hash,
        "request_surface": args.request_surface,
        "playground_session_id": args.playground_session_id,
        "prompt": args.prompt,
        "prompt_hash": prompt_hash,
        "input_payload_json": stable_json(request_payload.get("input_images") or request_payload.get("input") or {}),
        "request_json": stable_json(request_payload),
        "response_id": response_id,
        "response_json": stable_json(response_json) if response_json else None,
        "usage_json": stable_json(usage_json) if usage_json else None,
        "latency_ms": elapsed_ms,
        "status": status,
        "cost_estimate_usd": estimate_cost(
            usage_json,
            mode=args.mode,
            model=args.model,
            input_rate_usd_per_1m=args.input_rate_usd_per_1m,
            output_rate_usd_per_1m=args.output_rate_usd_per_1m,
            cost_per_image_usd=args.cost_per_image_usd,
            image_count=image_count,
        ),
        "cost_estimate_brl": None,
        "fx_rate_usd_brl": None,
        "fx_source": None,
        "fx_quoted_at": None,
        "billing_classification": billing_classification,
        "free_usage_eligible": bool_to_int(args.free_usage_eligible),
        "free_usage_confirmed": bool_to_int(args.free_usage_confirmed),
        "pricing_json": stable_json(pricing_json),
        "output_text": response_text,
        "output_path": output_path,
        "error_json": None,
        "sdk_version": args.sdk_version,
        "python_version": args.python_version,
        "metadata_json": stable_json(metadata) if metadata else None,
    }
    cost_estimate_usd = estimate_cost(
        usage_json,
        mode=args.mode,
        model=args.model,
        input_rate_usd_per_1m=args.input_rate_usd_per_1m,
        output_rate_usd_per_1m=args.output_rate_usd_per_1m,
        cost_per_image_usd=args.cost_per_image_usd,
        image_count=image_count,
    )
    try:
        fx = fetch_bcb_usd_brl()
    except Exception:
        fx = None
    if cost_estimate_usd is not None and fx is not None:
        cost_estimate_brl = cost_estimate_usd * fx["usd_brl"]
    row["cost_estimate_usd"] = cost_estimate_usd
    row["cost_estimate_brl"] = cost_estimate_brl
    row["fx_rate_usd_brl"] = fx["usd_brl"] if fx else None
    row["fx_source"] = fx["source"] if fx else None
    row["fx_quoted_at"] = fx["quoted_at"] if fx else None
    record_row(con, row)

    print(json.dumps(
        {
            "recorded_at": row["recorded_at"],
            "request_hash": request_hash,
            "response_id": response_id,
            "mode": args.mode,
            "model": args.model,
            "latency_ms": elapsed_ms,
            "status": status,
            "usage": usage_json,
            "cost_estimate_usd": row["cost_estimate_usd"],
            "cost_estimate_brl": row["cost_estimate_brl"],
            "fx_rate_usd_brl": row["fx_rate_usd_brl"],
            "billing_classification": row["billing_classification"],
            "free_usage_eligible": row["free_usage_eligible"],
            "free_usage_confirmed": row["free_usage_confirmed"],
            "pricing": pricing_json,
            "output_text": response_text,
            "output_path": output_path,
        },
        ensure_ascii=False,
        indent=2,
    ))


def summary(args: argparse.Namespace) -> None:
    con = connect()
    init_db(con)
    rows = con.execute(
        """
        SELECT *
        FROM openai_requests
        ORDER BY recorded_at DESC
        LIMIT ?
        """,
        (args.limit,),
    ).fetchall()

    if not rows:
        print("Nenhuma request registrada.")
        return

    total_cost = sum(float(row["cost_estimate_usd"]) for row in rows if row["cost_estimate_usd"] is not None)
    brl_rows = [float(row["cost_estimate_brl"]) for row in rows if row["cost_estimate_brl"] is not None]
    total_cost_brl = sum(brl_rows) if brl_rows else None
    completed = sum(1 for row in rows if row["status"] == "completed")
    failed = sum(1 for row in rows if row["status"] == "failed")
    api_rows = sum(1 for row in rows if row["request_surface"] == "api")
    playground_rows = sum(1 for row in rows if row["request_surface"] == "playground")
    free_confirmed_rows = sum(1 for row in rows if row["free_usage_confirmed"] == 1)

    print(f"Requests analisadas: {len(rows)}")
    print(f"Concluidas: {completed}")
    print(f"Falhas: {failed}")
    print(f"Origem API: {api_rows}")
    print(f"Origem Playground: {playground_rows}")
    print(f"Free usage confirmado: {free_confirmed_rows}")
    print(f"Custo estimado total: US${total_cost:.6f}")
    print(f"Custo estimado total: {format_brl(total_cost_brl)}")
    print("\nUltimas requests:")
    for row in rows[: args.limit]:
        cost = (
            f"US${float(row['cost_estimate_usd']):.6f}"
            if row["cost_estimate_usd"] is not None
            else "sem custo"
        )
        cost_brl = (
            format_brl(float(row["cost_estimate_brl"]))
            if row["cost_estimate_brl"] is not None
            else "sem custo"
        )
        print(
            f"- {row['recorded_at']} | {row['mode']} | {row['model']} | {row['status']} | "
            f"{cost} | {cost_brl} | {row['request_surface']} | {row['latency_ms']}ms | {row['request_hash'][:10]}"
        )


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--project-name", default="default-project")
    common.add_argument("--run-label", default=None)
    common.add_argument("--input-rate-usd-per-1m", type=float, default=None)
    common.add_argument("--output-rate-usd-per-1m", type=float, default=None)
    common.add_argument("--cost-per-image-usd", type=float, default=None)
    common.add_argument("--metadata", type=str, default=None, help="JSON inline ou path para um JSON")
    common.add_argument(
        "--request-surface",
        choices=["api", "playground"],
        default="api",
        help="Origem observada da request. Use playground quando a execução vier do Playground.",
    )
    common.add_argument("--playground-session-id", default=None, help="Identificador opcional da sessão no Playground")
    common.add_argument(
        "--billing-classification",
        default=None,
        help="Classificacao manual: free_or_paid_unknown, free_shared, prepaid, paid, unknown",
    )
    common.add_argument(
        "--free-usage-eligible",
        action="store_true",
        default=None,
        help="Marca a request como elegivel para free usage compartilhado",
    )
    common.add_argument(
        "--free-usage-confirmed",
        action="store_true",
        default=None,
        help="Marca a request como confirmada no Usage Dashboard como free usage",
    )
    common.add_argument("--sdk-version", default=None)
    common.add_argument(
        "--python-version",
        default=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    )

    parser = argparse.ArgumentParser(
        description="Observabilidade local para requests OpenAI",
        parents=[common],
    )

    sub = parser.add_subparsers(dest="command", required=True)

    probe_parser = sub.add_parser("probe", help="Executa uma request minima e registra observabilidade", parents=[common])
    probe_parser.add_argument("--mode", choices=["text", "image"], default="text")
    probe_parser.add_argument("--model", required=True)
    probe_parser.add_argument("--prompt", required=True)
    probe_parser.add_argument("--max-output-tokens", type=int, default=16)
    probe_parser.add_argument("--output", help="Caminho para salvar imagem gerada no modo image")
    probe_parser.add_argument("--input-image", action="append", default=[], help="Imagem opcional de referência")
    probe_parser.add_argument("--size", default="1024x1024")
    probe_parser.add_argument("--quality", default="medium")
    probe_parser.add_argument("--background", default=None)
    probe_parser.add_argument("--moderation", default=None)
    probe_parser.add_argument("--n", type=int, default=1)
    probe_parser.set_defaults(func=probe)

    summary_parser = sub.add_parser("summary", help="Resumo das requests registradas", parents=[common])
    summary_parser.add_argument("--limit", type=int, default=20)
    summary_parser.set_defaults(func=summary)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.sdk_version is None:
        try:
            import openai

            args.sdk_version = getattr(openai, "__version__", "unknown")
        except Exception:
            args.sdk_version = "unknown"

    if args.metadata:
        args.metadata = read_json_argument(args.metadata)
    try:
        args.func(args)
    except Exception:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
