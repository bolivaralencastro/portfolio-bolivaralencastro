# portfolio-bolivaralencastro

Portfolio HTML-first publicado no GitHub Pages em `https://bolivaralencastro.com.br`.

## Automacao editorial e SEO

Este repositorio usa scripts Python (stdlib) para manter metadados, indices editoriais e URLs versionadas de assets sem CMS.

## Camada agentica

Este repositorio agora inclui uma camada minima de customizacao para fluxos agentic no VS Code e em outros agentes compatíveis:

- `AGENTS.md`: regras gerais do workspace para agentes
- `.github/copilot-instructions.md`: instrucoes sempre ativas para GitHub Copilot
- `.github/instructions/blog-html.instructions.md`: convencoes especificas para `blog/*.html`
- `.github/skills/portfolio-editorial/SKILL.md`: workflow editorial reutilizavel para posts e revisoes
- `.github/skills/portfolio-blog-images/SKILL.md`: workflow reutilizavel para combinar imagens em trios e converter assets para webp
- `.github/prompts/*.prompt.md`: prompts prontos para criar, revisar e adaptar blogposts
- `.github/agents/blog-editor.agent.md`: agente editorial para estruturar e lapidar publicacoes do portfolio

Esses arquivos nao substituem o `README`; eles tornam o contexto operacional do repositorio mais facil de carregar e reaproveitar em tarefas recorrentes.

Arquivos, blocos e referencias gerados automaticamente:
- `sitemap.xml`
- `sitemap.txt`
- `feed.xml`
- `feed.txt` (mantido sincronizado com `feed.xml` para compatibilidade)
- bloco `AUTO:blog-jsonld` em `blog.html` (CollectionPage + ItemList)
- bloco `AUTO:blog-list` em `blog.html`
- bloco `AUTO:blog-pagination` em `blog.html`
- bloco `AUTO:projects-list` em `projects.html`
- bloco `AUTO:featured-projects` em `index.html`
- bloco `AUTO:latest-post` em `index.html`
- bloco `AUTO:now-notes` em `now.html`
- `notes/index.html`
- `notes/page/N.html` quando houver mais de 20 notas publicadas
- `notes/YYYY-MM-DD-slug.html` para cada nota publicada
- URLs versionadas para `/style.css` e `/assets/js/gtm.js` em todas as paginas publicas

Scripts:
- `python scripts/build_site_metadata.py`: gera sitemap, feed, blocos auto-gerados e atualiza o versionamento de assets publicos.
- `python scripts/build_site_metadata.py --check`: falha se os arquivos gerados ou as URLs versionadas de assets estiverem desatualizados.
- `python scripts/validate_site.py`: valida SEO/editorial/integridade.
- `python scripts/blog_image_workflow.py`: compoe tripticos horizontais sem corte e converte assets para `webp`.
- `python scripts/twitter_post.py`: publica conteudo do portfolio no X, com suporte a blog, projetos e paginas avulsas.

## Analytics

- O portfolio carrega Google Tag Manager por meio de [`assets/js/gtm.js`](./assets/js/gtm.js).
- O container ativo e `GTM-T3LNHCNR`.
- O container publica Google Analytics 4 (`G-Q08W81XJ0K`) e Microsoft Clarity (`t8asclyhhx`).
- Eventos proprios do site sao enviados ao `dataLayer` por [`assets/js/analytics-events.js`](./assets/js/analytics-events.js).
- Toda pagina publica deve incluir o loader do GTM, o script de eventos e a folha principal com URL versionada, por exemplo:
  - `<link rel="stylesheet" href="/style.css?v=HASH">`
  - `<script src="/assets/js/gtm.js?v=HASH" defer></script>`
  - `<script src="/assets/js/analytics-events.js?v=HASH" defer></script>`
- As paginas com CSP liberam GTM, GA4 e Clarity: `www.googletagmanager.com`, `www.google-analytics.com`, `*.google-analytics.com`, `www.clarity.ms`, `*.clarity.ms` e `c.bing.com`.
- Eventos enviados ao GTM/GA4:
  - `portfolio_page_context`
  - `portfolio_read_depth`
  - `portfolio_contact_click`
  - `portfolio_social_click`
  - `portfolio_outbound_click`
  - `portfolio_content_click`
