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

DEFAULT_IMAGE_MODEL = "openai/gpt-5.4-image-2"
DEFAULT_PROMPT_MODEL = "google/gemini-2.0-flash-001"  # barato e rápido

PRESETS = {
    "cover":  (1400, 787),
    "card":   (960, 540),
    "inline": (1200, 675),
}

STYLE_PROFILES = {
    "default": (
        "Flat vector illustration style. Dark charcoal background. "
        "Blue and teal accent colors. Clean, minimal, modern editorial feel."
    ),
    "diagrammatic": (
        "Diagrammatic editorial style with strong geometric structure. "
        "Dark slate background, cyan accents, crisp contours, controlled density."
    ),
    "newsprint-collage": (
        "Magazine-like editorial collage style with cutout shapes and paper texture cues. "
        "Bold contrast and limited palette, modern but tactile."
    ),
    "constructivist": (
        "Constructivist poster-inspired editorial style with assertive diagonals, "
        "angular forms, and high-contrast composition."
    ),
    "surrealist-portrait": (
        "Extreme asymmetric close-up composition with deliberate scale distortion. "
        "Dramatic high-contrast shadow masses against bright highlight zones. "
        "Restricted saturated palette. Hyper-detailed focal textures contrasted against "
        "grainy abstract color fields. Surrealist editorial art direction."
    ),
    "painterly-landscape": (
        "Visible impasto brushstrokes and palette-knife texture throughout. "
        "Broken warm-cool color transitions — ochre against ultramarine. "
        "Asymmetric low-horizon composition with atmospheric perspective. "
        "Painterly abstraction over photorealism. No photographic sharpness."
    ),
    "pop-editorial": (
        "Artificial staged backdrop — hand-painted flat panel behind subject. "
        "High-saturation limited palette: royal blue, red accent, cream. "
        "Harsh direct frontal lighting, flattened color planes. "
        "Tactile material texture emphasis. Subtle film grain. "
        "Poster-like composition with strong graphic intent."
    ),
    "electron-monochrome": (
        "Hyper-fisheye lens distortion filling the entire frame, no vignetting, no edge blur. "
        "Extreme monochromatic tonal range from blown-out whites to dense blacks. "
        "Ultra-fine filamentary micro-texture as if imaged by scanning electron microscope "
        "at 10,000x magnification. Radial spiral vortex composition. "
        "No color, no warm tones, no atmospheric haze."
    ),
    "garden-microscope": (
        "Maximum chromatic saturation with harmonious palette — emerald, burnt orange, "
        "lime green, burgundy, teal — at uniform luminosity. "
        "Ultra-fine pointillist micro-texture on every surface: moss, raked sand, stone, foliage. "
        "Soft isometric overhead perspective, no sky, no horizon. "
        "Flat diffuse lighting with no directional shadows. "
        "Frame entirely filled with subject, zero negative space."
    ),
    "fantasy-fashion": (
        "Hyper-low angle portrait (camera below chin looking up), slight wide-angle distortion "
        "without vignetting. Cool D65 white balance — zero warm cast, zero golden hour. "
        "Deliberate warm-cool palette tension: deep red or burgundy against electric blue or teal. "
        "Fantasy costume elements rendered as tactile real-world materials with "
        "ultra-fine fabric texture detail — individual threads, velvet pile direction, "
        "translucent wing venation. Dramatic single-source cool top-front key light "
        "with hard shadow fall-off, no warm bounce. "
        "Autumnal background with orange-blue color separation at depth. "
        "Biomimetic skin clarity and 0.3mm sparkle micro-detail on reflective surfaces."
    ),
}

