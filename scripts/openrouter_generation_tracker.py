#!/usr/bin/env python3
"""
Rastreia geracoes OpenRouter em SQLite e calcula resumos/projecoes simples.

Exemplos:
    python3 scripts/openrouter_generation_tracker.py init
    python3 scripts/openrouter_generation_tracker.py record-video-job \
        --job-json /Users/Pessoal/Desktop/pacote/video-job.json \
        --slug meu-post \
        --workflow seedance-social \
        --asset-pack /Users/Pessoal/Desktop/pacote \
        --output /Users/Pessoal/Desktop/pacote/video.mp4 \
        --prompt-path /Users/Pessoal/Desktop/pacote/roteiro.md
    python3 scripts/openrouter_generation_tracker.py summary --days 30
    python3 scripts/openrouter_generation_tracker.py forecast-video \
        --model bytedance/seedance-2.0 --duration 6 --resolution 720p --count 12
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import ssl
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "openrouter-generations.sqlite"
ENV_FILE = ROOT / ".env"

try:
    import certifi

    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = ssl.create_default_context()

VIDEO_RATE_PER_MTOKEN = {
    "bytedance/seedance-2.0": 7.0,
    "bytedance/seedance-2.0-fast": 5.6,
}

VIDEO_RESOLUTION_DIMS = {
    "480p": (854, 480),
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "1K": (1024, 1024),
    "2K": (2048, 2048),
    "4K": (3840, 2160),
}


@dataclass
class Forecast:
    model: str
    duration: int
    resolution: str
    count: int
    tokens_per_video: int | None
    estimated_cost_per_video: float | None
    estimated_total_cost: float | None
    historical_avg_cost: float | None


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


def get_openrouter_api_key() -> str:
    env_file = load_env_file()
    return (os.environ.get("OPENROUTER_API_KEY") or env_file.get("OPENROUTER_API_KEY") or "").strip()


def fetch_openrouter_credits() -> dict[str, float] | None:
    api_key = get_openrouter_api_key()
    if not api_key:
        return None
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/credits",
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )
    with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    data = payload.get("data") or {}
    total_credits = float(data.get("total_credits", 0.0))
    total_usage = float(data.get("total_usage", 0.0))
    return {
        "total_credits": total_credits,
        "total_usage": total_usage,
        "remaining_credits": total_credits - total_usage,
    }


def fetch_bcb_usd_brl(days_back: int = 7) -> dict[str, Any]:
    end = datetime.now().date()
    start = end - timedelta(days=days_back)
    url = (
        "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
        "CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?"
        f"@moeda='USD'&@dataInicial='{start.strftime('%m-%d-%Y')}'&@dataFinalCotacao='{end.strftime('%m-%d-%Y')}'"
        "&$top=1&$orderby=dataHoraCotacao%20desc&$format=json&$select=cotacaoVenda,dataHoraCotacao"
    )
    with urllib.request.urlopen(url, context=SSL_CONTEXT, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    values = payload.get("value") or []
    if not values:
        raise RuntimeError("BCB PTAX sem valores para USD/BRL no periodo consultado")
    latest = values[0]
    return {
        "usd_brl": float(latest["cotacaoVenda"]),
        "quoted_at": latest["dataHoraCotacao"],
        "source": "Banco Central do Brasil PTAX",
    }


def format_brl(value: float | None) -> str:
    if value is None:
        return "indisponivel"
    return f"R${value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS openrouter_generations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            provider_job_id TEXT,
            generation_id TEXT,
            model TEXT NOT NULL,
            modality TEXT NOT NULL,
            workflow TEXT,
            slug TEXT,
            asset_pack_path TEXT,
            prompt_path TEXT,
            prompt_text TEXT,
            first_frame_path TEXT,
            last_frame_path TEXT,
            output_path TEXT,
            status TEXT NOT NULL,
            cost_usd REAL,
            duration_seconds INTEGER,
            resolution TEXT,
            aspect_ratio TEXT,
            retries INTEGER NOT NULL DEFAULT 0,
            qualitative_rating TEXT,
            qualitative_summary TEXT,
            notes TEXT,
            source_json_path TEXT,
            metadata_json TEXT
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_openrouter_job_id
        ON openrouter_generations(provider_job_id)
        WHERE provider_job_id IS NOT NULL;

        CREATE INDEX IF NOT EXISTS idx_openrouter_recorded_at
        ON openrouter_generations(recorded_at);

        CREATE INDEX IF NOT EXISTS idx_openrouter_model
        ON openrouter_generations(model);

        CREATE INDEX IF NOT EXISTS idx_openrouter_slug
        ON openrouter_generations(slug);
        """
    )
    con.commit()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def maybe_read_text(path: Path | None) -> str | None:
    if not path or not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def upsert_generation(con: sqlite3.Connection, row: dict[str, Any]) -> None:
    provider_job_id = row.get("provider_job_id")
    if provider_job_id:
        existing = con.execute(
            "SELECT id FROM openrouter_generations WHERE provider_job_id = ?",
            (provider_job_id,),
        ).fetchone()
        if existing:
            update_keys = [key for key in sorted(row.keys()) if key != "provider_job_id"]
            assignments = ", ".join(f"{key} = ?" for key in update_keys)
            con.execute(
                f"""
                UPDATE openrouter_generations
                SET {assignments}
                WHERE provider_job_id = ?
                """,
                [row[key] for key in update_keys] + [provider_job_id],
            )
            con.commit()
            return

    keys = sorted(row.keys())
    placeholders = ", ".join("?" for _ in keys)
    con.execute(
        f"INSERT INTO openrouter_generations ({', '.join(keys)}) VALUES ({placeholders})",
        [row[key] for key in keys],
    )
    con.commit()


