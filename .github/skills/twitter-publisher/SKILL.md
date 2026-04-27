---
name: twitter-publisher
description: >
  Publica conteudo do portfolio no X via CLI usando a API oficial.
  Use quando a tarefa envolve divulgar blog posts, projetos ou paginas
  avulsas do site com dry run, slug ou path explicito.
---

# Twitter Publisher Skill

Publica conteudo do portfolio no X com imagem quando a propria pagina
ja expoe `og:image` ou `twitter:image` apontando para um asset local.

## Pre-requisitos

- Python 3.10+
- `.env` na raiz com as credenciais do X

## Fluxo padrao

```bash
# 1. Primeira vez: autenticar e salvar tokens
python3 scripts/twitter_auth.py

# 2. Publicar o ultimo post do blog
python3 scripts/twitter_post.py

# 3. Dry run
python3 scripts/twitter_post.py --dry-run

# 4. Publicar blog especifico
python3 scripts/twitter_post.py --slug nome-do-slug

# 5. Publicar projeto especifico
python3 scripts/twitter_post.py --kind project --slug keeps-learning-konquest

# 6. Publicar pagina avulsa
python3 scripts/twitter_post.py --path about.html
```

## Configuracao do `.env`

```bash
X_API_KEY=<api_key>
X_API_SECRET=<api_secret>
X_ACCESS_TOKEN=<access_token>
X_ACCESS_TOKEN_SECRET=<access_token_secret>
X_CALLBACK_URL=http://127.0.0.1:8080/callback
X_USERNAME=<handle_opcional>
```

## Como a selecao de conteudo funciona

- Sem argumentos: publica o post mais recente em `blog/`, usando `<time datetime="...">`
- `--slug <slug>` com `--kind blog`: publica `blog/<slug>.html`
- `--kind project --slug <slug>`: publica `projects/<slug>.html`
- `--path <arquivo.html>`: publica qualquer HTML do repositorio

## Como a imagem funciona

- O script le `og:image` ou `twitter:image` da propria pagina
- Se a URL apontar para um asset local do dominio principal, faz upload da imagem
- Se nao houver imagem local compativel, publica apenas texto + URL

## Arquivos relevantes

- `scripts/twitter_auth.py` — fluxo OAuth 1.0a
- `scripts/twitter_post.py` — publicador principal
- `.social_publish_state/twitter_last_publish.json` — trava local contra repost acidental

## Notas tecnicas

- O script usa OAuth 1.0a user context
- O upload de imagem usa `https://upload.twitter.com/1.1/media/upload.json`
- A criacao do tweet usa `https://api.twitter.com/2/tweets`
