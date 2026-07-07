# Claude Code — Portfolio

@AGENTS.md

As instruções completas do repositório estão em `AGENTS.md` (importado acima) e as regras estruturais/SEO em `README.md`. Pontos críticos que sempre valem:

- Rode `python3 scripts/build_site_metadata.py` e `python3 scripts/validate_site.py` imediatamente antes de commitar mudanças de conteúdo público, e commite os arquivos gerados junto.
- A CSP não tem `unsafe-inline`: nunca cole scripts ou estilos inline; use arquivo externo em `assets/js/` registrado em `VERSIONED_ASSETS`.
- Não edite HTML gerado: páginas de `notes/`, blocos `AUTO:` e sitemap/feed vêm do pipeline.
- Imagens referenciadas: máx. 500KB e 2000px de largura; OG em JPEG 1200×630 <300KB; material-fonte pesado vai em `.referencias/` (gitignored), nunca em `assets/`.