def record_video_job(args: argparse.Namespace) -> None:
    job_path = Path(args.job_json).expanduser().resolve()
    job = read_json(job_path)

    submit = job.get("submit") or {}
    status = job.get("status") or {}
    payload = job.get("payload") or {}
    prompt_path = Path(args.prompt_path).expanduser().resolve() if args.prompt_path else None

    row = {
        "provider_job_id": status.get("id") or submit.get("id"),
        "generation_id": status.get("generation_id"),
        "model": payload.get("model") or args.model,
        "modality": "video",
        "workflow": args.workflow,
        "slug": args.slug,
        "asset_pack_path": args.asset_pack,
        "prompt_path": str(prompt_path) if prompt_path else None,
        "prompt_text": maybe_read_text(prompt_path),
        "first_frame_path": args.first_frame,
        "last_frame_path": args.last_frame,
        "output_path": args.output,
        "status": status.get("status") or submit.get("status") or "unknown",
        "cost_usd": ((status.get("usage") or {}).get("cost")),
        "duration_seconds": payload.get("duration"),
        "resolution": payload.get("resolution"),
        "aspect_ratio": payload.get("aspect_ratio"),
        "retries": args.retries,
        "qualitative_rating": args.qualitative_rating,
        "qualitative_summary": args.qualitative_summary,
        "notes": args.notes,
        "source_json_path": str(job_path),
        "metadata_json": json.dumps(job, ensure_ascii=False),
    }

    con = connect()
    init_db(con)
    upsert_generation(con, row)
    print(f"Registrado job {row['provider_job_id']} em {DB_PATH}")


def record_manual(args: argparse.Namespace) -> None:
    con = connect()
    init_db(con)
    prompt_path = Path(args.prompt_path).expanduser().resolve() if args.prompt_path else None
    row = {
        "provider_job_id": args.provider_job_id,
        "generation_id": args.generation_id,
        "model": args.model,
        "modality": args.modality,
        "workflow": args.workflow,
        "slug": args.slug,
        "asset_pack_path": args.asset_pack,
        "prompt_path": str(prompt_path) if prompt_path else None,
        "prompt_text": args.prompt_text or maybe_read_text(prompt_path),
        "first_frame_path": args.first_frame,
        "last_frame_path": args.last_frame,
        "output_path": args.output,
        "status": args.status,
        "cost_usd": args.cost,
        "duration_seconds": args.duration,
        "resolution": args.resolution,
        "aspect_ratio": args.aspect_ratio,
        "retries": args.retries,
        "qualitative_rating": args.qualitative_rating,
        "qualitative_summary": args.qualitative_summary,
        "notes": args.notes,
        "source_json_path": args.source_json_path,
        "metadata_json": args.metadata_json,
    }
    upsert_generation(con, row)
    print(f"Registro manual salvo em {DB_PATH}")


