#!/usr/bin/env python3
"""
Collect transcript, comments, and replies from a YouTube video URL, or
transcript from an Instagram Reel/Post URL, and build local research artifacts
for editorial reuse.

The workflow prefers public captions first for YouTube. If captions are
unavailable, it can fall back to audio extraction with yt-dlp + ffmpeg and
speech-to-text via OpenRouter. For Instagram, the workflow uses yt-dlp metadata
plus audio fallback only. DeepSeek is reserved for transcript cleanup and
research analysis, not for the raw speech-to-text step itself.

Usage:
    python3 youtube-research/scripts/collect_video_research.py 'https://www.youtube.com/watch?v=VIDEO_ID'
    python3 youtube-research/scripts/collect_video_research.py 'https://www.instagram.com/rndyrbrts/reel/DWpSK4uDhIO/'
    python3 youtube-research/scripts/collect_video_research.py 'https://youtu.be/VIDEO_ID' --lang pt --force-stt
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import os
import re
import shutil
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter
from html import unescape
from pathlib import Path
from typing import Any

try:
    import certifi

    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except Exception:
    SSL_CONTEXT = ssl.create_default_context()


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ROOT = REPO_ROOT
ENV_FILE = REPO_ROOT / ".env"
DATA_ROOT = REPO_ROOT / "youtube-research" / "videos"
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
WATCH_BASE = "https://www.youtube.com/watch"
TIMEDTEXT_BASE = "https://www.youtube.com/api/timedtext"
YT_DLP_JSON_CMD = [sys.executable, "-m", "yt_dlp", "--no-playlist", "--skip-download", "--dump-single-json"]
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_AUDIO_URL = "https://openrouter.ai/api/v1/audio/transcriptions"
DEFAULT_STT_MODEL = "openai/whisper-large-v3"
DEFAULT_ANALYSIS_MODEL = "deepseek/deepseek-chat"
DEFAULT_CLEANUP_MODEL = "deepseek/deepseek-chat"
DEFAULT_CHUNK_SECONDS = 480
DEFAULT_OVERLAP_SECONDS = 2
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

STOPWORDS = {
    "a", "ao", "aos", "aquela", "aquele", "aqueles", "as", "ate", "com", "como", "da", "das",
    "de", "delas", "dele", "deles", "depois", "do", "dos", "e", "ela", "elas", "ele", "eles",
    "em", "entre", "era", "essa", "esse", "esta", "estao", "este", "eu", "foi", "isso", "isto",
    "ja", "la", "mais", "mas", "me", "mesmo", "meu", "minha", "muito", "na", "nao", "nas", "nem",
    "no", "nos", "nossa", "nosso", "num", "numa", "o", "os", "ou", "para", "pela", "pelas",
    "pelo", "pelos", "por", "pra", "pro", "que", "se", "sem", "ser", "seu", "sua", "sobre",
    "tambem", "te", "tem", "ter", "to", "tu", "um", "uma", "umas", "uns", "vai", "voce", "voces",
    "able", "about", "after", "all", "also", "an", "and", "any", "are", "as", "at", "be", "been",
    "but", "by", "can", "did", "do", "does", "for", "from", "get", "got", "had", "has", "have",
    "how", "i", "if", "in", "into", "is", "it", "its", "just", "me", "more", "my", "not", "of",
    "on", "or", "our", "out", "really", "so", "that", "the", "their", "them", "there", "they",
    "this", "to", "too", "up", "use", "very", "was", "we", "what", "when", "where", "which",
    "who", "why", "with", "would", "you", "your",
}

QUESTION_HINTS = (
    "como",
    "por que",
    "porque",
    "qual",
    "quais",
    "when",
    "what",
    "why",
    "how",
    "where",
    "which",
)

OPPORTUNITY_PATTERNS = (
    r"\b(faz|fa[aç]a|poderia|podia|queria|gostaria|seria legal|parte 2|part 2|next video|more about|talk about|cover)\b",
    r"\b(como|how to|tutorial|passo a passo|guia)\b",
    r"\b(duvida|d[úu]vida|nao entendi|n[aã]o entendi|nao consegui|n[aã]o consegui|dificuldade|erro|problema)\b",
)


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return {**env, **os.environ}


def http_get_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, context=SSL_CONTEXT, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def http_get_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, context=SSL_CONTEXT, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="YouTube URL, Instagram URL, or raw YouTube video id")
    parser.add_argument("--lang", default="", help="Preferred transcript language code. Default: auto-detect")
    parser.add_argument("--max-comments", type=int, default=0, help="Limit top-level comments. 0 = all")
    parser.add_argument("--output-dir", help="Optional output directory. Default: youtube-research/videos/<titulo>--<video_id>")
    parser.add_argument("--force-stt", action="store_true", help="Skip public captions and force audio transcription.")
    parser.add_argument("--chunk-seconds", type=int, default=DEFAULT_CHUNK_SECONDS, help=f"Audio chunk size in seconds. Default: {DEFAULT_CHUNK_SECONDS}")
    parser.add_argument("--chunk-overlap-seconds", type=int, default=DEFAULT_OVERLAP_SECONDS, help=f"Chunk overlap in seconds. Default: {DEFAULT_OVERLAP_SECONDS}")
    parser.add_argument("--stt-model", default=DEFAULT_STT_MODEL, help=f"OpenRouter STT model. Default: {DEFAULT_STT_MODEL}")
    parser.add_argument("--analysis-model", default=DEFAULT_ANALYSIS_MODEL, help=f"OpenRouter chat model for insight extraction. Default: {DEFAULT_ANALYSIS_MODEL}")
    parser.add_argument("--cleanup-model", default=DEFAULT_CLEANUP_MODEL, help=f"OpenRouter chat model for transcript cleanup. Default: {DEFAULT_CLEANUP_MODEL}")
    parser.add_argument("--skip-ai-analysis", action="store_true", help="Skip the DeepSeek/OpenRouter analysis pass.")
    parser.add_argument("--skip-cleanup", action="store_true", help="Skip transcript cleanup after STT.")
    parser.add_argument(
        "--cookies-from-browser",
        default="",
        help=(
            "Passa --cookies-from-browser ao yt-dlp. Exemplos: 'chrome' ou "
            "'chrome:/tmp/chrome-social-capture'."
        ),
    )
    parser.add_argument(
        "--cookies-file",
        default="",
        help="Passa --cookies <arquivo> ao yt-dlp.",
    )
    return parser.parse_args()


def build_yt_dlp_cookie_args(cookies_from_browser: str = "", cookies_file: str = "") -> list[str]:
    args: list[str] = []
    browser = (cookies_from_browser or "").strip()
    cookie_file = (cookies_file or "").strip()
    if browser:
        args += ["--cookies-from-browser", browser]
    if cookie_file:
        args += ["--cookies", cookie_file]
    return args


def normalize_language_code(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    text = text.replace("_", "-")
    text = text.split(",")[0].strip()
    if not text:
        return ""
    base = text.split("-")[0].lower()
    return base if re.fullmatch(r"[a-z]{2,3}", base) else ""


def resolve_preferred_language(cli_lang: str, video: dict[str, Any]) -> tuple[str, str]:
    explicit = normalize_language_code(cli_lang)
    if explicit:
        return explicit, "cli"

    audio_lang = normalize_language_code(str(video.get("default_audio_language", "")))
    if audio_lang:
        return audio_lang, "video.default_audio_language"

    default_lang = normalize_language_code(str(video.get("default_language", "")))
    if default_lang:
        return default_lang, "video.default_language"

    return "", "stt_auto_detect"


def slugify_title(value: str, max_length: int = 80) -> str:
    text = (value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    if not text:
        return "video"
    return text[:max_length].rstrip("-")


def detect_platform(value: str) -> str:
    parsed = urllib.parse.urlparse(value.strip())
    host = parsed.netloc.lower()
    if re.fullmatch(r"[\w-]{11}", value.strip()):
        return "youtube"
    if "instagram.com" in host:
        return "instagram"
    return "youtube"


def default_video_output_dir(video: dict[str, Any]) -> Path:
    slug = slugify_title(str(video.get("title", "")))
    video_id = str(video.get("video_id", "")).strip() or "unknown"
    return DATA_ROOT / f"{slug}--{video_id}"


def extract_video_id(value: str) -> str:
    value = value.strip()
    if re.fullmatch(r"[\w-]{11}", value):
        return value
    parsed = urllib.parse.urlparse(value)
    if parsed.netloc in {"youtu.be", "www.youtu.be"}:
        candidate = parsed.path.strip("/").split("/")[0]
        if re.fullmatch(r"[\w-]{11}", candidate):
            return candidate
    if "youtube.com" in parsed.netloc:
        query_video = urllib.parse.parse_qs(parsed.query).get("v", [""])[0]
        if re.fullmatch(r"[\w-]{11}", query_video):
            return query_video
        parts = [part for part in parsed.path.split("/") if part]
        for index, part in enumerate(parts):
            if part in {"embed", "shorts", "live"} and index + 1 < len(parts):
                candidate = parts[index + 1]
                if re.fullmatch(r"[\w-]{11}", candidate):
                    return candidate
    raise SystemExit(f"Erro: nao consegui extrair o video_id de: {value}")


def youtube_api_url(path: str, **params: Any) -> str:
    query = urllib.parse.urlencode({k: v for k, v in params.items() if v not in (None, "")})
    return f"{YOUTUBE_API_BASE}/{path}?{query}"


def api_get(path: str, api_key: str, **params: Any) -> dict[str, Any]:
    url = youtube_api_url(path, key=api_key, **params)
    try:
        return http_get_json(url)
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Erro na API do YouTube ({exc.code}): {payload}") from exc


def fetch_web_metadata(url: str, cookies_from_browser: str = "", cookies_file: str = "") -> dict[str, Any]:
    ensure_dependency("yt-dlp", [sys.executable, "-m", "yt_dlp"])
    cmd = YT_DLP_JSON_CMD + build_yt_dlp_cookie_args(cookies_from_browser, cookies_file) + [url]
    proc = run_command(cmd)
    if proc.returncode != 0:
        raise RuntimeError(f"Falha ao ler metadados com yt-dlp:\n{proc.stderr or proc.stdout}")
    try:
        info = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"yt-dlp retornou JSON invalido:\n{proc.stdout[:1000]}") from exc

    title = info.get("title") or info.get("fulltitle") or info.get("id") or "video"
    video_id = str(info.get("id") or "").strip() or str(info.get("display_id") or "").strip() or "unknown"
    duration_seconds = int(float(info.get("duration") or 0) or 0)
    timestamp = info.get("timestamp")
    published_at = ""
    if timestamp:
        try:
            from datetime import datetime, timezone

            published_at = datetime.fromtimestamp(float(timestamp), tz=timezone.utc).isoformat()
        except Exception:
            published_at = ""

    return {
        "video_id": video_id,
        "title": title,
        "channel_title": info.get("uploader") or info.get("channel") or info.get("artist") or "",
        "channel_id": info.get("uploader_id") or info.get("channel_id") or "",
        "published_at": published_at,
        "description": info.get("description") or "",
        "tags": info.get("tags") or [],
        "default_language": info.get("language") or "",
        "default_audio_language": info.get("language") or "",
        "category_id": str(info.get("category") or ""),
        "duration": str(info.get("duration_string") or ""),
        "duration_seconds": duration_seconds,
        "view_count": int(info.get("view_count") or 0),
        "like_count": int(info.get("like_count") or 0),
        "comment_count": int(info.get("comment_count") or 0),
        "url": info.get("webpage_url") or url,
        "platform": (info.get("extractor_key") or info.get("extractor") or "web").lower(),
        "source_url": url,
        "uploader": info.get("uploader") or "",
        "availability": info.get("availability") or "",
    }


def openrouter_request_json(url: str, body: dict[str, Any], api_key: str) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://bolivaralencastro.com.br",
            "X-Title": "portfolio-bolivaralencastro",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=240, context=SSL_CONTEXT) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Erro OpenRouter ({exc.code}): {payload}") from exc


def run_command(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=False,
    )


def ensure_dependency(name: str, check_cmd: list[str]) -> None:
    if len(check_cmd) == 1 and shutil.which(check_cmd[0]):
        return
    if len(check_cmd) >= 2 and check_cmd[0] == sys.executable and check_cmd[1:3] == ["-m", "yt_dlp"]:
        proc = run_command([sys.executable, "-m", "yt_dlp", "--version"])
        if proc.returncode == 0:
            return
        raise RuntimeError(f"Dependencia ausente: {name}")


def parse_iso8601_duration(value: str) -> int:
    pattern = re.compile(
        r"^P(?:(?P<days>\d+)D)?T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?$"
    )
    match = pattern.match(value or "")
    if not match:
        return 0
    parts = {key: int(number or 0) for key, number in match.groupdict().items()}
    return (
        parts["days"] * 86400
        + parts["hours"] * 3600
        + parts["minutes"] * 60
        + parts["seconds"]
    )


def fetch_video(api_key: str, video_id: str) -> dict[str, Any]:
    payload = api_get(
        "videos",
        api_key,
        part="snippet,statistics,contentDetails",
        id=video_id,
    )
    items = payload.get("items", [])
    if not items:
        raise SystemExit(f"Erro: nenhum video encontrado para {video_id}")
    item = items[0]
    snippet = item.get("snippet", {})
    statistics = item.get("statistics", {})
    content_details = item.get("contentDetails", {})
    duration_raw = content_details.get("duration", "")
    return {
        "video_id": video_id,
        "title": snippet.get("title", ""),
        "channel_title": snippet.get("channelTitle", ""),
        "channel_id": snippet.get("channelId", ""),
        "published_at": snippet.get("publishedAt", ""),
        "description": snippet.get("description", ""),
        "tags": snippet.get("tags", []),
        "default_language": snippet.get("defaultLanguage", ""),
        "default_audio_language": snippet.get("defaultAudioLanguage", ""),
        "category_id": snippet.get("categoryId", ""),
        "duration": duration_raw,
        "duration_seconds": parse_iso8601_duration(duration_raw),
        "view_count": int(statistics.get("viewCount", 0) or 0),
        "like_count": int(statistics.get("likeCount", 0) or 0),
        "comment_count": int(statistics.get("commentCount", 0) or 0),
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "platform": "youtube",
    }


def simplify_comment(snippet: dict[str, Any], reply_count: int = 0) -> dict[str, Any]:
    return {
        "comment_id": snippet.get("id", ""),
        "author": snippet.get("authorDisplayName", ""),
        "author_channel_url": snippet.get("authorChannelUrl", ""),
        "published_at": snippet.get("publishedAt", ""),
        "updated_at": snippet.get("updatedAt", ""),
        "like_count": int(snippet.get("likeCount", 0) or 0),
        "text": snippet.get("textDisplay") or snippet.get("textOriginal") or "",
        "reply_count": reply_count,
    }


def fetch_replies(api_key: str, parent_id: str) -> list[dict[str, Any]]:
    replies: list[dict[str, Any]] = []
    page_token = ""
    while True:
        payload = api_get(
            "comments",
            api_key,
            part="snippet",
            parentId=parent_id,
            maxResults=100,
            pageToken=page_token,
            textFormat="plainText",
        )
        for item in payload.get("items", []):
            snippet = item.get("snippet", {})
            replies.append(
                {
                    "comment_id": item.get("id", ""),
                    "author": snippet.get("authorDisplayName", ""),
                    "author_channel_url": snippet.get("authorChannelUrl", ""),
                    "published_at": snippet.get("publishedAt", ""),
                    "updated_at": snippet.get("updatedAt", ""),
                    "like_count": int(snippet.get("likeCount", 0) or 0),
                    "text": snippet.get("textDisplay") or snippet.get("textOriginal") or "",
                    "parent_id": snippet.get("parentId", parent_id),
                }
            )
        page_token = payload.get("nextPageToken", "")
        if not page_token:
            break
    return replies


def fetch_comments(api_key: str, video_id: str, max_comments: int) -> list[dict[str, Any]]:
    threads: list[dict[str, Any]] = []
    page_token = ""
    remaining = max_comments if max_comments > 0 else None

    while True:
        page_size = 100
        if remaining is not None:
            if remaining <= 0:
                break
            page_size = min(page_size, remaining)

        payload = api_get(
            "commentThreads",
            api_key,
            part="snippet,replies",
            videoId=video_id,
            maxResults=page_size,
            pageToken=page_token,
            order="relevance",
            textFormat="plainText",
        )

        items = payload.get("items", [])
        for item in items:
            top = item.get("snippet", {}).get("topLevelComment", {})
            top_snippet = top.get("snippet", {})
            top_id = top.get("id", "")
            total_reply_count = int(item.get("snippet", {}).get("totalReplyCount", 0) or 0)
            embedded_replies = item.get("replies", {}).get("comments", [])

            replies = [
                {
                    "comment_id": reply.get("id", ""),
                    "author": reply.get("snippet", {}).get("authorDisplayName", ""),
                    "author_channel_url": reply.get("snippet", {}).get("authorChannelUrl", ""),
                    "published_at": reply.get("snippet", {}).get("publishedAt", ""),
                    "updated_at": reply.get("snippet", {}).get("updatedAt", ""),
                    "like_count": int(reply.get("snippet", {}).get("likeCount", 0) or 0),
                    "text": reply.get("snippet", {}).get("textDisplay") or reply.get("snippet", {}).get("textOriginal") or "",
                    "parent_id": reply.get("snippet", {}).get("parentId", top_id),
                }
                for reply in embedded_replies
            ]

            if total_reply_count > len(replies):
                replies = fetch_replies(api_key, top_id)

            threads.append(
                {
                    "top_level": simplify_comment(top_snippet, reply_count=total_reply_count),
                    "replies": replies,
                }
            )

        if remaining is not None:
            remaining -= len(items)

        page_token = payload.get("nextPageToken", "")
        if not page_token or not items:
            break

    return threads


def extract_player_response(html_text: str) -> dict[str, Any]:
    patterns = [
        r"ytInitialPlayerResponse\s*=\s*(\{.+?\})\s*;",
        r"var\s+ytInitialPlayerResponse\s*=\s*(\{.+?\})\s*;",
    ]
    for pattern in patterns:
        match = re.search(pattern, html_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
    raise RuntimeError("Nao consegui localizar ytInitialPlayerResponse na pagina do video.")


def choose_caption_track(caption_tracks: list[dict[str, Any]], preferred_lang: str) -> dict[str, Any] | None:
    if not caption_tracks:
        return None
    preferred_lang = (preferred_lang or "").lower()
    if not preferred_lang:
        return caption_tracks[0]
    exact = [track for track in caption_tracks if track.get("languageCode", "").lower() == preferred_lang]
    if exact:
        return exact[0]
    prefix = [track for track in caption_tracks if track.get("languageCode", "").lower().startswith(preferred_lang)]
    if prefix:
        return prefix[0]
    return caption_tracks[0]


def parse_json3_transcript(payload: dict[str, Any]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    for event in payload.get("events", []):
        start_ms = event.get("tStartMs")
        duration_ms = event.get("dDurationMs")
        segs = event.get("segs")
        if start_ms is None or not segs:
            continue
        text = "".join(seg.get("utf8", "") for seg in segs)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue
        segments.append(
            {
                "start_ms": int(start_ms),
                "duration_ms": int(duration_ms or 0),
                "text": unescape(text),
                "source": "public_captions",
            }
        )
    return segments


def parse_xml_transcript(xml_text: str, *, source: str) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_text)
    segments: list[dict[str, Any]] = []
    for node in root.findall("text"):
        text = re.sub(r"\s+", " ", "".join(node.itertext())).strip()
        if not text:
            continue
        start_seconds = float(node.attrib.get("start", "0") or 0)
        duration_seconds = float(node.attrib.get("dur", "0") or 0)
        segments.append(
            {
                "start_ms": int(start_seconds * 1000),
                "duration_ms": int(duration_seconds * 1000),
                "text": unescape(text),
                "source": source,
            }
        )
    return segments


def fetch_timedtext_tracks(video_id: str) -> list[dict[str, str]]:
    params = urllib.parse.urlencode({"type": "list", "v": video_id})
    try:
        payload = http_get_text(f"{TIMEDTEXT_BASE}?{params}")
    except Exception:
        return []
    if not payload.strip():
        return []
    try:
        root = ET.fromstring(payload)
    except ET.ParseError:
        return []
    tracks: list[dict[str, str]] = []
    for node in root.findall("track"):
        tracks.append(
            {
                "lang_code": node.attrib.get("lang_code", ""),
                "lang_original": node.attrib.get("lang_original", ""),
                "lang_translated": node.attrib.get("lang_translated", ""),
                "name": node.attrib.get("name", ""),
                "kind": node.attrib.get("kind", ""),
            }
        )
    return tracks


def choose_timedtext_track(tracks: list[dict[str, str]], preferred_lang: str) -> dict[str, str] | None:
    if not tracks:
        return None
    preferred_lang = (preferred_lang or "").lower()
    if not preferred_lang:
        return tracks[0]
    exact = [track for track in tracks if track.get("lang_code", "").lower() == preferred_lang]
    if exact:
        return exact[0]
    prefix = [track for track in tracks if track.get("lang_code", "").lower().startswith(preferred_lang)]
    if prefix:
        return prefix[0]
    return tracks[0]


def fetch_transcript_from_timedtext(video_id: str, preferred_lang: str) -> tuple[list[dict[str, Any]], dict[str, Any]] | None:
    tracks = fetch_timedtext_tracks(video_id)
    track = choose_timedtext_track(tracks, preferred_lang)
    if not track:
        return None

    params = {"v": video_id, "lang": track.get("lang_code", ""), "fmt": "srv3"}
    if track.get("name"):
        params["name"] = track["name"]
    if track.get("kind"):
        params["kind"] = track["kind"]

    transcript_xml = http_get_text(f"{TIMEDTEXT_BASE}?{urllib.parse.urlencode(params)}")
    segments = parse_xml_transcript(transcript_xml, source="public_captions")
    meta = {
        "status": "ok" if segments else "empty",
        "language_code": track.get("lang_code", ""),
        "track_name": track.get("lang_original", "") or track.get("lang_code", ""),
        "is_auto_generated": track.get("kind", "") == "asr",
        "source": "timedtext",
    }
    return segments, meta


def fetch_public_transcript(video_id: str, preferred_lang: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    timedtext_result = fetch_transcript_from_timedtext(video_id, preferred_lang)
    if timedtext_result is not None and timedtext_result[0]:
        return timedtext_result

    watch_url = f"{WATCH_BASE}?v={video_id}&hl={urllib.parse.quote(preferred_lang or 'en')}"
    html_text = http_get_text(watch_url)
    player = extract_player_response(html_text)
    captions = (
        player.get("captions", {})
        .get("playerCaptionsTracklistRenderer", {})
        .get("captionTracks", [])
    )
    if not captions:
        return [], {"status": "unavailable", "reason": "No public captions exposed by the video."}

    track = choose_caption_track(captions, preferred_lang)
    if not track:
        return [], {"status": "unavailable", "reason": "No matching caption track found."}

    base_url = track.get("baseUrl", "")
    language_code = track.get("languageCode", "")
    track_name = track.get("name", {}).get("simpleText", "") or language_code
    if not base_url:
        return [], {"status": "unavailable", "reason": "Caption track found without baseUrl."}

    try:
        transcript_payload = http_get_json(base_url + "&fmt=json3")
        segments = parse_json3_transcript(transcript_payload)
    except Exception:
        transcript_xml = http_get_text(base_url)
        segments = parse_xml_transcript(transcript_xml, source="public_captions")

    status = "ok" if segments else "empty"
    meta = {
        "status": status,
        "language_code": language_code,
        "track_name": track_name,
        "is_auto_generated": "kind=asr" in base_url,
        "source": "watch-page",
    }
    return segments, meta


def download_audio(video_url: str, work_dir: Path, cookies_from_browser: str = "", cookies_file: str = "") -> Path:
    ensure_dependency("ffmpeg", ["ffmpeg"])
    ensure_dependency("yt-dlp", [sys.executable, "-m", "yt_dlp"])
    cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--no-playlist",
        "-f",
        "bestaudio/best",
        "-o",
        str(work_dir / "source.%(ext)s"),
        "--print",
        "after_move:filepath",
    ]
    cmd += build_yt_dlp_cookie_args(cookies_from_browser, cookies_file)
    cmd += [video_url]
    proc = run_command(cmd, cwd=work_dir)
    if proc.returncode != 0:
        raise RuntimeError(f"Falha ao baixar audio com yt-dlp:\n{proc.stderr or proc.stdout}")
    lines = [line.strip() for line in (proc.stdout or "").splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("yt-dlp nao retornou o caminho do audio baixado.")
    path = Path(lines[-1])
    if not path.exists():
        raise RuntimeError(f"Audio baixado nao encontrado: {path}")
    return path


def ffprobe_duration_seconds(audio_path: Path) -> float:
    proc = run_command(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ]
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Falha ao obter duracao do audio:\n{proc.stderr or proc.stdout}")
    return float((proc.stdout or "0").strip() or 0)


def build_chunk_plan(total_seconds: float, chunk_seconds: int, overlap_seconds: int) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    if total_seconds <= 0:
        return plan
    if chunk_seconds <= 0:
        raise RuntimeError("chunk_seconds precisa ser > 0")
    num_chunks = max(1, math.ceil(total_seconds / chunk_seconds))
    for index in range(num_chunks):
        nominal_start = index * chunk_seconds
        start = 0 if index == 0 else max(0, nominal_start - overlap_seconds)
        end = min(total_seconds, (index + 1) * chunk_seconds)
        if index < num_chunks - 1:
            end = min(total_seconds, end + overlap_seconds)
        duration = max(0.1, end - start)
        plan.append(
            {
                "index": index,
                "start_seconds": round(start, 3),
                "duration_seconds": round(duration, 3),
            }
        )
    return plan


def render_audio_chunks(source_audio: Path, chunk_dir: Path, chunk_seconds: int, overlap_seconds: int) -> list[dict[str, Any]]:
    ensure_dependency("ffmpeg", ["ffmpeg"])
    ensure_dependency("ffprobe", ["ffprobe"])
    total_seconds = ffprobe_duration_seconds(source_audio)
    chunk_dir.mkdir(parents=True, exist_ok=True)
    plan = build_chunk_plan(total_seconds, chunk_seconds, overlap_seconds)
    for chunk in plan:
        output_path = chunk_dir / f"chunk-{chunk['index']:03d}.wav"
        proc = run_command(
            [
                "ffmpeg",
                "-y",
                "-ss",
                str(chunk["start_seconds"]),
                "-i",
                str(source_audio),
                "-t",
                str(chunk["duration_seconds"]),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                str(output_path),
            ]
        )
        if proc.returncode != 0:
            raise RuntimeError(f"Falha ao renderizar chunk {chunk['index']}:\n{proc.stderr or proc.stdout}")
        chunk["path"] = str(output_path)
        chunk["size_bytes"] = output_path.stat().st_size
    return plan


def transcribe_audio_chunk(audio_path: Path, api_key: str, model: str, language: str) -> tuple[str, dict[str, Any]]:
    audio_bytes = audio_path.read_bytes()
    body = {
        "model": model,
        "input_audio": {
            "data": base64.b64encode(audio_bytes).decode("ascii"),
            "format": "wav",
        }
    }
    if language:
        body["language"] = language
    payload = openrouter_request_json(OPENROUTER_AUDIO_URL, body, api_key)
    text = (payload.get("text") or payload.get("transcript") or "").strip()
    if not text:
        raise RuntimeError(f"Transcricao vazia para {audio_path.name}: {payload}")
    usage = payload.get("usage") or {}
    return text, {"response": payload, "usage": usage}


def normalize_join_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def merge_overlapping_text(previous: str, current: str) -> str:
    previous = normalize_join_text(previous)
    current = normalize_join_text(current)
    if not previous:
        return current
    if not current:
        return previous

    prev_words = previous.split()
    curr_words = current.split()
    max_overlap = min(40, len(prev_words), len(curr_words))
    best = 0
    for size in range(max_overlap, 4, -1):
        if [word.lower() for word in prev_words[-size:]] == [word.lower() for word in curr_words[:size]]:
            best = size
            break
    if best:
        return " ".join(prev_words + curr_words[best:])
    return f"{previous} {current}".strip()


def cleanup_transcript_text(raw_text: str, api_key: str, model: str, language: str) -> tuple[str, dict[str, Any]]:
    language_instruction = (
        f"Mantenha o idioma principal em {language}. "
        if language
        else "Mantenha o idioma original da fala. "
    )
    prompt = (
        "Revise a transcricao abaixo sem mudar o significado. "
        + "Corrija pontuacao, capitalizacao e quebras obvias de ASR. "
        + "Nao resuma, nao reescreva em outro tom e nao invente palavras ausentes. "
        + language_instruction
        + "Retorne apenas o texto revisado.\n\n"
        + f"TRANSCRICAO:\n{raw_text}"
    )
    body = {
        "model": model,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": "Voce limpa transcricoes ASR preservando o significado exato.",
            },
            {"role": "user", "content": prompt},
        ],
    }
    payload = openrouter_request_json(OPENROUTER_CHAT_URL, body, api_key)
    text = (
        payload.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )
    if not text:
        raise RuntimeError(f"Limpeza de transcript sem texto: {payload}")
    return text, payload


def transcribe_via_audio_fallback(
    video: dict[str, Any],
    language: str,
    output_dir: Path,
    openrouter_api_key: str,
    stt_model: str,
    cleanup_model: str,
    chunk_seconds: int,
    overlap_seconds: int,
    skip_cleanup: bool,
    cookies_from_browser: str = "",
    cookies_file: str = "",
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    work_dir = output_dir / "_audio_work"
    chunk_dir = work_dir / "chunks"
    work_dir.mkdir(parents=True, exist_ok=True)

    source_audio = download_audio(
        video["url"],
        work_dir,
        cookies_from_browser=cookies_from_browser,
        cookies_file=cookies_file,
    )
    chunk_plan = render_audio_chunks(source_audio, chunk_dir, chunk_seconds, overlap_seconds)

    raw_joined = ""
    chunk_outputs: list[dict[str, Any]] = []
    segments: list[dict[str, Any]] = []

    for chunk in chunk_plan:
        chunk_path = Path(chunk["path"])
        text, meta = transcribe_audio_chunk(chunk_path, openrouter_api_key, stt_model, language)
        raw_joined = merge_overlapping_text(raw_joined, text)
        chunk_output = {
            **chunk,
            "transcript_text": text,
            "usage": meta.get("usage", {}),
            "model": stt_model,
        }
        chunk_outputs.append(chunk_output)
        segments.append(
            {
                "start_ms": int(float(chunk["start_seconds"]) * 1000),
                "duration_ms": int(float(chunk["duration_seconds"]) * 1000),
                "text": text,
                "source": "audio_stt_chunk",
                "chunk_index": chunk["index"],
            }
        )

    final_text = raw_joined
    cleanup_payload: dict[str, Any] | None = None
    if final_text and not skip_cleanup:
        final_text, cleanup_payload = cleanup_transcript_text(final_text, openrouter_api_key, cleanup_model, language)

    transcript_segments = [
        {
            "start_ms": 0,
            "duration_ms": int(video.get("duration_seconds", 0) * 1000),
            "text": final_text,
            "source": "audio_stt_merged",
        }
    ] if final_text else segments

    meta = {
        "status": "ok" if final_text or segments else "unavailable",
        "language_code": language,
        "track_name": "OpenRouter audio transcription",
        "is_auto_generated": False,
        "source": "audio_stt",
        "stt_model": stt_model,
        "cleanup_model": cleanup_model if cleanup_payload else "",
        "chunk_seconds": chunk_seconds,
        "chunk_overlap_seconds": overlap_seconds,
        "chunk_count": len(chunk_outputs),
        "audio_path": str(source_audio),
    }
    artifacts = {
        "source_audio_path": str(source_audio),
        "chunks": chunk_outputs,
        "raw_merged_transcript": raw_joined,
        "cleaned_transcript": final_text,
        "cleanup_response": cleanup_payload or {},
    }
    return transcript_segments, meta, artifacts


def iter_all_comment_texts(comment_threads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for thread in comment_threads:
        top_level = thread.get("top_level", {})
        if top_level:
            entries.append(
                {
                    "scope": "top_level",
                    "text": top_level.get("text", ""),
                    "likes": int(top_level.get("like_count", 0) or 0),
                    "author": top_level.get("author", ""),
                }
            )
        for reply in thread.get("replies", []):
            entries.append(
                {
                    "scope": "reply",
                    "text": reply.get("text", ""),
                    "likes": int(reply.get("like_count", 0) or 0),
                    "author": reply.get("author", ""),
                }
            )
    return entries


def normalize_comment_text(text: str) -> str:
    return re.sub(r"\s+", " ", unescape(text or "")).strip()


def build_summary(
    video: dict[str, Any],
    transcript_segments: list[dict[str, Any]],
    transcript_meta: dict[str, Any],
    comment_threads: list[dict[str, Any]],
) -> dict[str, Any]:
    entries = iter_all_comment_texts(comment_threads)
    normalized_entries = [{**entry, "text": normalize_comment_text(entry["text"])} for entry in entries if entry.get("text")]

    question_candidates = [
        entry for entry in normalized_entries
        if "?" in entry["text"] or entry["text"].lower().startswith(QUESTION_HINTS)
    ]
    opportunity_candidates = [
        entry for entry in normalized_entries
        if any(re.search(pattern, entry["text"], re.IGNORECASE) for pattern in OPPORTUNITY_PATTERNS)
    ]

    tokens = []
    for entry in normalized_entries:
        words = re.findall(r"[A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9_-]{2,}", entry["text"].lower())
        tokens.extend(word for word in words if word not in STOPWORDS)

    top_keywords = [{"term": term, "count": count} for term, count in Counter(tokens).most_common(20)]
    top_comments = sorted(normalized_entries, key=lambda item: item["likes"], reverse=True)[:10]
    top_questions = sorted(question_candidates, key=lambda item: item["likes"], reverse=True)[:12]
    top_opportunities = sorted(opportunity_candidates, key=lambda item: item["likes"], reverse=True)[:12]
    total_replies = sum(len(thread.get("replies", [])) for thread in comment_threads)

    transcript_text = "\n".join(segment["text"] for segment in transcript_segments).strip()
    transcript_word_count = len(re.findall(r"\S+", transcript_text))

    return {
        "video_id": video["video_id"],
        "title": video["title"],
        "transcript": {
            "status": transcript_meta.get("status", "unavailable"),
            "language_code": transcript_meta.get("language_code", ""),
            "language_resolution": transcript_meta.get("language_resolution", ""),
            "segment_count": len(transcript_segments),
            "word_count": transcript_word_count,
            "source": transcript_meta.get("source", ""),
            "stt_model": transcript_meta.get("stt_model", ""),
        },
        "counts": {
            "top_level_comments": len(comment_threads),
            "replies": total_replies,
            "all_comment_entries": len(normalized_entries),
        },
        "top_keywords": top_keywords,
        "top_comments": top_comments,
        "top_questions": top_questions,
        "content_opportunities": top_opportunities,
    }


def generate_ai_insights(
    video: dict[str, Any],
    transcript_text: str,
    summary: dict[str, Any],
    comment_threads: list[dict[str, Any]],
    api_key: str,
    model: str,
) -> dict[str, Any]:
    sampled_threads = []
    for thread in comment_threads[:20]:
        sampled_threads.append(
            {
                "top_level": thread.get("top_level", {}),
                "replies": thread.get("replies", [])[:4],
            }
        )

    payload = {
        "video": {
            "title": video.get("title", ""),
            "channel_title": video.get("channel_title", ""),
            "description": video.get("description", "")[:3000],
            "url": video.get("url", ""),
        },
        "summary": summary,
        "sampled_threads": sampled_threads,
        "transcript_excerpt": transcript_text[:16000],
    }
    prompt = (
        "Analise o material abaixo e retorne JSON estrito. "
        "Objetivo: transformar transcript e comentarios de um video "
        "em aprendizado complementar de alta utilidade sobre o conteudo original do video. "
        "Priorize o que os comentarios acrescentam ao assunto: duvidas reais, "
        "pedidos de aprofundamento, exemplos concretos, contrapontos, limites do argumento, "
        "lacunas de explicacao e pontos que merecem continuidade. "
        "Retorne exatamente este formato JSON: "
        '{"core_themes":[{"title":"","why_it_matters":""}],'
        '"complementary_learning":[{"topic":"","what_comments_add":"","evidence":""}],'
        '"open_loops":[{"question":"","why_unresolved":"","evidence":""}],'
        '"practical_extensions":[{"topic":"","why_useful":"","evidence":""}],'
        '"counterpoints_or_tensions":[{"point":"","why_it_matters":"","evidence":""}],'
        '"examples_from_audience":[{"example":"","why_it_matters":"","evidence":""}],'
        '"audience_questions":[{"question":"","evidence":""}],'
        '"content_ideas":[{"title":"","angle":"","evidence":""}],'
        '"objections_or_pains":[{"point":"","evidence":""}],'
        '"language_to_reuse":[""],'
        '"blind_spots":[""],'
        '"recommended_next_piece":{"format":"","title":"","reason":""},'
        '"learning_summary":{"what_the_video_teaches":"","what_the_comments_add":"","best_next_step_for_learning":""}}. '
        "Regras: "
        "1) nao repita apenas o transcript; extraia valor adicional vindo da audiencia; "
        "2) use evidencia concreta de comentario ou reply sempre que possivel; "
        "3) se faltar transcript, use comentarios e metadados sem inventar fatos; "
        "4) pense como pesquisador tentando complementar o video para quem quer aprender melhor o tema.\n\n"
        f"DADOS:\n{json.dumps(payload, ensure_ascii=False)}"
    )
    body = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": "Voce transforma sinais de audiencia em pesquisa editorial acionavel com saida JSON estrita.",
            },
            {"role": "user", "content": prompt},
        ],
    }
    response = openrouter_request_json(OPENROUTER_CHAT_URL, body, api_key)
    content = (
        response.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", content)
        if not match:
            raise RuntimeError(f"Resposta DeepSeek sem JSON valido: {content[:500]}")
        parsed = json.loads(match.group(0))
    parsed["_meta"] = {"model": model, "raw_response": response}
    return parsed


def build_report(
    video: dict[str, Any],
    transcript_meta: dict[str, Any],
    summary: dict[str, Any],
    ai_insights: dict[str, Any] | None = None,
) -> str:
    lines = [
        f"# Research: {video['title']}",
        "",
        f"- Plataforma: {video.get('platform', 'n/d')}",
        f"- Video: {video['url']}",
        f"- Canal: {video['channel_title']}",
        f"- Publicado em: {video['published_at'] or 'n/d'}",
        f"- Duracao: {video.get('duration_seconds', 0)}s",
        f"- Views: {video['view_count']}",
        f"- Likes: {video['like_count']}",
        f"- Comentarios reportados: {video['comment_count']}",
        "",
        "## Coleta",
        "",
        f"- Transcript: {transcript_meta.get('status', 'unavailable')}",
        f"- Fonte do transcript: {transcript_meta.get('source', 'n/d')}",
        f"- Idioma do transcript: {transcript_meta.get('language_code', 'n/d') or 'n/d'}",
        f"- Resolucao do idioma: {transcript_meta.get('language_resolution', 'n/d') or 'n/d'}",
        f"- Modelo STT: {transcript_meta.get('stt_model', 'n/d') or 'n/d'}",
        f"- Comentarios top-level coletados: {summary['counts']['top_level_comments']}",
        f"- Respostas coletadas: {summary['counts']['replies']}",
        "",
        "## Perguntas recorrentes",
        "",
    ]

    questions = summary.get("top_questions", [])
    if questions:
        for item in questions[:8]:
            lines.append(f"- ({item['likes']} likes) {item['text']}")
    else:
        lines.append("- Nenhuma pergunta evidente encontrada com os heurísticos atuais.")

    lines.extend(["", "## Oportunidades de conteudo", ""])
    opportunities = summary.get("content_opportunities", [])
    if opportunities:
        for item in opportunities[:8]:
            lines.append(f"- ({item['likes']} likes) {item['text']}")
    else:
        lines.append("- Nenhum pedido claro de follow-up apareceu nos padrões buscados.")

    lines.extend(["", "## Linguagem da audiencia", ""])
    keywords = summary.get("top_keywords", [])
    if keywords:
        lines.append("- " + ", ".join(f"{item['term']} ({item['count']})" for item in keywords[:15]))
    else:
        lines.append("- Sem termos frequentes suficientes para listar.")

    lines.extend(["", "## Comentarios com mais tracao", ""])
    for item in summary.get("top_comments", [])[:8]:
        lines.append(f"- ({item['likes']} likes) {item['text']}")

    if ai_insights:
        lines.extend(["", "## Leitura AI", ""])
        for theme in ai_insights.get("core_themes", [])[:5]:
            lines.append(f"- Tema: {theme.get('title', '')} | {theme.get('why_it_matters', '')}")
        learning_summary = ai_insights.get("learning_summary") or {}
        if learning_summary:
            lines.extend(
                [
                    "",
                    "## Complemento De Aprendizado",
                    "",
                    f"- O que o video ensina: {learning_summary.get('what_the_video_teaches', '')}",
                    f"- O que os comentarios acrescentam: {learning_summary.get('what_the_comments_add', '')}",
                    f"- Melhor proximo passo: {learning_summary.get('best_next_step_for_learning', '')}",
                ]
            )
        complementary = ai_insights.get("complementary_learning", [])
        if complementary:
            lines.extend(["", "## O Que A Audiencia Acrescenta", ""])
            for item in complementary[:6]:
                lines.append(
                    f"- {item.get('topic', '')}: {item.get('what_comments_add', '')} | Evidencia: {item.get('evidence', '')}"
                )
        open_loops = ai_insights.get("open_loops", [])
        if open_loops:
            lines.extend(["", "## Pontos Em Aberto", ""])
            for item in open_loops[:6]:
                lines.append(
                    f"- {item.get('question', '')} | Por que ficou em aberto: {item.get('why_unresolved', '')} | Evidencia: {item.get('evidence', '')}"
                )
        extensions = ai_insights.get("practical_extensions", [])
        if extensions:
            lines.extend(["", "## Extensoes Praticas", ""])
            for item in extensions[:6]:
                lines.append(
                    f"- {item.get('topic', '')}: {item.get('why_useful', '')} | Evidencia: {item.get('evidence', '')}"
                )
        counterpoints = ai_insights.get("counterpoints_or_tensions", [])
        if counterpoints:
            lines.extend(["", "## Contrapontos E Tensoes", ""])
            for item in counterpoints[:6]:
                lines.append(
                    f"- {item.get('point', '')}: {item.get('why_it_matters', '')} | Evidencia: {item.get('evidence', '')}"
                )
        audience_examples = ai_insights.get("examples_from_audience", [])
        if audience_examples:
            lines.extend(["", "## Exemplos Trazidos Pela Audiencia", ""])
            for item in audience_examples[:6]:
                lines.append(
                    f"- {item.get('example', '')}: {item.get('why_it_matters', '')} | Evidencia: {item.get('evidence', '')}"
                )
        next_piece = ai_insights.get("recommended_next_piece") or {}
        if next_piece:
            lines.extend(
                [
                    "",
                    "## Proxima peca recomendada",
                    "",
                    f"- Formato: {next_piece.get('format', '')}",
                    f"- Titulo: {next_piece.get('title', '')}",
                    f"- Motivo: {next_piece.get('reason', '')}",
                ]
            )

    if transcript_meta.get("status") != "ok":
        lines.extend(
            [
                "",
                "## Limite atual",
                "",
                "- O video nao expôs captions publicas suficientes para montar transcript direto por legenda.",
                "- O pipeline caiu para audio+STT apenas se OpenRouter estava configurado e permitido no fluxo.",
            ]
        )
    if video.get("platform") != "youtube":
        lines.extend(
            [
                "",
                "## Limitacoes Da Plataforma",
                "",
                "- Este conector reutiliza a transcricao e a analise, mas nao captura comentarios do Instagram.",
                "- O output final fica focado no transcript, metadados e sinais do proprio conteudo.",
            ]
        )

    return "\n".join(lines).strip() + "\n"


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    env = load_env()
    youtube_api_key = (env.get("YOUTUBE_API_KEY") or "").strip()
    openrouter_api_key = (env.get("OPENROUTER_API_KEY") or "").strip()
    platform = detect_platform(args.url)

    if platform == "youtube":
        if not youtube_api_key:
            print("Erro: configure YOUTUBE_API_KEY no .env ou no ambiente.")
            return 1
        video_id = extract_video_id(args.url)
        video = fetch_video(youtube_api_key, video_id)
    else:
        video = fetch_web_metadata(
            args.url,
            cookies_from_browser=args.cookies_from_browser,
            cookies_file=args.cookies_file,
        )
        video.setdefault("platform", platform)
        video_id = str(video.get("video_id", "")).strip()

    output_dir = Path(args.output_dir) if args.output_dir else default_video_output_dir(video)
    output_dir.mkdir(parents=True, exist_ok=True)
    preferred_language, language_resolution = resolve_preferred_language(args.lang, video)
    comments = fetch_comments(youtube_api_key, video_id, max_comments=args.max_comments) if platform == "youtube" else []

    transcript_segments: list[dict[str, Any]] = []
    transcript_meta: dict[str, Any] = {}
    transcript_debug: dict[str, Any] = {}

    if platform == "youtube" and not args.force_stt:
        try:
            transcript_segments, transcript_meta = fetch_public_transcript(video_id, preferred_language)
            transcript_meta["language_resolution"] = language_resolution
        except Exception as exc:
            transcript_meta = {
                "status": "unavailable",
                "reason": str(exc),
                "source": "public_captions",
                "language_resolution": language_resolution,
            }

    needs_stt = args.force_stt or transcript_meta.get("status") != "ok"
    if needs_stt and openrouter_api_key:
        try:
            transcript_segments, transcript_meta, transcript_debug = transcribe_via_audio_fallback(
                video=video,
                language=preferred_language,
                output_dir=output_dir,
                openrouter_api_key=openrouter_api_key,
                stt_model=args.stt_model,
                cleanup_model=args.cleanup_model,
                chunk_seconds=args.chunk_seconds,
                overlap_seconds=args.chunk_overlap_seconds,
                skip_cleanup=args.skip_cleanup,
                cookies_from_browser=args.cookies_from_browser,
                cookies_file=args.cookies_file,
            )
            transcript_meta["language_resolution"] = language_resolution
        except Exception as exc:
            prior_reason = transcript_meta.get("reason", "")
            transcript_meta = {
                "status": "unavailable",
                "reason": f"public={prior_reason} | audio_stt={exc}",
                "source": "audio_stt",
                "stt_model": args.stt_model,
                "language_resolution": language_resolution,
            }
    elif needs_stt and not openrouter_api_key:
        reason = "Instagram requer OPENROUTER_API_KEY para fallback STT." if platform != "youtube" else "Sem transcript publico"
        transcript_meta = {
            **transcript_meta,
            "reason": f"{reason} | OPENROUTER_API_KEY ausente para fallback STT",
            "language_resolution": language_resolution,
        }

    transcript_text = "\n".join(segment["text"] for segment in transcript_segments).strip()
    summary = build_summary(video, transcript_segments, transcript_meta, comments)

    ai_insights: dict[str, Any] | None = None
    if openrouter_api_key and not args.skip_ai_analysis:
        try:
            ai_insights = generate_ai_insights(
                video=video,
                transcript_text=transcript_text,
                summary=summary,
                comment_threads=comments,
                api_key=openrouter_api_key,
                model=args.analysis_model,
            )
        except Exception as exc:
            ai_insights = {"_error": str(exc), "_meta": {"model": args.analysis_model}}

    report = build_report(video, transcript_meta, summary, ai_insights=ai_insights)

    write_json(output_dir / "video.json", video)
    write_json(output_dir / "comments.json", comments)
    write_json(output_dir / "transcript.json", {"meta": transcript_meta, "segments": transcript_segments})
    write_json(output_dir / "summary.json", summary)
    write_json(output_dir / "transcript_debug.json", transcript_debug)
    if ai_insights is not None:
        write_json(output_dir / "ai_insights.json", ai_insights)
    (output_dir / "transcript.txt").write_text(transcript_text, encoding="utf-8")
    (output_dir / "report.md").write_text(report, encoding="utf-8")

    print(f"Video: {video['title']}")
    print(f"Saida: {output_dir}")
    print(
        "Resumo: "
        f"{summary['counts']['top_level_comments']} comentarios top-level, "
        f"{summary['counts']['replies']} respostas, "
        f"transcript={transcript_meta.get('status', 'unavailable')}, "
        f"fonte={transcript_meta.get('source', 'n/d')}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
