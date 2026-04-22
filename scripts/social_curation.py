#!/usr/bin/env python3
"""
Importa exports oficiais de LinkedIn/Instagram e gera uma curadoria em Markdown.

O script foi feito para trabalhar com arquivos baixados manualmente das plataformas,
sem scraping e sem APIs privadas.

Usage:
    python3 scripts/social_curation.py import .referencias/social-exports/linkedin/export.zip --source linkedin
    python3 scripts/social_curation.py import .referencias/social-exports/instagram/export.zip --source instagram
    python3 scripts/social_curation.py report --days 90
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import shutil
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "social-curation.sqlite"
EXPORT_ROOT = ROOT / ".referencias" / "social-exports"
REPORT_DIR = ROOT / "curadorias"
URL_RE = re.compile(r"https?://[^\s<>'\")\]]+")


LINKEDIN_KIND_BY_FILENAME = {
    "saved items": "saved",
    "reactions": "reaction",
    "comments": "comment",
    "shares": "share",
    "instant reposts": "repost",
}

INSTAGRAM_KIND_HINTS = {
    "saved": "saved",
    "like": "like",
    "liked": "like",
    "likes": "like",
}


@dataclass(frozen=True)
class Item:
    source: str
    kind: str
    url: str
    date: str = ""
    title: str = ""
    text: str = ""
    author: str = ""
    author_handle: str = ""
    platform_post_id: str = ""
    raw_json: str = ""
    origin_file: str = ""

    @property
    def fingerprint(self) -> str:
        raw = f"{self.source}|{self.kind}|{self.url}|{self.date}|{self.text}|{self.author}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


EXTRA_COLUMNS = {
    "author": "TEXT",
    "author_handle": "TEXT",
    "platform_post_id": "TEXT",
    "raw_json": "TEXT",
    "ai_label": "TEXT",
    "ai_score": "REAL",
    "ai_reason": "TEXT",
    "ai_model": "TEXT",
    "ai_classified_at": "TEXT",
}


def ensure_columns(con: sqlite3.Connection) -> None:
    existing = {row[1] for row in con.execute("PRAGMA table_info(social_items)").fetchall()}
    for name, sql_type in EXTRA_COLUMNS.items():
        if name in existing:
            continue
        con.execute(f"ALTER TABLE social_items ADD COLUMN {name} {sql_type}")


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS social_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fingerprint TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            kind TEXT NOT NULL,
            url TEXT NOT NULL,
            date TEXT,
            title TEXT,
            text TEXT,
            author TEXT,
            author_handle TEXT,
            platform_post_id TEXT,
            raw_json TEXT,
            ai_label TEXT,
            ai_score REAL,
            ai_reason TEXT,
            ai_model TEXT,
            ai_classified_at TEXT,
            origin_file TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    ensure_columns(con)
    con.execute("CREATE INDEX IF NOT EXISTS idx_social_items_date ON social_items(date)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_social_items_source_kind ON social_items(source, kind)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_social_items_ai_label ON social_items(ai_label)")
    return con


def normalize_url(value: str) -> str:
    url = html.unescape(value.strip())
    url = url.rstrip(".,;")
    return url


def parse_date(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    if not text:
        return ""

    if text.isdigit():
        number = int(text)
        if number > 10_000_000_000:
            number = number // 1000
        try:
            return datetime.fromtimestamp(number, UTC).date().isoformat()
        except (OSError, ValueError):
            return ""

    candidates = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%b %d, %Y",
        "%B %d, %Y",
    ]
    clean = text.replace("Z", "+0000")
    clean = re.sub(r"([+-]\d\d):(\d\d)$", r"\1\2", clean)
    for fmt in candidates:
        try:
            return datetime.strptime(clean, fmt).date().isoformat()
        except ValueError:
            pass
    return text[:10] if re.match(r"\d{4}-\d{2}-\d{2}", text) else ""


def first_value(row: dict[str, str], names: Iterable[str]) -> str:
    normalized = {k.strip().lower(): v for k, v in row.items()}
    for name in names:
        value = normalized.get(name.lower())
        if value:
            return value.strip()
    return ""


def urls_from_text(text: str) -> list[str]:
    return [normalize_url(match.group(0)) for match in URL_RE.finditer(text or "")]


def linked_in_kind(path: Path) -> str:
    name = path.stem.lower().replace("_", " ").replace("-", " ")
    for needle, kind in LINKEDIN_KIND_BY_FILENAME.items():
        if needle in name:
            return kind
    return "item"


def instagram_kind(path: Path) -> str:
    name = path.as_posix().lower().replace("_", " ").replace("-", " ")
    for needle, kind in INSTAGRAM_KIND_HINTS.items():
        if needle in name:
            return kind
    return "item"


def extract_zip(path: Path) -> Path:
    target = Path(tempfile.mkdtemp(prefix="social-export-"))
    with zipfile.ZipFile(path) as zf:
        zf.extractall(target)
    return target


def iter_input_files(input_path: Path) -> Iterable[Path]:
    if input_path.is_file() and input_path.suffix.lower() == ".zip":
        extracted = extract_zip(input_path)
        yield from sorted(p for p in extracted.rglob("*") if p.is_file())
        shutil.rmtree(extracted, ignore_errors=True)
    elif input_path.is_file():
        yield input_path
    else:
        yield from sorted(p for p in input_path.rglob("*") if p.is_file())


def parse_linkedin_csv(path: Path) -> list[Item]:
    kind = linked_in_kind(path)
    items: list[Item] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = parse_date(first_value(row, ["Date", "Saved Date", "Creation Date", "Created At", "Time"]))
            title = first_value(row, ["Title", "Name", "Post Title", "Article Title"])
            text = first_value(row, ["Comment", "Text", "Share Commentary", "Reaction Type", "Content"])
            author = first_value(row, ["Author", "Actor", "Creator", "Profile Name"])
            author_handle = first_value(row, ["Author URL", "Actor URL", "Profile URL"])
            urls = []
            explicit = first_value(row, ["URL", "Link", "Post URL", "Article URL", "Permalink"])
            if explicit:
                urls.append(explicit)
            urls.extend(url for value in row.values() for url in urls_from_text(value or ""))
            for url in dict.fromkeys(normalize_url(url) for url in urls if url):
                items.append(Item("linkedin", kind, url, date, title, text, author, author_handle, "", "", path.name))
    return items


def walk_json(obj: Any, path: Path, kind: str, context: dict[str, str] | None = None) -> list[Item]:
    context = dict(context or {})
    items: list[Item] = []

    if isinstance(obj, dict):
        next_context = dict(context)
        for key, value in obj.items():
            key_l = str(key).lower()
            if any(part in key_l for part in ["timestamp", "date", "time"]):
                parsed = parse_date(value)
                if parsed:
                    next_context.setdefault("date", parsed)
            if any(part in key_l for part in ["title", "caption", "name"]):
                if isinstance(value, str) and value.strip():
                    next_context.setdefault("title", value.strip()[:240])
            if any(part in key_l for part in ["text", "comment", "caption"]):
                if isinstance(value, str) and value.strip():
                    next_context.setdefault("text", value.strip()[:500])
            if any(part in key_l for part in ["author", "username", "owner", "creator"]):
                if isinstance(value, str) and value.strip():
                    next_context.setdefault("author", value.strip()[:120])
            if any(part in key_l for part in ["id", "media_id", "pk"]):
                if isinstance(value, (str, int)):
                    next_context.setdefault("platform_post_id", str(value)[:120])

        for key, value in obj.items():
            if isinstance(value, str):
                for url in urls_from_text(value):
                    items.append(
                        Item(
                            "instagram",
                            kind,
                            url,
                            next_context.get("date", ""),
                            next_context.get("title", ""),
                            next_context.get("text", ""),
                            next_context.get("author", ""),
                            next_context.get("author_handle", ""),
                            next_context.get("platform_post_id", ""),
                            "",
                            path.name,
                        )
                    )
            else:
                items.extend(walk_json(value, path, kind, next_context))

    elif isinstance(obj, list):
        for value in obj:
            items.extend(walk_json(value, path, kind, context))

    return items


def parse_instagram_json(path: Path) -> list[Item]:
    kind = instagram_kind(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    return walk_json(data, path, kind)


def parse_text_file(path: Path, source: str) -> list[Item]:
    kind = instagram_kind(path) if source == "instagram" else linked_in_kind(path)
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except UnicodeDecodeError:
        return []
    return [Item(source, kind, url, "", "", "", "", "", "", "", path.name) for url in urls_from_text(text)]


def parse_file(path: Path, source: str) -> list[Item]:
    suffix = path.suffix.lower()
    if source == "linkedin" and suffix == ".csv":
        return parse_linkedin_csv(path)
    if source == "instagram" and suffix == ".json":
        return parse_instagram_json(path)
    if suffix in {".html", ".txt", ".json", ".csv"}:
        return parse_text_file(path, source)
    return []


def import_items(input_path: Path, source: str) -> tuple[int, int]:
    con = connect()
    found = 0
    inserted = 0
    for file_path in iter_input_files(input_path):
        for item in parse_file(file_path, source):
            found += 1
            cur = con.execute(
                """
                INSERT OR IGNORE INTO social_items
                (fingerprint, source, kind, url, date, title, text, author, author_handle, platform_post_id, raw_json, origin_file)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.fingerprint,
                    item.source,
                    item.kind,
                    item.url,
                    item.date,
                    item.title,
                    item.text,
                    item.author,
                    item.author_handle,
                    item.platform_post_id,
                    item.raw_json,
                    item.origin_file,
                ),
            )
            inserted += cur.rowcount
    con.commit()
    con.close()
    return found, inserted