- Parametros principais: `page_type`, `site_section`, `content_type`, `content_slug`, `content_title`, `content_category`, `content_date`, `page_path`, `page_location`, `canonical_url`, `link_url`, `link_text`, `link_domain`, `social_network`, `contact_type`, `target_content_type`, `target_content_slug` e `read_percent`.

## Cache de assets

- O HTML continua sem cache agressivo para evitar pagina velha apos deploy.
- CSS/JS estaticos devem ser servidos com URL versionada para permitir cache forte no Cloudflare sem risco pratico de stale asset.
- Sempre que `style.css`, `assets/js/gtm.js` ou `assets/js/analytics-events.js` mudarem, rode `python scripts/build_site_metadata.py` antes de publicar se estiver trabalhando fora do CI.
- Para cards de listagem, prefira `card.webp` no mesmo diretorio da imagem social. O gerador usa `card.webp`, cai para `cover.webp` e so usa `og.*` como ultimo fallback.

## Workflows GitHub Actions

- `.github/workflows/validate-content.yml`
  - roda em `pull_request` e `push`
  - executa `build_site_metadata.py --check`
  - executa `validate_site.py`
  - funciona como rede de seguranca remota, nao como gerador automatico de conteudo

## Fluxo recomendado de publicacao

Este repositorio segue um fluxo `local-first` para conteudo publicado:

1. editar o HTML e os assets localmente
2. rodar `python3 scripts/build_site_metadata.py`
3. rodar `python3 scripts/validate_site.py`
4. publicar somente depois que a validacao local estiver limpa

Nao ha mais workflow de GitHub Actions fazendo commit automatico em `main`. Isso evita divergencias artificiais entre `main` local e remoto, reduz conflitos em arquivos gerados e combina melhor com um fluxo solo de publicacao direta.

## Fluxo de notas

Notas publicadas no `Now` agora nascem em `content/notes/*.md`.

- um arquivo por nota
- `now.html` continua como porta de entrada editorial
- cada nota publicada ganha uma pagina propria em `notes/YYYY-MM-DD-slug.html`
- o arquivo completo das notas fica em `notes/index.html` e `notes/page/N.html`
- `python3 scripts/build_site_metadata.py` le a pasta de notas e regenera o bloco `AUTO:now-notes`
- `python3 scripts/build_site_metadata.py` tambem gera as paginas individuais das notas, o arquivo paginado, o `sitemap.xml`, o `sitemap.txt`, o `feed.xml` e o `feed.txt`
- `python3 scripts/validate_site.py` valida o `now.html` e os arquivos-fonte das notas

Formato recomendado:

```md
---
title: Lendo O infinito em um junco
date: 2026-05-20
category: Leitura em curso
classes: note-seed
status: published
---

{{ image src="/assets/images/now/exemplo.webp" alt="Descricao da imagem." width="1440" height="1280" }}

Texto da nota com [links](https://example.com), *italico*, listas e citacoes.

{{ audio src="/assets/audio/notas/exemplo.m4a" caption="Trecho de audio." }}
{{ video src="/assets/video/notas/exemplo.mp4" poster="/assets/images/now/exemplo-poster.webp" caption="Clip curto." }}
```

Campos e regras:

- `date`: obrigatorio no front matter ou no prefixo do arquivo (`YYYY-MM-DD-slug.md`)
- `category`: opcional, padrao `Nota`
- `classes`: opcional, para reaproveitar estilos como `note-seed`
- `status`: `published` ou `draft`; rascunhos nao entram no `now.html`
- notas publicadas entram no feed e no sitemap
- shortcodes suportados: `image`, `audio`, `video`
- para casos mais especificos, blocos HTML puros tambem podem ser embutidos no corpo

Fluxo recomendado para publicar uma nota:

1. criar `content/notes/YYYY-MM-DD-slug.md`
2. rodar `python3 scripts/build_site_metadata.py`
3. rodar `python3 scripts/validate_site.py`
4. commitar e publicar

Atalho recomendado para agentes e terminal:

```bash
python3 scripts/note.py new "Titulo da nota" \
  --body "Texto da nota" \
  --direct-main
```

Esse comando:

- cria o arquivo em `content/notes/`
- regenera `now.html`
- gera ou atualiza `notes/`
- atualiza `feed.xml`, `feed.txt`, `sitemap.xml` e `sitemap.txt`
- roda `validate_site.py`
- cria um commit isolado a partir de `origin/main`
- faz `git push` direto para `main`
- evita PR e nao depende da branch local atual

