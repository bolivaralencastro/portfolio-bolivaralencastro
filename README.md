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
- `feed.xml`
- `feed.txt` (mantido sincronizado com `feed.xml` para compatibilidade)
- bloco `AUTO:blog-jsonld` em `blog.html` (CollectionPage + ItemList)
- bloco `AUTO:blog-list` em `blog.html`
- bloco `AUTO:projects-list` em `projects.html`
- bloco `AUTO:featured-projects` em `index.html`
- bloco `AUTO:latest-post` em `index.html`
- URLs versionadas para `/style.css` e `/assets/js/clarity.js` em todas as paginas publicas

Scripts:
- `python scripts/build_site_metadata.py`: gera sitemap, feed, blocos auto-gerados e atualiza o versionamento de assets publicos.
- `python scripts/build_site_metadata.py --check`: falha se os arquivos gerados ou as URLs versionadas de assets estiverem desatualizados.
- `python scripts/validate_site.py`: valida SEO/editorial/integridade.
- `python scripts/blog_image_workflow.py`: compoe tripticos horizontais sem corte e converte assets para `webp`.
- `python scripts/twitter_post.py`: publica conteudo do portfolio no X, com suporte a blog, projetos e paginas avulsas.

## Analytics

- O portfolio carrega o Microsoft Clarity por meio de [`assets/js/clarity.js`](./assets/js/clarity.js).
- O ID do projeto ativo e `t8asclyhhx`.
- Toda pagina publica deve incluir o loader do Clarity e a folha principal com URL versionada, por exemplo:
  - `<link rel="stylesheet" href="/style.css?v=HASH">`
  - `<script src="/assets/js/clarity.js?v=HASH" defer></script>`
- As paginas com CSP liberam `www.clarity.ms`, `*.clarity.ms` e `c.bing.com`.
- Para integrar um banner proprio no futuro, use `window.portfolioClarityConsent("granted" | "denied", "granted" | "denied")`.

## Cache de assets

- O HTML continua sem cache agressivo para evitar pagina velha apos deploy.
- CSS/JS estaticos devem ser servidos com URL versionada para permitir cache forte no Cloudflare sem risco pratico de stale asset.
- Sempre que `style.css` ou `assets/js/clarity.js` mudarem, rode `python scripts/build_site_metadata.py` antes de publicar se estiver trabalhando fora do CI.
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
- `<meta property="og:image" content="https://...">` (obrigatorio para capa na listagem do blog)
- recomendado para listagens: `assets/images/blog/<slug>/card.webp` em 960x540
- exatamente um `<h1>` (idealmente `class="p-name"`)
- `<time class="dt-published" datetime="YYYY-MM-DD">`
- JSON-LD com `"@type": "BlogPosting"`
- conteudo em `.e-content` com ao menos um paragrafo
- recomendado: Open Graph + Twitter Card (`og:*` e `twitter:*`)

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
