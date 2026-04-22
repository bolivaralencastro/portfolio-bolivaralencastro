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


def generate_image_b64(prompt: str, api_key: str) -> bytes:
    """Chama a API e retorna os bytes brutos da imagem."""
    payload = json.dumps({
        "model": MODEL,
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


def build_editorial_prompt(user_prompt: str) -> str:
    """Adiciona contexto editorial padrão ao prompt do usuário."""
    return (
        f"{user_prompt} "
        "Dark charcoal background. Flat vector graphic style. "
        "Blue and teal accent colors. No readable text or labels in the image. "
        "Clean, minimal, modern editorial illustration."
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
    prompt = args.prompt if args.raw_prompt else build_editorial_prompt(args.prompt)

    print(f"🎨 Gerando imagem ({w}x{h})...")
    print(f"   Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")
    print(f"   Destino: {dest.relative_to(ROOT) if dest.is_relative_to(ROOT) else dest}")

    try:
        img_bytes = generate_image_b64(prompt, api_key)
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