Esse e o fluxo mais simples para site estatico com GitHub Pages: a nota entra em `main` e o deploy do site segue o comportamento normal do Pages apos o push.

Para criar e publicar na branch local atual, mantendo o fluxo Git normal:

```bash
python3 scripts/note.py new "Titulo da nota" \
  --body "Texto da nota"
```

Para criar sem publicar ainda:

```bash
python3 scripts/note.py new "Titulo da nota" \
  --body "Texto da nota" \
  --no-publish
```

Para publicar uma nota ja criada:

```bash
python3 scripts/note.py publish content/notes/YYYY-MM-DD-slug.md
```

## Publicacao social via CLI

Fluxos locais disponiveis:

- LinkedIn: `python3 scripts/linkedin_post.py`
- Instagram: `python3 scripts/instagram_post.py`
- X: `python3 scripts/twitter_post.py`

Exemplos do X:

```bash
# ultimo post do blog
python3 scripts/twitter_post.py --dry-run
python3 scripts/twitter_post.py

# projeto especifico
python3 scripts/twitter_post.py --dry-run --kind project --slug keeps-learning-konquest
python3 scripts/twitter_post.py --kind project --slug keeps-learning-konquest

# pagina avulsa
python3 scripts/twitter_post.py --dry-run --path about.html
```

Credenciais esperadas no `.env` para o X:

```bash
X_API_KEY=<api_key>
X_API_SECRET=<api_secret>
X_ACCESS_TOKEN=<access_token>
X_ACCESS_TOKEN_SECRET=<access_token_secret>
X_CALLBACK_URL=http://127.0.0.1:8080/callback
X_USERNAME=<handle_opcional>
```

Na primeira configuracao, rode `python3 scripts/twitter_auth.py` para concluir o OAuth 1.0a e salvar os tokens no `.env`.

## Pesquisa de videos do YouTube

O repositorio agora inclui um fluxo local para transformar um video do YouTube em material de pesquisa editorial:

- transcript publico do video
- fallback de audio com `yt-dlp` + `ffmpeg` + OpenRouter STT
- comentarios top-level
- replicas de comentarios
- relatorio com perguntas, dores e oportunidades de conteudo
- leitura AI opcional com DeepSeek para temas, perguntas e proximas pecas

Configuracao no `.env`:

```bash
YOUTUBE_API_KEY=<api_key_do_youtube_data_api_v3>
OPENROUTER_API_KEY=<api_key_openrouter>
```

Uso:

```bash
python3 youtube-research/scripts/collect_video_research.py 'https://www.youtube.com/watch?v=VIDEO_ID'
python3 youtube-research/scripts/collect_video_research.py 'https://youtu.be/VIDEO_ID' --lang pt
python3 youtube-research/scripts/collect_video_research.py 'https://youtu.be/VIDEO_ID' --force-stt
python3 youtube-research/scripts/analyze_learning.py youtube-research/videos/<titulo-do-video>--VIDEO_ID
```

Estrutura:

- `youtube-research/scripts/`: coleta e analise
- `youtube-research/prompts/`: prompts versionaveis/refinaveis
- `youtube-research/videos/<titulo-do-video>--<video_id>/`: uma pasta por video analisado

Saida gerada em `youtube-research/videos/<titulo-do-video>--<video_id>/`:

- `video.json`
- `transcript.json`
- `transcript.txt`
- `comments.json`
- `summary.json`
- `report.md`
- `transcript_debug.json`
- `ai_insights.json` (quando a analise AI estiver ativa)
- `ai_insights_learning.json` (segunda camada de analise)
- `final-learning-report.md` (arquivo final para leitura humana)

Observacao importante:
- comentarios e replicas usam a YouTube Data API v3 no fluxo de YouTube
- Instagram entra apenas no modo de transcricao por audio; nao ha coleta de comentarios nesse conector
- o script tenta captions publicas primeiro
- a resolucao de idioma segue esta ordem: `--lang` explicito, `defaultAudioLanguage`, `defaultLanguage`, autodeteccao do STT
- por padrao, a lingua do STT e autodetectada; use `--lang pt`, `--lang en` etc. apenas quando quiser forcar
- se o video nao expuser captions publicas, ele pode cair para extracao local de audio, segmentacao em lotes e transcricao via OpenRouter
- o modelo padrao de STT e `openai/whisper-large-v3`; o modelo DeepSeek entra na limpeza do transcript e na analise editorial, nao na captura bruta de fala

