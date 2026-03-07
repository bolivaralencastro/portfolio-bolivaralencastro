# portfolio-bolivaralencastro

Portfolio HTML-first publicado no GitHub Pages em `https://bolivaralencastro.com.br`.

## Automacao editorial e SEO

Este repositorio usa scripts Python (stdlib) para manter metadados e indices editoriais sem CMS.

Arquivos e blocos gerados automaticamente:
- `sitemap.xml`
- `feed.xml`
- `feed.txt` (mantido sincronizado com `feed.xml` para compatibilidade)
- bloco `AUTO:blog-list` em `blog.html`
- bloco `AUTO:projects-list` em `projects.html`
- bloco `AUTO:latest-post` em `index.html`

Scripts:
- `python scripts/build_site_metadata.py`: gera sitemap, feed e blocos auto-gerados.
- `python scripts/build_site_metadata.py --check`: falha se os arquivos gerados estiverem desatualizados.
- `python scripts/validate_site.py`: valida SEO/editorial/integridade.

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
- pelo menos um `<h1>`
- todas as imagens com `alt` nao vazio
- recomendado: JSON-LD com `CreativeWork` e Open Graph/Twitter Card

## Teste local rapido

```bash
python scripts/build_site_metadata.py
python scripts/build_site_metadata.py --check
python scripts/validate_site.py
```

Se os comandos acima passarem, o PR tende a passar no CI.
