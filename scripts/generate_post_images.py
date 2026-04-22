#!/usr/bin/env python3
"""
Gera automaticamente todas as imagens de um post do blog.

Lê o conteúdo do post, usa um modelo de texto barato para criar prompts
visuais contextualizados, depois gera as imagens em paralelo via OpenRouter.

Usage:
    python3 scripts/generate_post_images.py blog/meu-post.html
    python3 scripts/generate_post_images.py blog/meu-post.html --inline 3
    python3 scripts/generate_post_images.py blog/meu-post.html --only cover
    python3 scripts/generate_post_images.py blog/meu-post.html --dry-run

Saída:
    Salva os webps em assets/images/blog/<slug>/
    Imprime as <img> tags prontas para inserir no HTML do post.
"""

import argparse
import base64
import concurrent.futures
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
from io import BytesIO
from pathlib import Path

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = ssl.create_default_context()

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

ROOT = Path(__file__).parent.parent
ENV_FILE = ROOT / ".env"

IMAGE_MODEL = "openai/gpt-5.4-image-2"
PROMPT_MODEL = "google/gemini-2.0-flash-001"  # barato e rápido

PRESETS = {
    "cover":  (1400, 787),
    "card":   (960, 540),
    "inline": (1200, 675),
}

EDITORIAL_SUFFIX = (
    " Flat vector illustration style. Dark charcoal background. "
    "Blue and teal accent colors. No readable text or labels. "
    "Clean, minimal, modern editorial feel."
)


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def load_env() -> dict:
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return {**env, **os.environ}


def extract_post_content(html_path: Path) -> dict:
    """Extrai título, descrição, texto e slug do post."""
    content = html_path.read_text(encoding="utf-8")

    title_m = re.search(r'<h1[^>]*>(.*?)</h1>', content, re.DOTALL)
    title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip() if title_m else ""

    desc_m = re.search(r'<meta name="description" content="([^"]+)"', content)
    description = desc_m.group(1).strip() if desc_m else ""

    # Extrai texto puro do e-content
    econtent_m = re.search(r'class="e-content[^"]*"[^>]*>(.*?)</div>', content, re.DOTALL)
    if econtent_m:
        raw = econtent_m.group(1)
        # Remove tags mas mantém texto
        text = re.sub(r'<[^>]+>', ' ', raw)
        text = re.sub(r'\s+', ' ', text).strip()[:2000]
    else:
        text = description

    h2s = re.findall(r'<h2[^>]*>(.*?)</h2>', content, re.DOTALL)
    sections = [re.sub(r'<[^>]+>', '', h).strip() for h in h2s]

    return {
        "slug": html_path.stem,
        "title": title,
        "description": description,
        "text": text,
        "sections": sections,
    }


def call_text_model(prompt: str, api_key: str, max_tokens: int = 1024) -> str:
    """Chama modelo de texto via OpenRouter."""
    payload = json.dumps({
        "model": PROMPT_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }).encode()

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://bolivaralencastro.com.br",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=60) as r:
        result = json.loads(r.read())
    return result["choices"][0]["message"]["content"].strip()


def generate_prompts(post: dict, n_inline: int, api_key: str) -> dict:
    """
    Usa modelo de texto barato para gerar prompts visuais contextualizados.
    Retorna dict com chaves: cover, card, inline (lista).
    """
    sections_str = "\n".join(f"- {s}" for s in post["sections"]) if post["sections"] else "(sem seções)"

    system_prompt = f"""Você é um diretor de arte editorial para um blog de tecnologia.
Dado o conteúdo de um post, crie prompts em inglês para geração de imagens editoriais.

POST:
Título: {post['title']}
Descrição: {post['description']}
Seções: {sections_str}
Resumo do conteúdo: {post['text'][:800]}

Gere exatamente {2 + n_inline} prompts no formato JSON abaixo.
Cada prompt deve descrever APENAS o conteúdo visual (não o estilo — o estilo já será aplicado automaticamente).
Seja específico: formas, elementos, relações espaciais, metáforas visuais do tema.

{{
  "cover": "prompt para a imagem de capa (16:9, mais impactante e representativa do post)",
  "card": "prompt para o card social (16:9, variação simplificada da cover)",
  "inline": [
    "prompt para imagem inline 1 (ilustra a primeira seção ou conceito principal)",
    "prompt para imagem inline 2 (ilustra o segundo conceito ou ponto de virada)",
    ...{' mais ' + str(n_inline - 2) + ' prompts' if n_inline > 2 else ''}
  ]
}}

Retorne APENAS o JSON, sem markdown, sem explicação."""

    raw = call_text_model(system_prompt, api_key)

    # Extrai JSON mesmo se vier com ```json ... ```
    json_m = re.search(r'\{.*\}', raw, re.DOTALL)
    if not json_m:
        raise ValueError(f"Modelo não retornou JSON válido:\n{raw[:300]}")

    data = json.loads(json_m.group(0))

    # Garante que inline tem exatamente n_inline itens
    inline = data.get("inline", [])
    if len(inline) < n_inline:
        inline += [data["cover"]] * (n_inline - len(inline))
    data["inline"] = inline[:n_inline]

    return data


def generate_image_bytes(prompt: str, api_key: str) -> bytes:
    """Gera imagem via OpenRouter e retorna bytes brutos."""
    payload = json.dumps({
        "model": IMAGE_MODEL,
        "modalities": ["text", "image"],
        "messages": [{"role": "user", "content": prompt + EDITORIAL_SUFFIX}],
        "max_tokens": 4096,
    }).encode()

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://bolivaralencastro.com.br",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=180) as r:
        raw = r.read().decode()

    m = re.search(r'data:image/[a-z]+;base64,([A-Za-z0-9+/=]+)', raw)
    if not m:
        raise ValueError("Nenhuma imagem na resposta da API.")
    return base64.b64decode(m.group(1))


