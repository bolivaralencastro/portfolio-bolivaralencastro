#!/usr/bin/env python3
"""
Gera imagens editoriais via OpenRouter e salva como webp.

Usage:
    python3 scripts/generate_image.py "prompt aqui" output/path.webp
    python3 scripts/generate_image.py "prompt" blog/meu-post/cover.webp --width 1400
    python3 scripts/generate_image.py "prompt" blog/meu-post/card.webp --preset card
    python3 scripts/generate_image.py --list-presets

Presets:
    cover   → 1400x787  (16:9, capa do post)
    card    → 960x540   (16:9, card social)
    inline  → 1200x675  (16:9, imagem inline no post)
    square  → 800x800   (1:1, uso geral)

O path de saída pode ser:
    - Caminho absoluto
    - Relativo ao cwd
    - Slug de post: "meu-post/cover" → assets/images/blog/meu-post/cover.webp
"""

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

PRESETS = {
    "cover":  (1400, 787),
    "card":   (960, 540),
    "inline": (1200, 675),
    "square": (800, 800),
}

MODEL = "openai/gpt-5.4-image-2"

STYLE_PROFILES = {
    "default": (
        "Dark charcoal background. Flat vector graphic style. "
        "Blue and teal accent colors. Clean, minimal, modern editorial illustration."
    ),
    "diagrammatic": (
        "Diagrammatic editorial style. Strong geometric blocks and clear visual hierarchy. "
        "Dark slate background with cyan accents. Crisp edges and restrained detail."
    ),
    "newsprint-collage": (
        "Editorial collage style inspired by magazine art direction. "
        "Textured paper feeling, cutout shapes, bold contrast, limited palette."
    ),
    "constructivist": (
        "Constructivist editorial poster style with angular forms and dynamic diagonals. "
        "High contrast composition and assertive negative space."
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
    " Avoid generic stock AI iconography, floating random particles, lens flare, "
    "and corporate 3D clipart aesthetics. No readable text or labels in the image."
)


def load_api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if key:
        return key
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                if k.strip() == "OPENROUTER_API_KEY":
                    return v.strip()
    return ""


def resolve_output_path(raw: str) -> Path:
    """
    Resolve o path de saída:
    - Se contiver '/' e não começar com assets/, trata como path direto
    - Se for "slug/nome" sem extensão → assets/images/blog/slug/nome.webp
    - Se for path relativo/absoluto normal, usa como está
    """
    p = Path(raw)
    # Já tem extensão → usa como está (relativo ao ROOT se não for absoluto)
    if p.suffix:
        return p if p.is_absolute() else ROOT / p
    # Sem extensão: slug/nome → assets/images/blog/slug/nome.webp
    parts = p.parts
    if len(parts) == 2:
        slug, name = parts
        dest = ROOT / "assets" / "images" / "blog" / slug / f"{name}.webp"
        dest.parent.mkdir(parents=True, exist_ok=True)
        return dest
    # Fallback: adiciona .webp
    return (p if p.is_absolute() else ROOT / p).with_suffix(".webp")


def generate_image_b64(prompt: str, api_key: str, model: str) -> bytes:
    """Chama a API e retorna os bytes brutos da imagem."""
    payload = json.dumps({
        "model": model,
        "modalities": ["text", "image"],
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096,
    }).encode()

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://bolivaralencastro.com.br",
            "X-Title": "Portfolio Image Generator",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=180) as r:
        raw = r.read().decode()

    m = re.search(r'data:image/[a-z]+;base64,([A-Za-z0-9+/=]+)', raw)
    if not m:
        raise ValueError("Nenhuma imagem na resposta da API.")
    return base64.b64decode(m.group(1))


