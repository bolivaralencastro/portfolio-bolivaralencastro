#!/usr/bin/env python3
"""
Transforma uma foto real em ilustração editorial via OpenRouter (image-to-image).

Usage:
    python3 scripts/generate_image_from_photo.py foto.jpg "prompt de estilo" output/path.webp
    python3 scripts/generate_image_from_photo.py foto.jpg "prompt" blog/meu-post/cover.webp --width 1600 --height 900

O prompt descreve a transformação desejada; a imagem de entrada é enviada como
referência visual (pose, composição, likeness) para o modelo de imagem.
"""

import argparse
import base64
import json
import mimetypes
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

MODEL = "google/gemini-2.5-flash-image"


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


def encode_image(path: Path) -> str:
    mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"
    data = base64.b64encode(path.read_bytes()).decode()
    return f"data:{mime};base64,{data}"


def generate_image_b64(prompt: str, image_data_url: str, api_key: str, model: str) -> bytes:
    payload = json.dumps({
        "model": model,
        "modalities": ["text", "image"],
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_data_url}},
            ],
        }],
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
        raise ValueError(f"Nenhuma imagem na resposta da API. Resposta: {raw[:500]}")
    return base64.b64decode(m.group(1))


def save_as_webp(img_bytes: bytes, dest: Path, width: int, height: int, quality: int = 85):
    if not HAS_PIL:
        dest.with_suffix(".png").write_bytes(img_bytes)
        print(f"⚠️  PIL não instalado. Salvo como PNG: {dest.with_suffix('.png')}")
        return

    from io import BytesIO
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


def resolve_output_path(raw: str) -> Path:
    p = Path(raw)
    if p.suffix:
        return p if p.is_absolute() else ROOT / p
    parts = p.parts
    if len(parts) == 2:
        slug, name = parts
        dest = ROOT / "assets" / "images" / "blog" / slug / f"{name}.webp"
        dest.parent.mkdir(parents=True, exist_ok=True)
        return dest
    return (p if p.is_absolute() else ROOT / p).with_suffix(".webp")


def main():
    parser = argparse.ArgumentParser(description="Transforma foto em ilustração via OpenRouter (img2img)")
    parser.add_argument("source", help="Caminho da foto de origem")
    parser.add_argument("prompt", help="Prompt de estilo/transformação")
    parser.add_argument("output", help="Destino: path ou slug/nome")
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--height", type=int, default=1200)
    parser.add_argument("--quality", type=int, default=88)
    parser.add_argument("--model", default=MODEL)
    args = parser.parse_args()

    api_key = load_api_key()
    if not api_key:
        print("❌ OPENROUTER_API_KEY não encontrado no .env ou nas variáveis de ambiente.")
        sys.exit(1)

    source = Path(args.source)
    if not source.is_absolute():
        source = Path.cwd() / source
    if not source.exists():
        print(f"❌ Foto não encontrada: {source}")
        sys.exit(1)

    dest = resolve_output_path(args.output)

    print(f"🎨 Transformando {source.name} ({args.width}x{args.height})...")
    print(f"   Modelo: {args.model}")
    print(f"   Prompt: {args.prompt[:100]}{'...' if len(args.prompt) > 100 else ''}")
    print(f"   Destino: {dest.relative_to(ROOT) if dest.is_relative_to(ROOT) else dest}")

    try:
        image_data_url = encode_image(source)
        img_bytes = generate_image_b64(args.prompt, image_data_url, api_key, args.model)
        save_as_webp(img_bytes, dest, args.width, args.height, args.quality)
        size_kb = dest.stat().st_size // 1024
        print(f"✅ Salvo: {dest.relative_to(ROOT) if dest.is_relative_to(ROOT) else dest} ({size_kb}KB)")
    except urllib.error.HTTPError as e:
        print(f"❌ Erro HTTP {e.code}: {e.read().decode()[:500]}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
