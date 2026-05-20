#!/usr/bin/env python3
"""
Analyze an existing YouTube research folder and extract complementary learning
signals from transcript + comments using a prompt file that can be iterated over
time.

Usage:
    python3 youtube-research/scripts/analyze_learning.py youtube-research/videos/VIDEO_ID
"""

from __future__ import annotations

import argparse
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
ROOT = REPO_ROOT
ENV_FILE = REPO_ROOT / ".env"
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "deepseek/deepseek-chat"
DEFAULT_PROMPT_FILE = (
    ROOT
    / "youtube-research"
    / "prompts"
    / "learning-analysis-v2.md"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("research_dir", help="Folder containing YouTube research artifacts")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"OpenRouter model. Default: {DEFAULT_MODEL}")
    parser.add_argument("--prompt-file", default=str(DEFAULT_PROMPT_FILE), help="Prompt file to drive the analysis")
    parser.add_argument("--max-threads", type=int, default=30, help="Maximum comment threads to include. Default: 30")
    parser.add_argument("--max-replies", type=int, default=4, help="Maximum replies per thread to include. Default: 4")
    parser.add_argument("--transcript-chars", type=int, default=18000, help="Transcript characters to send. Default: 18000")
    return parser.parse_args()


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
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
        with urllib.request.urlopen(req, timeout=240, context=SSL_CONTEXT) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Erro OpenRouter ({exc.code}): {payload}") from exc


def load_research_artifacts(research_dir: Path) -> dict[str, Any]:
    required = ["video.json", "comments.json", "summary.json"]
    missing = [name for name in required if not (research_dir / name).exists()]
    if missing:
        raise RuntimeError(f"Artefatos ausentes em {research_dir}: {', '.join(missing)}")

    transcript_path = research_dir / "transcript.txt"
    transcript_json_path = research_dir / "transcript.json"
    transcript_text = ""
    if transcript_path.exists():
        transcript_text = transcript_path.read_text(encoding="utf-8").strip()
    elif transcript_json_path.exists():
        transcript_payload = read_json(transcript_json_path)
        segments = transcript_payload.get("segments", [])
        transcript_text = "\n".join(segment.get("text", "") for segment in segments).strip()

    return {
        "video": read_json(research_dir / "video.json"),
        "comments": read_json(research_dir / "comments.json"),
        "summary": read_json(research_dir / "summary.json"),
        "transcript_text": transcript_text,
    }


def sample_threads(comments: list[dict[str, Any]], max_threads: int, max_replies: int) -> list[dict[str, Any]]:
    sampled: list[dict[str, Any]] = []
    for thread in comments[:max_threads]:
        sampled.append(
            {
                "top_level": thread.get("top_level", {}),
                "replies": thread.get("replies", [])[:max_replies],
            }
        )
    return sampled


def build_prompt(prompt_file: Path, payload: dict[str, Any]) -> str:
    base = prompt_file.read_text(encoding="utf-8").strip()
    return f"{base}\n\nDATA:\n{json.dumps(payload, ensure_ascii=False)}"


def extract_json_from_response(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise RuntimeError(f"Resposta sem JSON valido: {text[:500]}")
    return json.loads(match.group(0))


def translate_insights_to_ptbr(insights: dict[str, Any], api_key: str, model: str) -> dict[str, Any]:
    body = {
        "model": model,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Voce traduz valores de um JSON para pt-BR preservando exatamente a estrutura, as chaves, "
                    "os arrays e os tipos. Traduza apenas os valores textuais. Preserve nomes proprios, siglas, "
                    "termos tecnicos inevitaveis e citacoes literais quando fizer sentido. Retorne apenas JSON estrito."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Traduza o JSON abaixo para pt-BR. Preserve as chaves exatamente como estao.\n\n"
                    f"{json.dumps(insights, ensure_ascii=False)}"
                ),
            },
        ],
    }
    response = openrouter_request_json(body, api_key)
    content = (
        response.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )
    translated = extract_json_from_response(content)
    translated["_translation_meta"] = {"model": model, "raw_response": response}
    return translated


