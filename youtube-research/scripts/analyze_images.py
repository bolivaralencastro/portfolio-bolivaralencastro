#!/usr/bin/env python3
"""
Analisa imagens de um post/carrossel do Instagram via modelo de visão (OpenRouter).

Lê a pasta de artefatos criada por enrich_social_image.py — que contém post.json
e um subdiretório slides/ com as imagens baixadas — envia as imagens para um
modelo de visão via OpenRouter, e gera:
  - ai_insights_images.json   (análise estruturada)
  - final-image-report.md     (relatório legível em português)

Usage:
    python3 youtube-research/scripts/analyze_images.py data/instagram-research/posts/<pasta>
    python3 youtube-research/scripts/analyze_images.py <pasta> --model google/gemini-flash-1.5
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except Exception:
    SSL_CONTEXT = ssl.create_default_context()


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_FILE = REPO_ROOT / ".env"
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

DEFAULT_MODEL = "google/gemini-flash-1.5"
MAX_SLIDES = 10          # limite de imagens enviadas ao modelo por segurança
MAX_IMG_BYTES = 4 * 1024 * 1024  # 4 MB por imagem — acima disso, redimensionar via PIL se disponível

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MIME_BY_EXT = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip().strip('"').strip("'")
    return {**env, **os.environ}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def openrouter_request_json(body: dict[str, Any], api_key: str) -> dict[str, Any]:
    req = urllib.request.Request(
        OPENROUTER_CHAT_URL,
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
        with urllib.request.urlopen(req, timeout=300, context=SSL_CONTEXT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Erro OpenRouter ({exc.code}): {payload}") from exc


def encode_image(path: Path) -> str:
    """Codifica imagem em data URI base64."""
    data = path.read_bytes()
    ext = path.suffix.lower()
    mime = MIME_BY_EXT.get(ext, "image/jpeg")
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def collect_slides(research_dir: Path) -> list[Path]:
    """Retorna lista de imagens da pasta slides/, ordenada."""
    slides_dir = research_dir / "slides"
    if not slides_dir.exists():
        return []
    paths = sorted(
        p for p in slides_dir.iterdir()
        if p.suffix.lower() in IMAGE_EXTENSIONS and p.is_file()
    )
    return paths[:MAX_SLIDES]


def extract_json_from_response(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise RuntimeError(f"Resposta sem JSON válido: {text[:500]}")
    return json.loads(match.group(0))


# ---------------------------------------------------------------------------
# Vision prompt e análise
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
Você é um analista de conteúdo visual especializado em posts do Instagram.
Responda exclusivamente em português do Brasil.
Seja objetivo, concreto e evite frases genéricas.
Preserve termos técnicos e nomes próprios no idioma original quando relevante.
Retorne apenas JSON estrito, sem markdown, sem blocos de código.
"""

USER_PROMPT_TEMPLATE = """\
Analise este post do Instagram e retorne um JSON com a estrutura abaixo.

Informações do post:
- Título/Tipo: {title}
- Autor: {author}
- Caption: {caption}
- Número de slides: {n_slides}

Estrutura JSON esperada:
{{
  "post_summary": "resumo do que este post comunica (2-3 frases)",
  "slide_descriptions": ["descrição detalhada do slide 1", "slide 2", ...],
  "main_message": "a mensagem central ou argumento principal do post",
  "key_information": ["ponto de informação 1", "ponto 2", ...],
  "context_and_relevance": "por que este conteúdo é relevante, contexto cultural/profissional",
  "takeaway": "o que fica de aprendizado ou reflexão após consumir este post",
  "content_type": "infográfico | texto | foto | dado/gráfico | tutorial | outro"
}}

Analise as imagens abaixo:
"""


def build_vision_request(post: dict, slide_paths: list[Path], model: str) -> dict[str, Any]:
    title = post.get("title") or post.get("id") or ""
    author = post.get("uploader") or post.get("channel_title") or ""
    caption = (post.get("description") or "")[:2000]
    n_slides = len(slide_paths)

    user_text = USER_PROMPT_TEMPLATE.format(
        title=title, author=author, caption=caption, n_slides=n_slides
    )

    content: list[dict] = [{"type": "text", "text": user_text}]
    for path in slide_paths:
        try:
            img_data = encode_image(path)
            content.append({
                "type": "image_url",
                "image_url": {"url": img_data},
            })
        except Exception as exc:
            print(f"  Aviso: não foi possível codificar {path.name}: {exc}")

    return {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
    }