def summary(args: argparse.Namespace) -> None:
    con = connect()
    init_db(con)
    since = (datetime.now(UTC) - timedelta(days=args.days)).strftime("%Y-%m-%d %H:%M:%S")
    rows = con.execute(
        """
        SELECT *
        FROM openrouter_generations
        WHERE recorded_at >= ?
        ORDER BY recorded_at DESC
        """,
        (since,),
    ).fetchall()
    if not rows:
        print("Nenhuma geracao registrada no periodo.")
        return

    total = len(rows)
    completed = [row for row in rows if row["status"] == "completed"]
    failed = [row for row in rows if row["status"] == "failed"]
    with_cost = [row for row in rows if row["cost_usd"] is not None]
    total_cost = sum(float(row["cost_usd"]) for row in with_cost)
    fx = None
    wallet = None
    try:
        fx = fetch_bcb_usd_brl()
    except Exception:
        fx = None
    try:
        wallet = fetch_openrouter_credits()
    except Exception:
        wallet = None

    print(f"Periodo: ultimos {args.days} dia(s)")
    print(f"Total de geracoes: {total}")
    print(f"Concluidas: {len(completed)}")
    print(f"Falhas: {len(failed)}")
    print(f"Custo total rastreado: US${total_cost:.4f}")
    if fx:
        print(f"Custo total rastreado em BRL: {format_brl(total_cost * fx['usd_brl'])}")
        print(f"Cambio USD/BRL: {fx['usd_brl']:.4f} ({fx['source']}, {fx['quoted_at']})")
    if wallet:
        print("\nCreditos OpenRouter:")
        print(f"- Total comprado: {wallet['total_credits']:.4f} creditos")
        print(f"- Total usado: {wallet['total_usage']:.4f} creditos")
        print(f"- Saldo restante: {wallet['remaining_credits']:.4f} creditos")
        if fx:
            print(f"- Total comprado em BRL: {format_brl(wallet['total_credits'] * fx['usd_brl'])}")
            print(f"- Total usado em BRL: {format_brl(wallet['total_usage'] * fx['usd_brl'])}")
            print(f"- Saldo restante em BRL: {format_brl(wallet['remaining_credits'] * fx['usd_brl'])}")

    by_modality = con.execute(
        """
        SELECT modality, COUNT(*) AS total, COALESCE(SUM(cost_usd), 0) AS cost
        FROM openrouter_generations
        WHERE recorded_at >= ?
        GROUP BY modality
        ORDER BY total DESC
        """,
        (since,),
    ).fetchall()
    print("\nPor modalidade:")
    for row in by_modality:
        print(f"- {row['modality']}: {row['total']} geracao(oes), US${float(row['cost']):.4f}")

    by_model = con.execute(
        """
        SELECT model, COUNT(*) AS total, COALESCE(SUM(cost_usd), 0) AS cost,
               AVG(cost_usd) AS avg_cost
        FROM openrouter_generations
        WHERE recorded_at >= ?
        GROUP BY model
        ORDER BY cost DESC, total DESC
        """,
        (since,),
    ).fetchall()
    print("\nPor modelo:")
    for row in by_model:
        avg = float(row["avg_cost"]) if row["avg_cost"] is not None else 0.0
        print(f"- {row['model']}: {row['total']} geracao(oes), US${float(row['cost']):.4f}, media US${avg:.4f}")

    by_rating = con.execute(
        """
        SELECT COALESCE(qualitative_rating, 'sem-avaliacao') AS rating,
               COUNT(*) AS total
        FROM openrouter_generations
        WHERE recorded_at >= ?
        GROUP BY COALESCE(qualitative_rating, 'sem-avaliacao')
        ORDER BY total DESC
        """,
        (since,),
    ).fetchall()
    print("\nAvaliacao qualitativa:")
    for row in by_rating:
        print(f"- {row['rating']}: {row['total']}")

    print("\nUltimos registros:")
    for row in rows[: min(args.limit, len(rows))]:
        cost = f"US${float(row['cost_usd']):.4f}" if row["cost_usd"] is not None else "sem custo"
        slug = row["slug"] or "-"
        print(f"- {row['recorded_at']} | {row['modality']} | {row['model']} | {row['status']} | {cost} | slug={slug}")