def build_learning_report(video: dict[str, Any], insights: dict[str, Any]) -> str:
    lines = [
        f"# Aprendizado Complementar: {video.get('title', '')}",
        "",
        f"- Video: {video.get('url', '')}",
        f"- Canal: {video.get('channel_title', '')}",
        "",
    ]

    learning = insights.get("learning_summary") or {}
    if learning:
        lines.extend(
            [
                "## Resumo De Aprendizado",
                "",
                f"- O que o video ensina: {learning.get('what_the_video_teaches', '')}",
                f"- O que os comentarios acrescentam: {learning.get('what_the_comments_add', '')}",
                f"- Melhor proximo passo: {learning.get('best_next_step_for_learning', '')}",
                "",
            ]
        )

    source_split = insights.get("source_split") or {}
    video_takeaways = source_split.get("main_takeaways_from_video") or []
    audience_takeaways = source_split.get("main_takeaways_from_audience") or []
    if video_takeaways or audience_takeaways:
        lines.extend(["## Separacao De Fontes", ""])
        if video_takeaways:
            lines.append("- Do video: " + " | ".join(str(item) for item in video_takeaways if str(item).strip()))
        if audience_takeaways:
            lines.append("- Da audiencia: " + " | ".join(str(item) for item in audience_takeaways if str(item).strip()))
        lines.append("")

    sections = [
        ("Aprendizado Complementar", "complementary_learning", ("topic", "what_comments_add", "how_it_complements_the_video", "evidence")),
        ("Pontos Em Aberto", "open_loops", ("question", "why_unresolved", "evidence")),
        ("Extensoes Praticas", "practical_extensions", ("topic", "why_useful", "how_it_extends_the_video", "evidence")),
        ("Contrapontos E Tensoes", "counterpoints_or_tensions", ("point", "why_it_matters", "evidence")),
        ("Exemplos Da Audiencia", "examples_from_audience", ("example", "why_it_matters", "how_it_makes_the_topic_more_concrete", "evidence")),
        ("Perguntas Da Audiencia", "audience_questions", ("question", "evidence")),
        ("Atrito Terminologico", "terminology_friction", ("term_or_concept", "why_confusing", "what_better_explanation_is_needed", "evidence")),
    ]

    for title, key, fields in sections:
        items = insights.get(key) or []
        if not items:
            continue
        lines.extend([f"## {title}", ""])
        for item in items[:8]:
            parts = [str(item.get(field, "")).strip() for field in fields if str(item.get(field, "")).strip()]
            lines.append(f"- {' | '.join(parts)}")
        lines.append("")

    priorities = insights.get("learning_priorities") or []
    if priorities:
        lines.extend(["## Prioridades De Aprendizado", ""])
        for item in priorities[:8]:
            parts = [
                str(item.get("priority", "")).strip(),
                str(item.get("why_it_matters_now", "")).strip(),
                str(item.get("evidence", "")).strip(),
            ]
            lines.append(f"- {' | '.join(part for part in parts if part)}")
        lines.append("")

    next_piece = insights.get("recommended_next_piece") or {}
    if next_piece:
        lines.extend(
            [
                "## Proxima Peca Recomendada",
                "",
                f"- Formato: {next_piece.get('format', '')}",
                f"- Titulo: {next_piece.get('title', '')}",
                f"- Motivo: {next_piece.get('reason', '')}",
                "",
            ]
        )

    return "\n".join(lines).strip() + "\n"


def main() -> int:
    args = parse_args()
    research_dir = Path(args.research_dir).resolve()
    if not research_dir.exists():
        print(f"Erro: pasta nao encontrada: {research_dir}")
        return 1

    env = load_env()
    api_key = (env.get("OPENROUTER_API_KEY") or "").strip()
    if not api_key:
        print("Erro: configure OPENROUTER_API_KEY no .env ou no ambiente.")
        return 1

    prompt_file = Path(args.prompt_file).resolve()
    if not prompt_file.exists():
        print(f"Erro: prompt file nao encontrado: {prompt_file}")
        return 1

    artifacts = load_research_artifacts(research_dir)
    payload = {
        "video": {
            "title": artifacts["video"].get("title", ""),
            "channel_title": artifacts["video"].get("channel_title", ""),
            "description": artifacts["video"].get("description", "")[:3000],
            "url": artifacts["video"].get("url", ""),
            "published_at": artifacts["video"].get("published_at", ""),
        },
        "summary": artifacts["summary"],
        "sampled_threads": sample_threads(artifacts["comments"], args.max_threads, args.max_replies),
        "transcript_excerpt": artifacts["transcript_text"][: args.transcript_chars],
    }
    prompt = build_prompt(prompt_file, payload)
    body = {
        "model": args.model,
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": "Voce extrai aprendizado complementar a partir de transcript e discussao da audiencia. Voce sempre retorna JSON estrito e escreve os valores em pt-BR, exceto nomes proprios, siglas, termos tecnicos inevitaveis e citacoes literais.",
            },
            {"role": "user", "content": prompt},
        ],
    }
    response = openrouter_request_json(body, api_key)
    content = (
        response.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )
    parsed = extract_json_from_response(content)
    translated = translate_insights_to_ptbr(parsed, api_key, args.model)
    translated["_meta"] = {
        "model": args.model,
        "prompt_file": str(prompt_file),
        "raw_response": response,
    }

    output_json = research_dir / "ai_insights_learning.json"
    output_report = research_dir / "final-learning-report.md"
    output_json.write_text(json.dumps(translated, ensure_ascii=False, indent=2), encoding="utf-8")
    output_report.write_text(build_learning_report(artifacts["video"], translated), encoding="utf-8")

    print(f"Analysis dir: {research_dir}")
    print(f"JSON: {output_json}")
    print(f"Report: {output_report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