def analyse(research_dir: Path, model: str, api_key: str) -> dict[str, Any]:
    """Executa a análise visual e retorna os insights estruturados."""
    post_json_path = research_dir / "post.json"
    if not post_json_path.exists():
        raise RuntimeError(f"post.json não encontrado em {research_dir}")

    post = read_json(post_json_path)
    slide_paths = collect_slides(research_dir)

    if not slide_paths:
        raise RuntimeError(f"Nenhuma imagem encontrada em {research_dir / 'slides'}")

    print(f"  {len(slide_paths)} slide(s) encontrado(s)")

    body = build_vision_request(post, slide_paths, model)
    print(f"  Enviando para {model}…")
    response = openrouter_request_json(body, api_key)

    content = (
        response.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )
    insights = extract_json_from_response(content)
    insights["_meta"] = {
        "model": model,
        "n_slides": len(slide_paths),
        "post_id": post.get("id") or post.get("video_id") or "",
        "post_url": post.get("url") or post.get("webpage_url") or "",
    }
    return insights


# ---------------------------------------------------------------------------
# Relatório final
# ---------------------------------------------------------------------------

def build_image_report(post: dict, insights: dict[str, Any]) -> str:
    title = post.get("title") or insights.get("_meta", {}).get("post_id") or "Post"
    author = post.get("uploader") or post.get("channel_title") or ""
    url = post.get("url") or post.get("webpage_url") or insights.get("_meta", {}).get("post_url") or ""
    caption = (post.get("description") or "").strip()

    lines = [
        f"# Análise Visual: {title}",
        "",
    ]
    if author:
        lines.append(f"**Autor:** {author}")
    if url:
        lines.append(f"**Post:** {url}")
    lines.append("")

    if caption:
        lines.extend([
            "## Caption",
            "",
            caption[:800] + ("…" if len(caption) > 800 else ""),
            "",
        ])

    post_summary = insights.get("post_summary", "")
    if post_summary:
        lines.extend([
            "## Resumo",
            "",
            post_summary,
            "",
        ])

    main_message = insights.get("main_message", "")
    if main_message:
        lines.extend([
            "## Mensagem Central",
            "",
            main_message,
            "",
        ])

    slide_descs = insights.get("slide_descriptions") or []
    if slide_descs:
        lines.extend(["## Slides", ""])
        for i, desc in enumerate(slide_descs, 1):
            lines.append(f"**Slide {i}:** {desc}")
        lines.append("")

    key_info = insights.get("key_information") or []
    if key_info:
        lines.extend(["## Informações-Chave", ""])
        for info in key_info:
            lines.append(f"- {info}")
        lines.append("")

    context = insights.get("context_and_relevance", "")
    if context:
        lines.extend([
            "## Contexto e Relevância",
            "",
            context,
            "",
        ])

    takeaway = insights.get("takeaway", "")
    if takeaway:
        lines.extend([
            "## Aprendizado",
            "",
            takeaway,
            "",
        ])

    content_type = insights.get("content_type", "")
    meta = insights.get("_meta", {})
    lines.extend([
        "---",
        "",
        f"*Tipo de conteúdo: {content_type} | Slides analisados: {meta.get('n_slides', '?')} | Modelo: {meta.get('model', '?')}*",
    ])

    return "\n".join(lines).strip() + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("research_dir", help="Pasta com post.json e slides/")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Modelo de visão via OpenRouter. Padrão: {DEFAULT_MODEL}",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    research_dir = Path(args.research_dir).resolve()

    if not research_dir.exists():
        print(f"Erro: pasta não encontrada: {research_dir}")
        return 1

    env = load_env()
    api_key = (env.get("OPENROUTER_API_KEY") or "").strip()
    if not api_key:
        print("Erro: configure OPENROUTER_API_KEY no .env ou no ambiente.")
        return 1

    print(f"Analisando: {research_dir}")

    post_json_path = research_dir / "post.json"
    post = read_json(post_json_path) if post_json_path.exists() else {}

    insights = analyse(research_dir, model=args.model, api_key=api_key)

    insights_path = research_dir / "ai_insights_images.json"
    insights_path.write_text(json.dumps(insights, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Insights: {insights_path.relative_to(REPO_ROOT)}")

    report = build_image_report(post, insights)
    report_path = research_dir / "final-image-report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"  Relatório: {report_path.relative_to(REPO_ROOT)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