## Jules (CLI + REST API)

Instalacao do CLI:

```bash
npm install -g @google/jules
jules version
```

Login no CLI (abre o navegador):

```bash
jules login
```

Onde adicionar a chave da API do Jules:

- arquivo: `.env` na raiz do repositorio
- variavel: `JULES_API_KEY`

Exemplo:

```bash
JULES_API_KEY=<sua_chave_jules>
```

Teste rapido da API (listar repositorios conectados):

```bash
curl 'https://jules.googleapis.com/v1alpha/sources' \
  -H "X-Goog-Api-Key: $JULES_API_KEY"
```

Se preferir, exporte a chave so na sessao atual do terminal:

```bash
export JULES_API_KEY="<sua_chave_jules>"
```

## Como criar um novo post (`/blog/*.html`)

Metadados minimos obrigatorios:
- `<html lang="pt-BR">`
- `<title>...</title>`
- `<meta name="description" content="...">`
- `<link rel="canonical" href="https://bolivaralencastro.com.br/blog/slug.html">`
- `<link rel="author" href="https://bolivaralencastro.com.br/about.html">` em posts autorais
- `<meta property="og:image" content="https://...">` (obrigatorio para capa na listagem do blog)
- recomendado para listagens: `assets/images/blog/<slug>/card.webp` em 960x540
- exatamente um `<h1>` (idealmente `class="p-name"`)
- `<time class="dt-published" datetime="YYYY-MM-DD">`
- JSON-LD com `"@type": "BlogPosting"`
- conteudo em `.e-content` com ao menos um paragrafo
- recomendado: Open Graph + Twitter Card (`og:*` e `twitter:*`)

Camada editorial recomendada para posts longos:
- metadata visivel com autor em `u-author h-card` e `rel="author"`
- `.p-summary` como resumo editorial do post
- `.quick-answer` logo depois da summary para uma tese curta, autocontida e citavel
- `p-category` para categoria principal e, quando concreto, tags secundarias
- `.references` no fim do corpo quando fontes externas sustentam a leitura
- `BlogPosting` JSON-LD com `inLanguage`, `articleSection`, `keywords`, `author.url`, `datePublished`, `dateModified`, `image`, `description` e `url`
- evitar `FAQPage` como padrao editorial; use FAQ apenas quando perguntas e respostas forem parte real do conteudo visivel

Heuristicas usadas no feed:
- titulo: `<h1 class="p-name">` ou `<title>`
- data: `time.dt-published[datetime]`
- resumo: `.p-summary`, ou primeiro paragrafo de `.e-content`
- trecho curto: primeiro paragrafo de `.e-content`

## Regras de voz editorial

- evitar estruturas de contraste automatico como `menos X, mais Y` e `nao foi X, foi Y`
- evitar abstrair demais quando o texto pode nomear as camadas concretas
- nao inflar workshop, meetup ou palestra como revelacao total quando o ponto real e reforco, clarificacao ou mudanca de escala
- adaptar o card `Sobre o autor` ao tema do post com alguma inteligencia contextual

## Como criar um novo projeto (`/projects/*.html`)

Metadados minimos obrigatorios:
- `<html lang="pt-BR">`
- `<title>...</title>`
- `<meta name="description" content="...">`
- `<link rel="canonical" href="https://bolivaralencastro.com.br/projects/slug.html">`
- `<meta property="og:image" content="https://...">` (obrigatorio para capa na listagem de projetos)
- recomendado para listagens: `assets/images/projects/<slug>/card.webp` em 960x540
- pelo menos um `<h1>`
- todas as imagens com `alt` nao vazio
- imagens dentro de `.e-content` com `width` e `height` numericos para preservar proporcao em web e mobile
- primeira imagem dentro de `.e-content` sem `loading="lazy"` e com `fetchpriority="high"`
- imagens seguintes dentro de `.e-content` com `loading="lazy"`
- todas as imagens dentro de `.e-content` com `decoding="async"`
- recomendado: JSON-LD com `CreativeWork` e Open Graph/Twitter Card

## Teste local rapido

```bash
python scripts/build_site_metadata.py
python scripts/build_site_metadata.py --check
python scripts/validate_site.py
```

Se os comandos acima passarem, o PR tende a passar no CI.

Se voce publica direto em `main`, a mesma regra vale: gere e valide localmente antes do push.
