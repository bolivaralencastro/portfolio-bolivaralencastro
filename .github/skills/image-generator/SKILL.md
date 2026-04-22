---
name: image-generator
description: >
  Gera imagens editoriais para posts do blog via OpenRouter (openai/gpt-5.4-image-2).
  Use quando a tarefa envolve criar cover, card ou imagens inline para um post.
  Chama o script diretamente — não faz chamadas de API manualmente.
---

# Image Generator Skill

Gera imagens webp editoriais em um único comando CLI. Não consome tokens de contexto com base64.

## Pré-requisitos

- `OPENROUTER_API_KEY` no `.env`
- `Pillow` instalado: `pip3 install Pillow`
- `certifi` instalado: `pip3 install certifi`

## Comandos

```bash
# Cover do post (1400x787)
python3 scripts/generate_image.py "descrição visual" meu-slug/cover --preset cover

# Card social (960x540)
python3 scripts/generate_image.py "descrição visual" meu-slug/card --preset card

# Imagem inline no corpo do post (1200x675)
python3 scripts/generate_image.py "descrição visual" meu-slug/nome-da-imagem --preset inline

# Path absoluto ou relativo
python3 scripts/generate_image.py "descrição" assets/images/blog/slug/img.webp

# Listar presets
python3 scripts/generate_image.py --list-presets
```

### Resolução de path

- `slug/nome` (sem extensão) → `assets/images/blog/slug/nome.webp` criado automaticamente
- Path com extensão → usado como está (relativo ao root do projeto)

## Como escrever bons prompts

O script adiciona automaticamente contexto editorial padrão:
> "Dark charcoal background. Flat vector graphic style. Blue and teal accents. No readable text."

Então o prompt deve descrever **apenas o conteúdo visual**, sem repetir estilo:

```
✅ "Terminal window on the left, LinkedIn card on the right, connected by a data stream arrow"
✅ "OAuth flow: browser with authorize button, curved arrow to local server icon"
✅ "Three-step horizontal pipeline: HTML file → CLI checkmark → LinkedIn post"

❌ "A dark, editorial, flat vector illustration of..."  # desnecessário
❌ "Generate an image of..."  # desnecessário
```

Use `--raw-prompt` para desativar o contexto automático quando precisar de estilo diferente.

## Presets disponíveis

| Preset   | Dimensão   | Uso                          |
|----------|------------|------------------------------|
| `cover`  | 1400×787   | Capa do post (`cover.webp`)  |
| `card`   | 960×540    | Card social (`card.webp`)    |
| `inline` | 1200×675   | Imagens no corpo do post     |
| `square` | 800×800    | Uso geral                    |

## Fluxo típico para novo post

```bash
# 1. Gerar cover e card
python3 scripts/generate_image.py "descrição do post" meu-slug/cover --preset cover
python3 scripts/generate_image.py "variação para card" meu-slug/card --preset card

# 2. Gerar imagens inline (quantas precisar)
python3 scripts/generate_image.py "step 1 do fluxo" meu-slug/fluxo-01 --preset inline
python3 scripts/generate_image.py "detalhe técnico" meu-slug/detalhe-02 --preset inline
```

## Notas

- Cada chamada custa ~$0.22 (7024 image tokens no modelo gpt-5.4-image-2)
- Tempo médio por imagem: 90–150 segundos
- Arquivos PNG originais são descartados; só o webp final é mantido
- A chave `OPENROUTER_API_KEY` fica no `.env` (gitignored)