def save_as_webp(img_bytes: bytes, dest: Path, width: int, height: int, quality: int = 85):
    """Salva a imagem como webp com crop 16:9 e resize."""
    if not HAS_PIL:
        # Salva o PNG bruto se PIL não disponível
        dest.with_suffix(".png").write_bytes(img_bytes)
        print(f"⚠️  PIL não instalado. Salvo como PNG: {dest.with_suffix('.png')}")
        return

    from io import BytesIO
    img = Image.open(BytesIO(img_bytes)).convert("RGB")
    ow, oh = img.size

    # Crop para proporção alvo
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


def build_editorial_prompt(
    user_prompt: str,
    style: str,
    style_notes: str,
    use_anti_generic: bool,
) -> str:
    """Monta prompt editorial com perfil de estilo configurável."""
    style_suffix = STYLE_PROFILES.get(style, STYLE_PROFILES["default"])
    extra = f" {style_notes.strip()}" if style_notes.strip() else ""
    anti = ANTI_GENERIC_SUFFIX if use_anti_generic else ""
    return (
        f"{user_prompt} "
        f"{style_suffix}{extra}{anti}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Gera imagens editoriais via OpenRouter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("prompt", nargs="?", help="Descrição da imagem a gerar")
    parser.add_argument("output", nargs="?", help="Destino: path ou slug/nome")
    parser.add_argument("--preset", choices=PRESETS.keys(), default="inline",
                        help="Preset de tamanho (padrão: inline 1200x675)")
    parser.add_argument("--width", type=int, help="Largura em px (sobrescreve preset)")
    parser.add_argument("--height", type=int, help="Altura em px (sobrescreve preset)")
    parser.add_argument("--quality", type=int, default=85, help="Qualidade webp 1-100 (padrão: 85)")
    parser.add_argument("--raw-prompt", action="store_true",
                        help="Usa o prompt exatamente como fornecido, sem contexto editorial")
    parser.add_argument("--style", choices=STYLE_PROFILES.keys(), default="default",
                        help="Perfil de direção de arte (padrão: default)")
    parser.add_argument("--style-notes", default="",
                        help="Notas extras de direção de arte para anexar ao prompt")
    parser.add_argument("--no-anti-generic", action="store_true",
                        help="Desativa as restrições anti visual genérico")
    parser.add_argument("--model", default=MODEL,
                        help="Modelo de imagem (padrão: openai/gpt-5.4-image-2)")
    parser.add_argument("--list-presets", action="store_true", help="Lista os presets disponíveis")
    args = parser.parse_args()

    if args.list_presets:
        print("Presets disponíveis:")
        for name, (w, h) in PRESETS.items():
            print(f"  {name:8s} → {w}x{h}")
        return

    if not args.prompt or not args.output:
        parser.print_help()
        sys.exit(1)

    api_key = load_api_key()
    if not api_key:
        print("❌ OPENROUTER_API_KEY não encontrado no .env ou nas variáveis de ambiente.")
        sys.exit(1)

    # Resolve dimensões
    w, h = PRESETS[args.preset]
    if args.width:
        w = args.width
    if args.height:
        h = args.height

    dest = resolve_output_path(args.output)
    prompt = args.prompt if args.raw_prompt else build_editorial_prompt(
        args.prompt,
        args.style,
        args.style_notes,
        not args.no_anti_generic,
    )

    print(f"🎨 Gerando imagem ({w}x{h})...")
    print(f"   Estilo: {args.style}")
    print(f"   Modelo: {args.model}")
    print(f"   Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")
    print(f"   Destino: {dest.relative_to(ROOT) if dest.is_relative_to(ROOT) else dest}")

    try:
        img_bytes = generate_image_b64(prompt, api_key, args.model)
        save_as_webp(img_bytes, dest, w, h, args.quality)
        size_kb = dest.stat().st_size // 1024
        print(f"✅ Salvo: {dest.relative_to(ROOT) if dest.is_relative_to(ROOT) else dest} ({size_kb}KB)")
    except urllib.error.HTTPError as e:
        print(f"❌ Erro HTTP {e.code}: {e.read().decode()[:200]}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