def save_webp(img_bytes: bytes, dest: Path, width: int, height: int, quality: int = 85):
    """Salva como webp com crop e resize para as dimensões alvo."""
    if not HAS_PIL:
        dest.with_suffix(".png").write_bytes(img_bytes)
        return

    img = Image.open(BytesIO(img_bytes)).convert("RGB")
    ow, oh = img.size
    target_ratio = width / height
    current_ratio = ow / oh

    if abs(current_ratio - target_ratio) > 0.01:
        if current_ratio > target_ratio:
            new_w = int(oh * target_ratio)
            left = (ow - new_w) // 2
            img = img.crop((left, 0, left + new_w, oh))
        else:
            new_h = int(ow / target_ratio)
            top = (oh - new_h) // 2
            img = img.crop((0, top, ow, top + new_h))

    img = img.resize((width, height), Image.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(dest), "webp", quality=quality)


def make_img_tag(path: Path, alt: str, width: int, height: int) -> str:
    rel = path.relative_to(ROOT)
    return (
        f'<img src="/{rel}" alt="{alt}" '
        f'width="{width}" height="{height}" loading="lazy" decoding="async">'
    )


# ──────────────────────────────────────────────
# Core
# ──────────────────────────────────────────────

def run(html_path: Path, n_inline: int, only: str | None, dry_run: bool, quality: int, api_key: str):
    post = extract_post_content(html_path)
    slug = post["slug"]
    assets_dir = ROOT / "assets" / "images" / "blog" / slug

    print(f"\n📄 Post: {post['title']}")
    print(f"📁 Assets: assets/images/blog/{slug}/\n")

    # ── Gerar prompts ──
    print("💬 Gerando prompts com modelo de texto...")
    prompts = generate_prompts(post, n_inline, api_key)

    jobs = []  # (nome, preset, prompt, dest_path)

    if not only or only == "cover":
        jobs.append(("cover", "cover", prompts["cover"],
                     assets_dir / "cover.webp"))

    if not only or only == "card":
        jobs.append(("card", "card", prompts["card"],
                     assets_dir / "card.webp"))

    if not only or only == "inline":
        for i, p in enumerate(prompts["inline"], 1):
            name = f"inline-{i:02d}"
            jobs.append((name, "inline", p, assets_dir / f"{name}.webp"))

    print(f"🎨 {len(jobs)} {'imagem' if len(jobs) == 1 else 'imagens'} a gerar:\n")
    for name, preset, prompt, dest in jobs:
        w, h = PRESETS[preset]
        print(f"  [{name}] {w}x{h}")
        print(f"  Prompt: {prompt[:90]}{'...' if len(prompt) > 90 else ''}\n")

    if dry_run:
        print("🔍 Dry run — nenhuma imagem gerada.")
        return

    # ── Gerar imagens em paralelo ──
    print("⚡ Gerando em paralelo...\n")
    results = {}

    def generate_job(job):
        name, preset, prompt, dest = job
        w, h = PRESETS[preset]
        img_bytes = generate_image_bytes(prompt, api_key)
        save_webp(img_bytes, dest, w, h, quality)
        return name, dest, w, h

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(generate_job, job): job[0] for job in jobs}
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            try:
                _, dest, w, h = future.result()
                size_kb = dest.stat().st_size // 1024
                print(f"  ✅ {name} → {dest.relative_to(ROOT)} ({size_kb}KB)")
                results[name] = (dest, w, h)
            except Exception as e:
                print(f"  ❌ {name}: {e}")

    # ── Imprimir <img> tags ──
    print(f"\n{'─'*60}")
    print("📋 Tags prontas para inserir no HTML:\n")

    for name, preset, prompt, dest in jobs:
        if name not in results:
            continue
        dest, w, h = results[name]
        if name == "cover":
            alt = f"Ilustração editorial do post: {post['title']}"
            tag = make_img_tag(dest, alt, w, h)
            print(f"<!-- COVER -->\n{tag}\n")
        elif name == "card":
            print(f"<!-- CARD (usar em og:image / twitter:image) -->\n{dest.relative_to(ROOT)}\n")
        else:
            idx = name.split("-")[1]
            alt = f"Ilustração {idx} do post sobre {post['title']}"
            tag = make_img_tag(dest, alt, w, h)
            print(f"<!-- INLINE {idx} -->\n{tag}\n")


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Gera imagens para um post do blog via OpenRouter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("post", help="Caminho do HTML do post (ex: blog/meu-post.html)")
    parser.add_argument("--inline", type=int, default=2, metavar="N",
                        help="Número de imagens inline no corpo do post (padrão: 2)")
    parser.add_argument("--only", choices=["cover", "card", "inline"],
                        help="Gera apenas um tipo de imagem")
    parser.add_argument("--dry-run", action="store_true",
                        help="Mostra os prompts sem gerar imagens")
    parser.add_argument("--quality", type=int, default=85,
                        help="Qualidade webp 1-100 (padrão: 85)")
    args = parser.parse_args()

    env = load_env()
    api_key = env.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        print("❌ OPENROUTER_API_KEY não encontrado no .env")
        sys.exit(1)

    html_path = Path(args.post)
    if not html_path.is_absolute():
        html_path = ROOT / html_path
    if not html_path.exists():
        print(f"❌ Post não encontrado: {html_path}")
        sys.exit(1)

    run(html_path, args.inline, args.only, args.dry_run, args.quality, api_key)


if __name__ == "__main__":
    main()