ANTI_GENERIC_SUFFIX = (
    " No readable text or labels. Avoid generic stock AI iconography, random neon particles, "
    "lens flare, and corporate 3D clipart aesthetics."
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


def call_text_model(prompt: str, api_key: str, model: str, max_tokens: int = 1024) -> str:
    """Chama modelo de texto via OpenRouter."""
    payload = json.dumps({
        "model": model,
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


def generate_prompts(
    post: dict,
    n_inline: int,
    api_key: str,
    prompt_model: str,
    style: str,
    style_notes: str,
) -> dict:
    """
    Usa modelo de texto barato para gerar prompts visuais contextualizados.
    Retorna dict com chaves: cover, card, inline (lista).
    """
    sections_str = "\n".join(f"- {s}" for s in post["sections"]) if post["sections"] else "(sem seções)"

    art_direction = STYLE_PROFILES.get(style, STYLE_PROFILES["default"])
    style_appendix = style_notes.strip()

    system_prompt = f"""Você é um diretor de arte editorial para um blog de tecnologia.
Dado o conteúdo de um post, crie prompts em inglês para geração de imagens editoriais.

POST:
Título: {post['title']}
Descrição: {post['description']}
Seções: {sections_str}
Resumo do conteúdo: {post['text'][:800]}

Direção de arte desejada:
- Base: {art_direction}
- Notas adicionais: {style_appendix if style_appendix else '(nenhuma)'}

Gere exatamente {2 + n_inline} prompts no formato JSON abaixo.
Cada prompt deve descrever conteúdo visual E composição coerente com a direção de arte.
Seja específico: formas, elementos, relações espaciais, metáforas visuais do tema,
hierarquia visual e enquadramento.

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

    raw = call_text_model(system_prompt, api_key, prompt_model)

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


def generate_image_bytes(
    prompt: str,
    api_key: str,
    image_model: str,
    style: str,
    style_notes: str,
    anti_generic: bool,
) -> bytes:
    """Gera imagem via OpenRouter e retorna bytes brutos."""
    style_suffix = STYLE_PROFILES.get(style, STYLE_PROFILES["default"])
    extra = f" {style_notes.strip()}" if style_notes.strip() else ""
    anti = ANTI_GENERIC_SUFFIX if anti_generic else ""

    payload = json.dumps({
        "model": image_model,
        "modalities": ["text", "image"],
        "messages": [{"role": "user", "content": f"{prompt} {style_suffix}{extra}{anti}"}],
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


def save_jpg_from_webp(src_webp: Path, dest_jpg: Path, quality: int = 92):
    """Converte um webp local para JPG (útil para Instagram Graph API)."""
    if not HAS_PIL:
        return
    img = Image.open(src_webp).convert("RGB")
    dest_jpg.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(dest_jpg), "JPEG", quality=quality)


def make_img_tag(path: Path, alt: str, width: int, height: int) -> str:
    rel = path.relative_to(ROOT)
    return (
        f'<img src="/{rel}" alt="{alt}" '
        f'width="{width}" height="{height}" loading="lazy" decoding="async">'
    )


# ──────────────────────────────────────────────
# Core
# ──────────────────────────────────────────────

def run(
    html_path: Path,
    n_inline: int,
    only: str | None,
    dry_run: bool,
    quality: int,
    api_key: str,
    style: str,
    style_notes: str,
    prompt_model: str,
    image_model: str,
    anti_generic: bool,
):
    post = extract_post_content(html_path)
    slug = post["slug"]
    assets_dir = ROOT / "assets" / "images" / "blog" / slug

    print(f"\n📄 Post: {post['title']}")
    print(f"📁 Assets: assets/images/blog/{slug}/\n")
    print(f"🎛️  Estilo: {style}")
    print(f"🧠 Prompt model: {prompt_model}")
    print(f"🖼️  Image model: {image_model}\n")

    # ── Gerar prompts ──
    print("💬 Gerando prompts com modelo de texto...")
    prompts = generate_prompts(post, n_inline, api_key, prompt_model, style, style_notes)

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
        img_bytes = generate_image_bytes(
            prompt,
            api_key,
            image_model,
            style,
            style_notes,
            anti_generic,
        )
        save_webp(img_bytes, dest, w, h, quality)

        # Gera card.jpg automaticamente para compatibilidade com Instagram.
        if name == "card" and dest.suffix.lower() == ".webp":
            save_jpg_from_webp(dest, dest.with_suffix(".jpg"))

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
    parser.add_argument("--style", choices=STYLE_PROFILES.keys(), default="default",
                        help="Perfil de direção de arte (padrão: default)")
    parser.add_argument("--style-notes", default="",
                        help="Notas extras de direção de arte para anexar ao prompt")
    parser.add_argument("--prompt-model", default=DEFAULT_PROMPT_MODEL,
                        help="Modelo para gerar prompts (padrão: google/gemini-2.0-flash-001)")
    parser.add_argument("--image-model", default=DEFAULT_IMAGE_MODEL,
                        help="Modelo para gerar imagem (padrão: openai/gpt-5.4-image-2)")
    parser.add_argument("--no-anti-generic", action="store_true",
                        help="Desativa restrições anti visual genérico")
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

    run(
        html_path,
        args.inline,
        args.only,
        args.dry_run,
        args.quality,
        api_key,
        args.style,
        args.style_notes,
        args.prompt_model,
        args.image_model,
        not args.no_anti_generic,
    )


if __name__ == "__main__":
    main()
