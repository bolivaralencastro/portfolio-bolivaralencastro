# portfolio-bolivaralencastro

Portfolio HTML-first publicado no GitHub Pages em `https://bolivaralencastro.com.br`.

## Automacao editorial e SEO

Este repositorio usa scripts Python (stdlib) para manter metadados, indices editoriais e URLs versionadas de assets sem CMS.

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
- `.github/workflows/refresh-site-metadata.yml`
  - roda em `push` para `main`
  - regenera metadados e indices
  - faz commit automatico quando houver mudancas nos arquivos gerados
  - evita loop usando `if: github.actor != 'github-actions[bot]'`

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
