#!/usr/bin/env python3
"""Send the weekly analytics report to the authenticated Gmail account."""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import html
import json
import pathlib
import subprocess
import sys
from email.message import EmailMessage


ROOT = pathlib.Path(__file__).resolve().parents[1]
WEEKLY_DIR = ROOT / "data" / "analytics" / "weekly"
DEFAULT_FROM = "bolivar@alencastro.com.br"


def current_week() -> str:
    today = dt.datetime.now().date()
    iso = today.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def load_report(week: str) -> dict:
    path = WEEKLY_DIR / f"{week}.json"
    if not path.exists():
        sys.exit(f"Missing weekly report: {path.relative_to(ROOT).as_posix()}")
    return json.loads(path.read_text(encoding="utf-8"))


def value_total(rows: list[dict], metric: str) -> int | float:
    return sum(row.get(metric, 0) or 0 for row in rows)


def fmt(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.0f}" if value.is_integer() else f"{value:.2f}"
    return str(value)


def html_table(rows: list[dict], columns: list[tuple[str, str]], limit: int = 8) -> str:
    if not rows:
        return '<p class="muted">Sem dados no periodo.</p>'

    head = "".join(f"<th>{html.escape(label)}</th>" for label, _ in columns)
    body_rows = []
    for row in rows[:limit]:
        cells = "".join(f"<td>{html.escape(fmt(row.get(key, '')))}</td>" for _, key in columns)
        body_rows.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