def domain(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host.removeprefix("www.")


def report(days: int, limit: int, output: Path | None, label: str | None = None, only_classified: bool = False) -> Path:
    con = connect()
    since = (datetime.now(UTC) - timedelta(days=days)).date().isoformat()
    clauses = ["(COALESCE(date, '') = '' OR date >= ?)"]
    params: list[Any] = [since]
    if label:
        clauses.append("ai_label = ?")
        params.append(label)
    if only_classified:
        clauses.append("COALESCE(ai_label, '') <> ''")
    where_sql = " AND ".join(clauses)
    query = f"""
        SELECT source, kind, url, date, title, text, author, ai_label, origin_file
        FROM social_items
        WHERE {where_sql}
        ORDER BY COALESCE(date, '0000-00-00') DESC, id DESC
        LIMIT ?
    """
    params.append(limit)
    rows = con.execute(query, params).fetchall()
    con.close()

    now = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"# Curadoria social - {now}",
        "",
        f"Fonte: exports oficiais em `{EXPORT_ROOT.relative_to(ROOT)}` e capturas via navegador autenticado.",
        f"Recorte: últimos {days} dias, até {limit} itens.",
        "",
    ]

    grouped: dict[tuple[str, str], list[tuple]] = {}
    for row in rows:
        grouped.setdefault((row[0], row[1]), []).append(row)

    for (source, kind), group in sorted(grouped.items()):
        lines.extend([f"## {source.title()} / {kind}", ""])
        for _, _, url, date, title, text, author, ai_label, origin_file in group:
            label = title or domain(url) or url
            meta = " · ".join(part for part in [date, author, ai_label, origin_file] if part)
            lines.append(f"- [{label}]({url})" + (f" — {meta}" if meta else ""))
            if text and text != title:
                excerpt = " ".join(text.split())
                if len(excerpt) > 220:
                    excerpt = excerpt[:217].rstrip() + "..."
                lines.append(f"  Nota: {excerpt}")
        lines.append("")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    target = output or REPORT_DIR / f"{now}-curadoria-social.md"
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def init_dirs():
    for path in [
        EXPORT_ROOT / "linkedin",
        EXPORT_ROOT / "instagram",
        ROOT / "data",
        REPORT_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Pipeline local de curadoria social")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Cria pastas esperadas")

    import_parser = sub.add_parser("import", help="Importa ZIP/pasta/arquivo exportado")
    import_parser.add_argument("path", type=Path)
    import_parser.add_argument("--source", choices=["linkedin", "instagram"], required=True)

    report_parser = sub.add_parser("report", help="Gera Markdown de curadoria")
    report_parser.add_argument("--days", type=int, default=90)
    report_parser.add_argument("--limit", type=int, default=200)
    report_parser.add_argument("--output", type=Path)
    report_parser.add_argument("--label", help="Filtra por rótulo de IA (ex.: ai-tools, design, produto)")
    report_parser.add_argument("--only-classified", action="store_true", help="Inclui apenas itens já classificados")

    args = parser.parse_args()

    if args.command == "init":
        init_dirs()
        print(f"Pastas criadas em {EXPORT_ROOT}")
        return

    if args.command == "import":
        init_dirs()
        found, inserted = import_items(args.path, args.source)
        print(f"Itens encontrados: {found}")
        print(f"Itens novos: {inserted}")
        print(f"Banco: {DB_PATH}")
        return

    if args.command == "report":
        init_dirs()
        target = report(args.days, args.limit, args.output, args.label, args.only_classified)
        print(f"Relatório gerado: {target}")


if __name__ == "__main__":
    main()
