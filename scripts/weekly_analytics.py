#!/usr/bin/env python3
"""Collect and summarize weekly portfolio analytics from GA4 and Clarity."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import subprocess
import sys
import urllib.parse
from collections import defaultdict
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
SNAPSHOT_DIR = ROOT / "data" / "analytics" / "snapshots"
WEEKLY_DIR = ROOT / "data" / "analytics" / "weekly"
CLARITY_API_URL = "https://www.clarity.ms/export-data/api/v1/project-live-insights"
CLARITY_TOKEN_KEY = "CLARITY_DATA_EXPORT_TOKEN"
GA4_PROPERTY_ID = "501542723"
GA4_PROPERTY = f"properties/{GA4_PROPERTY_ID}"
GA4_RUN_REPORT_URL = f"https://analyticsdata.googleapis.com/v1beta/{GA4_PROPERTY}:runReport"
DEFAULT_CLARITY_DIMENSIONS = [["URL"], ["Source"], ["Device"]]


def today_local() -> dt.date:
    return dt.datetime.now().date()


def read_env_value(key: str) -> str:
    if not ENV_PATH.exists():
        return ""

    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() == key:
            return value.strip().strip("\"'")
    return ""


def run_json(command: list[str], *, input_json: dict[str, Any] | None = None) -> dict[str, Any] | list[Any]:
    payload = json.dumps(input_json) if input_json is not None else None
    result = subprocess.run(command, input=payload, check=True, capture_output=True, text=True)
    return json.loads(result.stdout or "{}")


def gcloud_access_token() -> str:
    try:
        result = subprocess.run(
            ["gcloud", "auth", "application-default", "print-access-token"],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        sys.exit("gcloud was not found in PATH.")
    except subprocess.CalledProcessError as error:
        sys.exit(f"Could not get Google ADC token: {error.stderr.strip()}")
    return result.stdout.strip()


def ga4_report(
    token: str,
    *,
    start_date: str,
    end_date: str,
    metrics: list[str],
    dimensions: list[str] | None = None,
    limit: int = 25,
    dimension_filter: dict[str, Any] | None = None,
    order_bys: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "dateRanges": [{"startDate": start_date, "endDate": end_date}],
        "metrics": [{"name": name} for name in metrics],
        "limit": limit,
    }
    if dimensions:
        body["dimensions"] = [{"name": name} for name in dimensions]
    if dimension_filter:
        body["dimensionFilter"] = dimension_filter
    if order_bys:
        body["orderBys"] = order_bys

    payload = run_json(
        [
            "curl",
            "-sS",
            "-X",
            "POST",
            "-H",
            f"Authorization: Bearer {token}",
            "-H",
            "Content-Type: application/json",
            "--data",
            "@-",
            GA4_RUN_REPORT_URL,
        ],
        input_json=body,
    )
    if isinstance(payload, dict) and "error" in payload:
        raise RuntimeError(json.dumps(payload["error"], ensure_ascii=False))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Unexpected GA4 response: {payload!r}")
    return payload


def clarity_export(token: str, *, days: int, dimensions: list[str]) -> list[dict[str, Any]]:
    params: dict[str, str] = {"numOfDays": str(days)}
    for index, dimension in enumerate(dimensions[:3], start=1):
        params[f"dimension{index}"] = dimension

    url = f"{CLARITY_API_URL}?{urllib.parse.urlencode(params)}"
    payload = run_json(
        [
            "curl",
            "-sS",
            "--location",
            url,
            "--header",
            "Content-Type: application/json",
            "--header",
            f"Authorization: Bearer {token}",
        ]
    )
    if isinstance(payload, dict) and "error" in payload:
        raise RuntimeError(json.dumps(payload["error"], ensure_ascii=False))
    if not isinstance(payload, list):
        raise RuntimeError(f"Unexpected Clarity response: {payload!r}")
    return payload


def rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    dimensions = [item["name"] for item in report.get("dimensionHeaders", [])]
    metrics = [item["name"] for item in report.get("metricHeaders", [])]
    output = []

    for row in report.get("rows", []):
        item: dict[str, Any] = {}
        for index, name in enumerate(dimensions):
            values = row.get("dimensionValues", [])
            item[name] = values[index].get("value", "") if index < len(values) else ""
        for index, name in enumerate(metrics):
            values = row.get("metricValues", [])
            raw = values[index].get("value", "0") if index < len(values) else "0"
            item[name] = number(raw)
        output.append(item)
    return output


def number(value: str) -> int | float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0
    if numeric.is_integer():
        return int(numeric)
    return numeric


def iso_week_bounds(week: str | None) -> tuple[str, str, str]:
    if week:
        year_text, week_text = week.split("-W", 1)
        monday = dt.date.fromisocalendar(int(year_text), int(week_text), 1)
    else:
        now = today_local()
        iso = now.isocalendar()
        monday = dt.date.fromisocalendar(iso.year, iso.week, 1)

    sunday = monday + dt.timedelta(days=6)
    end = min(sunday, today_local())
    iso = monday.isocalendar()
    return f"{iso.year}-W{iso.week:02d}", monday.isoformat(), end.isoformat()


def event_filter(event_name: str) -> dict[str, Any]:
    return {
        "filter": {
            "fieldName": "eventName",
            "stringFilter": {"matchType": "EXACT", "value": event_name},
        }
    }


def metric_order(metric: str, desc: bool = True) -> list[dict[str, Any]]:
    return [{"metric": {"metricName": metric}, "desc": desc}]


def collect_ga4(start_date: str, end_date: str) -> dict[str, Any]:
    token = gcloud_access_token()
    reports: dict[str, Any] = {}

    specs = {
        "overview_by_date": {
            "dimensions": ["date"],
            "metrics": ["activeUsers", "sessions", "screenPageViews", "eventCount"],
            "limit": 60,
        },
        "top_pages": {
            "dimensions": ["pagePath", "pageTitle"],
            "metrics": ["screenPageViews", "activeUsers", "eventCount"],
            "limit": 30,
            "order_bys": metric_order("screenPageViews"),
        },
        "traffic_sources": {
            "dimensions": ["sessionSource", "sessionMedium"],
            "metrics": ["sessions", "activeUsers"],
            "limit": 30,
            "order_bys": metric_order("sessions"),
        },
        "portfolio_events": {
            "dimensions": ["eventName"],
            "metrics": ["eventCount"],
            "limit": 30,
            "order_bys": metric_order("eventCount"),
        },
    }

    for name, spec in specs.items():
        reports[name] = ga4_report(
            token,
            start_date=start_date,
            end_date=end_date,
            dimensions=spec["dimensions"],
            metrics=spec["metrics"],
            limit=spec["limit"],
            order_bys=spec.get("order_bys"),
        )

    custom_specs = {
        "content_performance": {
            "dimensions": ["customEvent:content_type", "customEvent:content_slug"],
            "metrics": ["eventCount"],
            "filter": event_filter("portfolio_page_context"),
        },
        "read_depth": {
            "dimensions": ["customEvent:content_type", "customEvent:content_slug", "customEvent:read_percent"],
            "metrics": ["eventCount"],
            "filter": event_filter("portfolio_read_depth"),
        },
        "social_clicks": {
            "dimensions": ["customEvent:social_network", "customEvent:content_slug"],
            "metrics": ["eventCount"],
            "filter": event_filter("portfolio_social_click"),
        },
        "contact_clicks": {
            "dimensions": ["customEvent:contact_type", "customEvent:content_slug"],
            "metrics": ["eventCount"],
            "filter": event_filter("portfolio_contact_click"),
        },
        "outbound_clicks": {
            "dimensions": ["customEvent:link_domain", "customEvent:content_slug"],
            "metrics": ["eventCount"],
            "filter": event_filter("portfolio_outbound_click"),
        },
        "internal_content_clicks": {
            "dimensions": ["customEvent:target_content_type", "customEvent:target_content_slug"],
            "metrics": ["eventCount"],
            "filter": event_filter("portfolio_content_click"),
        },
    }

    for name, spec in custom_specs.items():
        try:
            reports[name] = ga4_report(
                token,
                start_date=start_date,
                end_date=end_date,
                dimensions=spec["dimensions"],
                metrics=spec["metrics"],
                limit=50,
                dimension_filter=spec["filter"],
                order_bys=metric_order("eventCount"),
            )
        except RuntimeError as exc:
            reports[name] = {"error": str(exc), "rows": []}

    return reports


def collect_clarity(days: int) -> dict[str, Any]:
    token = read_env_value(CLARITY_TOKEN_KEY)
    if not token:
        return {"error": f"Missing {CLARITY_TOKEN_KEY} in {ENV_PATH}"}

    reports: dict[str, Any] = {}
    for dimensions in DEFAULT_CLARITY_DIMENSIONS:
        key = "_".join(dim.lower() for dim in dimensions)
        try:
            reports[key] = clarity_export(token, days=days, dimensions=dimensions)
        except RuntimeError as exc:
            reports[key] = {"error": str(exc)}
    return reports


def write_snapshot(start_date: str, end_date: str, clarity_days: int) -> pathlib.Path:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc)
    path = SNAPSHOT_DIR / f"{now.strftime('%Y-%m-%dT%H%M%SZ')}.json"
    payload = {
        "collected_at": now.isoformat(),
        "ga4_property": GA4_PROPERTY,
        "date_range": {"start_date": start_date, "end_date": end_date},
        "clarity_days": clarity_days,
        "ga4": collect_ga4(start_date, end_date),
        "clarity": collect_clarity(clarity_days),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_clarity_snapshots(start_date: str, end_date: str) -> list[dict[str, Any]]:
    if not SNAPSHOT_DIR.exists():
        return []

    start = dt.date.fromisoformat(start_date)
    end = dt.date.fromisoformat(end_date)
    snapshots = []

    for path in sorted(SNAPSHOT_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            collected = dt.datetime.fromisoformat(payload.get("collected_at", "").replace("Z", "+00:00")).date()
        except (ValueError, json.JSONDecodeError):
            continue
        if start <= collected <= end:
            payload["_path"] = path.relative_to(ROOT).as_posix()
            snapshots.append(payload)
    return snapshots


def clarity_metric_rows(snapshot: dict[str, Any], report_name: str, metric_name: str) -> list[dict[str, Any]]:
    report = snapshot.get("clarity", {}).get(report_name, [])
    if not isinstance(report, list):
        return []
    for metric in report:
        if metric.get("metricName") == metric_name:
            return metric.get("information", [])
    return []


def top_clarity_rows(snapshots: list[dict[str, Any]], report_name: str, metric_name: str, field: str, count_key: str) -> list[dict[str, Any]]:
    totals: dict[str, float] = defaultdict(float)
    for snapshot in snapshots:
        for row in clarity_metric_rows(snapshot, report_name, metric_name):
            key = row.get(field) or row.get(field.lower()) or "(not set)"
            totals[key] += float(row.get(count_key, 0) or 0)
    return [{"label": key, "value": value} for key, value in sorted(totals.items(), key=lambda item: item[1], reverse=True)]


def report_payload(week: str | None) -> dict[str, Any]:
    week_id, start_date, end_date = iso_week_bounds(week)
    ga4 = collect_ga4(start_date, end_date)
    snapshots = load_clarity_snapshots(start_date, end_date)

    summary = {
        "week": week_id,
        "date_range": {"start_date": start_date, "end_date": end_date},
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "ga4": {
            "overview_by_date": rows(ga4["overview_by_date"]),
            "top_pages": rows(ga4["top_pages"]),
            "traffic_sources": rows(ga4["traffic_sources"]),
            "portfolio_events": rows(ga4["portfolio_events"]),
            "content_performance": rows(ga4.get("content_performance", {})),
            "read_depth": rows(ga4.get("read_depth", {})),
            "social_clicks": rows(ga4.get("social_clicks", {})),
            "contact_clicks": rows(ga4.get("contact_clicks", {})),
            "outbound_clicks": rows(ga4.get("outbound_clicks", {})),
            "internal_content_clicks": rows(ga4.get("internal_content_clicks", {})),
        },
        "clarity": {
            "snapshot_count": len(snapshots),
            "snapshots": [snapshot["_path"] for snapshot in snapshots],
            "top_urls_by_traffic": top_clarity_rows(snapshots, "url", "Traffic", "Url", "totalSessionCount")[:20],
            "top_sources_by_traffic": top_clarity_rows(snapshots, "source", "Traffic", "Source", "totalSessionCount")[:20],
            "devices_by_traffic": top_clarity_rows(snapshots, "device", "Traffic", "Device", "totalSessionCount")[:20],
            "rage_click_urls": top_clarity_rows(snapshots, "url", "RageClickCount", "Url", "sessionsCount")[:20],
            "dead_click_urls": top_clarity_rows(snapshots, "url", "DeadClickCount", "Url", "sessionsCount")[:20],
        },
    }
    return summary


def total(rows_: list[dict[str, Any]], metric: str) -> int | float:
    return sum(row.get(metric, 0) or 0 for row in rows_)


def table_lines(items: list[dict[str, Any]], columns: list[tuple[str, str]], limit: int = 10) -> list[str]:
    if not items:
        return ["_Sem dados no período._"]

    header = "| " + " | ".join(label for label, _ in columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, separator]
    for item in items[:limit]:
        values = [str(item.get(key, "")) for _, key in columns]
        lines.append("| " + " | ".join(value.replace("|", "\\|") for value in values) + " |")
    return lines


def render_markdown(payload: dict[str, Any]) -> str:
    ga4 = payload["ga4"]
    overview = ga4["overview_by_date"]
    lines = [
        f"# Analytics semanal - {payload['week']}",
        "",
        f"Período: {payload['date_range']['start_date']} a {payload['date_range']['end_date']}",
        "",
        "## Resumo GA4",
        "",
        f"- Usuários ativos: {total(overview, 'activeUsers')}",
        f"- Sessões: {total(overview, 'sessions')}",
        f"- Visualizações de página: {total(overview, 'screenPageViews')}",
        f"- Eventos: {total(overview, 'eventCount')}",
        "",
        "## Páginas Mais Vistas",
        "",
        *table_lines(
            ga4["top_pages"],
            [("Página", "pagePath"), ("Título", "pageTitle"), ("Views", "screenPageViews"), ("Usuários", "activeUsers")],
        ),
        "",
        "## Eventos do Portfólio",
        "",
        *table_lines(ga4["portfolio_events"], [("Evento", "eventName"), ("Total", "eventCount")]),
        "",
        "## Leitura",
        "",
        *table_lines(
            ga4["read_depth"],
            [("Tipo", "customEvent:content_type"), ("Slug", "customEvent:content_slug"), ("%", "customEvent:read_percent"), ("Total", "eventCount")],
        ),
        "",
        "## Cliques Sociais e Contato",
        "",
        *table_lines(
            ga4["social_clicks"],
            [("Rede", "customEvent:social_network"), ("Origem", "customEvent:content_slug"), ("Total", "eventCount")],
        ),
        "",
        *table_lines(
            ga4["contact_clicks"],
            [("Tipo", "customEvent:contact_type"), ("Origem", "customEvent:content_slug"), ("Total", "eventCount")],
        ),
        "",
        "## Links Externos",
        "",
        *table_lines(
            ga4["outbound_clicks"],
            [("Domínio", "customEvent:link_domain"), ("Origem", "customEvent:content_slug"), ("Total", "eventCount")],
        ),
        "",
        "## Clarity",
        "",
        f"- Snapshots locais usados: {payload['clarity']['snapshot_count']}",
        "",
        "### URLs por Tráfego",
        "",
        *table_lines(payload["clarity"]["top_urls_by_traffic"], [("URL", "label"), ("Sessões", "value")]),
        "",
        "### Fontes por Tráfego",
        "",
        *table_lines(payload["clarity"]["top_sources_by_traffic"], [("Fonte", "label"), ("Sessões", "value")]),
        "",
        "### Dispositivos",
        "",
        *table_lines(payload["clarity"]["devices_by_traffic"], [("Dispositivo", "label"), ("Sessões", "value")]),
        "",
        "## Próximas Leituras",
        "",
        "- Verificar conteúdos com leitura 90% alta e transformar em posts sociais.",
        "- Verificar páginas com muitos cliques externos ou sociais para entender intenção.",
        "- Cruzar URLs com sinais de fricção do Clarity quando houver rage/dead clicks.",
        "",
    ]
    return "\n".join(lines)


def write_weekly_report(week: str | None) -> tuple[pathlib.Path, pathlib.Path]:
    payload = report_payload(week)
    WEEKLY_DIR.mkdir(parents=True, exist_ok=True)
    json_path = WEEKLY_DIR / f"{payload['week']}.json"
    md_path = WEEKLY_DIR / f"{payload['week']}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect and summarize weekly analytics")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect_parser = subparsers.add_parser("collect", help="Collect a local GA4 + Clarity snapshot")
    collect_parser.add_argument("--start-date", default="7daysAgo", help="GA4 start date, YYYY-MM-DD or relative")
    collect_parser.add_argument("--end-date", default="today", help="GA4 end date, YYYY-MM-DD or relative")
    collect_parser.add_argument("--clarity-days", type=int, default=3, choices=[1, 2, 3], help="Clarity lookback")

    report_parser = subparsers.add_parser("report", help="Generate a weekly JSON and Markdown report")
    report_parser.add_argument("--week", help="ISO week, for example 2026-W24. Defaults to current week.")

    args = parser.parse_args()
    if args.command == "collect":
        path = write_snapshot(args.start_date, args.end_date, args.clarity_days)
        print(path.relative_to(ROOT).as_posix())
        return 0

    json_path, md_path = write_weekly_report(args.week)
    print(json_path.relative_to(ROOT).as_posix())
    print(md_path.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