def render_html(report: dict) -> str:
    ga4 = report["ga4"]
    clarity = report["clarity"]
    overview = ga4["overview_by_date"]

    cards = [
        ("Usuários", value_total(overview, "activeUsers")),
        ("Sessões", value_total(overview, "sessions")),
        ("Pageviews", value_total(overview, "screenPageViews")),
        ("Eventos", value_total(overview, "eventCount")),
    ]
    card_html = "".join(
        f'<div class="card"><span>{html.escape(label)}</span><strong>{html.escape(fmt(value))}</strong></div>'
        for label, value in cards
    )

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ margin: 0; padding: 24px; background: #f4f1ec; color: #1f1d1a; font: 15px/1.5 Arial, sans-serif; }}
    main {{ max-width: 760px; margin: 0 auto; background: #fffdf8; border: 1px solid #ded8cc; padding: 28px; }}
    h1 {{ font-size: 24px; margin: 0 0 6px; }}
    h2 {{ font-size: 17px; margin: 28px 0 10px; border-top: 1px solid #e6dfd4; padding-top: 18px; }}
    p {{ margin: 0 0 12px; }}
    .muted {{ color: #6f675d; }}
    .cards {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin: 20px 0; }}
    .card {{ border: 1px solid #e1d9cd; padding: 12px; background: #faf7f1; }}
    .card span {{ display: block; color: #6f675d; font-size: 12px; }}
    .card strong {{ display: block; font-size: 22px; margin-top: 4px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
    th, td {{ border-bottom: 1px solid #e6dfd4; padding: 8px 6px; text-align: left; vertical-align: top; }}
    th {{ font-size: 12px; color: #6f675d; text-transform: uppercase; letter-spacing: .03em; }}
    td {{ font-size: 13px; }}
  </style>
</head>
<body>
  <main>
    <h1>Analytics semanal - {html.escape(report["week"])}</h1>
    <p class="muted">{html.escape(report["date_range"]["start_date"])} a {html.escape(report["date_range"]["end_date"])}</p>
    <div class="cards">{card_html}</div>

    <h2>Páginas mais vistas</h2>
    {html_table(ga4["top_pages"], [("Página", "pagePath"), ("Título", "pageTitle"), ("Views", "screenPageViews"), ("Usuários", "activeUsers")])}

    <h2>Eventos do portfólio</h2>
    {html_table(ga4["portfolio_events"], [("Evento", "eventName"), ("Total", "eventCount")])}

    <h2>Leitura</h2>
    {html_table(ga4["read_depth"], [("Tipo", "customEvent:content_type"), ("Slug", "customEvent:content_slug"), ("%", "customEvent:read_percent"), ("Total", "eventCount")])}

    <h2>Cliques sociais</h2>
    {html_table(ga4["social_clicks"], [("Rede", "customEvent:social_network"), ("Origem", "customEvent:content_slug"), ("Total", "eventCount")])}

    <h2>Cliques de contato</h2>
    {html_table(ga4["contact_clicks"], [("Tipo", "customEvent:contact_type"), ("Origem", "customEvent:content_slug"), ("Total", "eventCount")])}

    <h2>Links externos</h2>
    {html_table(ga4["outbound_clicks"], [("Domínio", "customEvent:link_domain"), ("Origem", "customEvent:content_slug"), ("Total", "eventCount")])}

    <h2>Clarity</h2>
    <p class="muted">Snapshots locais usados: {html.escape(fmt(clarity["snapshot_count"]))}</p>
    {html_table(clarity["top_urls_by_traffic"], [("URL", "label"), ("Sessões", "value")])}
  </main>
</body>
</html>
"""


def render_text(report: dict, markdown_path: pathlib.Path | None) -> str:
    overview = report["ga4"]["overview_by_date"]
    lines = [
        f"Analytics semanal - {report['week']}",
        f"{report['date_range']['start_date']} a {report['date_range']['end_date']}",
        "",
        f"Usuários ativos: {fmt(value_total(overview, 'activeUsers'))}",
        f"Sessões: {fmt(value_total(overview, 'sessions'))}",
        f"Pageviews: {fmt(value_total(overview, 'screenPageViews'))}",
        f"Eventos: {fmt(value_total(overview, 'eventCount'))}",
    ]
    if markdown_path:
        lines.extend(["", f"Relatório local: {markdown_path.relative_to(ROOT).as_posix()}"])
    return "\n".join(lines)


def profile_email() -> str:
    try:
        result = subprocess.run(
            ["gws", "gmail", "users", "getProfile", "--params", '{"userId":"me"}'],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return DEFAULT_FROM
    lines = [line for line in result.stdout.splitlines() if not line.startswith("Using keyring backend:")]
    try:
        return json.loads("\n".join(lines)).get("emailAddress", DEFAULT_FROM)
    except json.JSONDecodeError:
        return DEFAULT_FROM


def build_message(sender: str, recipient: str, subject: str, text_body: str, html_body: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")
    return message


def send_message(message: EmailMessage) -> dict:
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii").rstrip("=")
    result = subprocess.run(
        [
            "gws",
            "gmail",
            "users",
            "messages",
            "send",
            "--params",
            '{"userId":"me"}',
            "--json",
            json.dumps({"raw": raw}),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    lines = [line for line in result.stdout.splitlines() if not line.startswith("Using keyring backend:")]
    return json.loads("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="Send weekly analytics report by Gmail using gws")
    parser.add_argument("--week", default=current_week(), help="ISO week, for example 2026-W24")
    parser.add_argument("--to", help="Recipient. Defaults to the authenticated Gmail account.")
    parser.add_argument("--from-email", help="Sender. Defaults to the authenticated Gmail account.")
    parser.add_argument("--dry-run", action="store_true", help="Write HTML preview instead of sending")
    args = parser.parse_args()

    report = load_report(args.week)
    markdown_path = WEEKLY_DIR / f"{args.week}.md"
    sender = args.from_email or profile_email()
    recipient = args.to or sender
    subject = f"Analytics semanal - {args.week}"
    html_body = render_html(report)
    text_body = render_text(report, markdown_path if markdown_path.exists() else None)
    message = build_message(sender, recipient, subject, text_body, html_body)

    if args.dry_run:
        preview_path = WEEKLY_DIR / f"{args.week}.email.html"
        preview_path.write_text(html_body, encoding="utf-8")
        print(preview_path.relative_to(ROOT).as_posix())
        return 0

    response = send_message(message)
    print(json.dumps({"id": response.get("id"), "threadId": response.get("threadId")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
