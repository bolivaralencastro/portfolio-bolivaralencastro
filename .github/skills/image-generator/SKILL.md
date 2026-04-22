---
name: image-generator
description: >
  Gera imagens editoriais para posts do blog via OpenRouter (openai/gpt-5.4-image-2).
  Use quando a tarefa envolve criar imagens para um post. Para um post novo completo,
  use generate_post_images.py que gera tudo automaticamente. Para imagens avulsas
  com prompt específico, use generate_image.py.
---

# Image Generator Skill

Dois scripts disponíveis dependendo do contexto:

## Para posts novos — `generate_post_images.py` (recomendado)

Lê o HTML do post, gera prompts visuais com modelo de texto barato e cria todas as imagens em paralelo.

```bash
# Ver prompts antes de gastar (sem custo de imagem)
python3 scripts/generate_post_images.py blog/<slug>.html --dry-run

# Gerar cover + card + 2 inline (padrão)
python3 scripts/generate_post_images.py blog/<slug>.html

# Gerar com direção de arte mais diagramática
python3 scripts/generate_post_images.py blog/<slug>.html --style diagrammatic

# Adicionar briefing de estilo do projeto
python3 scripts/generate_post_images.py blog/<slug>.html --style-notes "bold asymmetry, dense composition, no empty center"

# Gerar cover + card + 3 inline
python3 scripts/generate_post_images.py blog/<slug>.html --inline 3

# Gerar só a cover
python3 scripts/generate_post_images.py blog/<slug>.html --only cover
```

**Saída:** salva webps em `assets/images/blog/<slug>/` e imprime `<img>` tags prontas para colar no HTML.

## Para imagens avulsas — `generate_image.py`

Quando o prompt é específico e conhecido de antemão.

```bash
# Usando preset
python3 scripts/generate_image.py "descrição visual" slug/nome --preset cover
python3 scripts/generate_image.py "descrição visual" slug/nome --preset card
python3 scripts/generate_image.py "descrição visual" slug/nome --preset inline

# Controlando direção de arte e modelo
python3 scripts/generate_image.py "descrição visual" slug/nome --preset cover --style constructivist
python3 scripts/generate_image.py "descrição visual" slug/nome --style-notes "editorial collage, gritty paper texture"
python3 scripts/generate_image.py "descrição visual" slug/nome --model openai/gpt-5.4-image-2

# Path direto
python3 scripts/generate_image.py "descrição" assets/images/blog/slug/img.webp

# Listar presets disponíveis
python3 scripts/generate_image.py --list-presets
```

## Presets

| Preset   | Dimensão   | Uso                          |
|----------|------------|------------------------------|
| `cover`  | 1400×787   | Capa do post (`cover.webp`)  |
| `card`   | 960×540    | Card social (`card.webp`)    |
| `inline` | 1200×675   | Imagens no corpo do post     |
| `square` | 800×800    | Uso geral                    |

## Alavancas de qualidade (novas)

Os scripts agora permitem calibrar direção de arte:

- `--style`: `default`, `diagrammatic`, `newsprint-collage`, `constructivist`
- `--style-notes`: briefing adicional para amarrar o estilo ao post
- `--no-anti-generic`: desativa bloqueios de visual genérico (normalmente mantenha ligado)
- `--prompt-model` (apenas em `generate_post_images.py`): modelo que cria os prompts
- `--image-model`: modelo final de geração de imagem

## Escrevendo prompts para `generate_image.py`

O script injeta contexto editorial automaticamente (dark background, flat vector, blue/teal, no text).
Descreva apenas o **conteúdo visual**:

```
✅ "Terminal window on the left, LinkedIn card on the right, connected by a data stream"
✅ "Three-step pipeline: HTML file → CLI checkmark → LinkedIn post"
❌ "A dark editorial flat vector illustration of..."  # redundante
```

Use `--raw-prompt` para desativar o contexto automático.

## Pré-requisitos

- `OPENROUTER_API_KEY` no `.env`
- `pip3 install Pillow certifi`

## Custo estimado

- ~$0.22 por imagem (modelo gpt-5.4-image-2)
- Geração de prompts via `generate_post_images.py`: ~$0.001 (Gemini Flash)