def estimate_seedance_tokens(duration: int, resolution: str) -> int | None:
    dims = VIDEO_RESOLUTION_DIMS.get(resolution)
    if not dims:
        return None
    width, height = dims
    return math.ceil((width * height * duration * 24) / 1024)


def forecast_video(args: argparse.Namespace) -> None:
    con = connect()
    init_db(con)
    avg_row = con.execute(
        """
        SELECT AVG(cost_usd) AS avg_cost
        FROM openrouter_generations
        WHERE modality = 'video'
          AND model = ?
          AND duration_seconds = ?
          AND resolution = ?
          AND status = 'completed'
          AND cost_usd IS NOT NULL
        """,
        (args.model, args.duration, args.resolution),
    ).fetchone()
    historical_avg = float(avg_row["avg_cost"]) if avg_row and avg_row["avg_cost"] is not None else None

    tokens = estimate_seedance_tokens(args.duration, args.resolution)
    rate = VIDEO_RATE_PER_MTOKEN.get(args.model)
    estimated_cost_per_video = None
    estimated_total_cost = None
    if tokens is not None and rate is not None:
        estimated_cost_per_video = (tokens / 1_000_000) * rate
        estimated_total_cost = estimated_cost_per_video * args.count

    forecast = Forecast(
        model=args.model,
        duration=args.duration,
        resolution=args.resolution,
        count=args.count,
        tokens_per_video=tokens,
        estimated_cost_per_video=estimated_cost_per_video,
        estimated_total_cost=estimated_total_cost,
        historical_avg_cost=historical_avg,
    )

    print(f"Modelo: {forecast.model}")
    print(f"Duracao: {forecast.duration}s")
    print(f"Resolucao: {forecast.resolution}")
    print(f"Quantidade: {forecast.count}")
    if forecast.tokens_per_video is not None:
        print(f"Tokens estimados por video: {forecast.tokens_per_video}")
    else:
        print("Tokens estimados por video: indisponivel para esta resolucao")
    if forecast.estimated_cost_per_video is not None:
        print(f"Custo teorico por video: US${forecast.estimated_cost_per_video:.4f}")
        print(f"Custo teorico total: US${forecast.estimated_total_cost:.4f}")
    else:
        print("Custo teorico: indisponivel para este modelo/resolucao")
    if forecast.historical_avg_cost is not None:
        print(f"Media historica para mesmas condicoes: US${forecast.historical_avg_cost:.4f}")
        print(f"Media historica total projetada: US${forecast.historical_avg_cost * forecast.count:.4f}")
    else:
        print("Media historica: sem dados suficientes")

    fx = None
    wallet = None
    try:
        fx = fetch_bcb_usd_brl()
    except Exception:
        fx = None
    try:
        wallet = fetch_openrouter_credits()
    except Exception:
        wallet = None

    if fx:
        print(f"Cambio USD/BRL: {fx['usd_brl']:.4f} ({fx['source']}, {fx['quoted_at']})")
        if forecast.estimated_cost_per_video is not None:
            print(f"Custo teorico por video em BRL: {format_brl(forecast.estimated_cost_per_video * fx['usd_brl'])}")
            print(f"Custo teorico total em BRL: {format_brl(forecast.estimated_total_cost * fx['usd_brl'])}")
        if forecast.historical_avg_cost is not None:
            print(f"Media historica por video em BRL: {format_brl(forecast.historical_avg_cost * fx['usd_brl'])}")
            print(f"Media historica total em BRL: {format_brl(forecast.historical_avg_cost * forecast.count * fx['usd_brl'])}")

    if wallet:
        print(f"Creditos totais na plataforma: {wallet['total_credits']:.4f}")
        print(f"Creditos usados: {wallet['total_usage']:.4f}")
        print(f"Creditos restantes: {wallet['remaining_credits']:.4f}")
        if fx:
            print(f"Saldo restante em BRL: {format_brl(wallet['remaining_credits'] * fx['usd_brl'])}")
        baseline_cost = forecast.historical_avg_cost or forecast.estimated_cost_per_video
        if baseline_cost:
            supported = int(wallet["remaining_credits"] // baseline_cost)
            print(f"Quantidade estimada de videos suportados pelo saldo atual: {supported}")
            if fx:
                remaining_after_batch = wallet["remaining_credits"] - (baseline_cost * forecast.count)
                print(f"Saldo estimado apos esta leva: {format_brl(remaining_after_batch * fx['usd_brl'])}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tracking local de geracoes OpenRouter")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Cria o banco SQLite").set_defaults(
        func=lambda _args: (init_db(connect()), print(f"Banco pronto em {DB_PATH}"))
    )

    record_video = sub.add_parser("record-video-job", help="Importa um job de video salvo em JSON")
    record_video.add_argument("--job-json", required=True)
    record_video.add_argument("--slug")
    record_video.add_argument("--workflow", default="manual")
    record_video.add_argument("--asset-pack")
    record_video.add_argument("--output")
    record_video.add_argument("--prompt-path")
    record_video.add_argument("--first-frame")
    record_video.add_argument("--last-frame")
    record_video.add_argument("--model")
    record_video.add_argument("--retries", type=int, default=0)
    record_video.add_argument("--qualitative-rating")
    record_video.add_argument("--qualitative-summary")
    record_video.add_argument("--notes")
    record_video.set_defaults(func=record_video_job)

    record_manual_parser = sub.add_parser("record-manual", help="Registra uma geracao manualmente")
    record_manual_parser.add_argument("--provider-job-id")
    record_manual_parser.add_argument("--generation-id")
    record_manual_parser.add_argument("--model", required=True)
    record_manual_parser.add_argument("--modality", required=True, choices=["image", "video", "text", "audio", "other"])
    record_manual_parser.add_argument("--workflow", default="manual")
    record_manual_parser.add_argument("--slug")
    record_manual_parser.add_argument("--asset-pack")
    record_manual_parser.add_argument("--prompt-path")
    record_manual_parser.add_argument("--prompt-text")
    record_manual_parser.add_argument("--first-frame")
    record_manual_parser.add_argument("--last-frame")
    record_manual_parser.add_argument("--output")
    record_manual_parser.add_argument("--status", default="completed")
    record_manual_parser.add_argument("--cost", type=float)
    record_manual_parser.add_argument("--duration", type=int)
    record_manual_parser.add_argument("--resolution")
    record_manual_parser.add_argument("--aspect-ratio")
    record_manual_parser.add_argument("--retries", type=int, default=0)
    record_manual_parser.add_argument("--qualitative-rating")
    record_manual_parser.add_argument("--qualitative-summary")
    record_manual_parser.add_argument("--notes")
    record_manual_parser.add_argument("--source-json-path")
    record_manual_parser.add_argument("--metadata-json")
    record_manual_parser.set_defaults(func=record_manual)

    summary_parser = sub.add_parser("summary", help="Resumo de geracoes e custos")
    summary_parser.add_argument("--days", type=int, default=30)
    summary_parser.add_argument("--limit", type=int, default=10)
    summary_parser.set_defaults(func=summary)

    forecast_parser = sub.add_parser("forecast-video", help="Projecao simples de custo para video")
    forecast_parser.add_argument("--model", required=True)
    forecast_parser.add_argument("--duration", type=int, required=True)
    forecast_parser.add_argument("--resolution", required=True)
    forecast_parser.add_argument("--count", type=int, default=1)
    forecast_parser.set_defaults(func=forecast_video)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
