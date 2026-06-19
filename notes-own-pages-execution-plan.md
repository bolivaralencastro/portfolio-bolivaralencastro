# Plano de Execucao: Notas com Pagina Propria

Este plano deve ser executado por uma IA com acesso ao repositorio local.

Objetivo final:

- manter `now.html` como ponto de entrada editorial das notas
- dar URL propria e indexavel para cada nota
- criar arquivo paginado de notas
- preparar a arquitetura para futuras IAs criarem notas, blogposts e atualizarem o site sem ambiguidade
- manter o site `HTML-first`, estatico e gerado localmente

## Resultado final esperado

Ao concluir este plano, o site deve funcionar assim:

- `content/notes/*.md` continua sendo a source of truth das notas
- cada nota publicada gera uma pagina HTML propria em `notes/`
- `now.html` mostra o contexto atual e uma selecao das notas mais recentes
- existe um arquivo paginado de notas em `notes/index.html` e `notes/page/N.html`
- notas publicadas entram no `sitemap.xml`
- notas publicadas entram no `feed.xml` e `feed.txt`
- a CLI de notas continua simples
- o fluxo de publicacao direta para `main` continua disponivel para notas
- as instrucoes para agentes ficam alinhadas com a nova arquitetura

## Decisoes fechadas

Estas decisoes nao devem ser reabertas durante a execucao, a menos que o usuario mude explicitamente de direcao.

- Prefixo publico das notas: `notes/`
- URL de cada nota: `notes/YYYY-MM-DD-slug.html`
- Source de cada nota: `content/notes/YYYY-MM-DD-slug.md`
- `now.html` continua como porta de entrada editorial
- `now.html` deve mostrar as 12 notas mais recentes
- arquivo de notas: 20 notas por pagina
- pagina 1 do arquivo: `notes/index.html`
- paginas seguintes: `notes/page/2.html`, `notes/page/3.html`, etc.
- cada pagina paginada deve ter canonical proprio
- cada nota deve ter canonical proprio
- blog deve continuar com a URL atual dos posts em `blog/<slug>.html`
- a arquitetura de paginacao do blog deve ser preparada agora, mesmo que o volume atual ainda nao exija muitas paginas
- o site continua sem framework, sem CMS e sem geracao client-side
- nao usar PR como requisito do fluxo de notas
- o fluxo de nota sem friccao continua sendo push direto para `origin/main`

## Restricoes obrigatorias

A IA que executar este plano deve obedecer a tudo abaixo:

- ler `AGENTS.md` e `README.md` antes de editar
- nao introduzir frameworks, bundlers, CMS ou JS de renderizacao de conteudo
- nao transformar notas em paginas dinamicas
- nao depender de GitHub Actions para gerar arquivos locais
- nao editar manualmente blocos `AUTO:` que sejam gerados por script
- manter metadata publica correta: canonical, description, Open Graph, Twitter Card, JSON-LD e um `h1`
- preservar o estilo editorial existente do site
- usar `apply_patch` para edits manuais
- ao final, rodar:
  - `python3 scripts/build_site_metadata.py`
  - `python3 scripts/validate_site.py`

## Arquivos que certamente serao afetados

- `scripts/notes_pipeline.py`
- `scripts/build_site_metadata.py`
- `scripts/validate_site.py`
- `scripts/note.py`
- `now.html`
- `README.md`
- `AGENTS.md`
- `.github/copilot-instructions.md`
- `.github/skills/portfolio-notes-editorial/SKILL.md`
- `.github/skills/portfolio-notes-editorial/references/note-patterns.md`
- `.github/agents/note-editor.agent.md`
- `.github/prompts/new-note.prompt.md`

Arquivos que provavelmente precisarao ser criados ou passar a ser gerados:

- `notes/index.html`
- `notes/page/2.html` e demais paginas, quando houver volume
- `notes/YYYY-MM-DD-slug.html` para cada nota publicada

## Ordem de execucao obrigatoria

Execute exatamente nesta ordem.

### Etapa 1: Auditar o pipeline atual

Objetivo:

- entender como notas sao carregadas hoje
- mapear como `now.html`, `sitemap.xml`, `feed.xml` e validacoes sao gerados

Acoes:

1. Ler integralmente:
   - `scripts/notes_pipeline.py`
   - `scripts/build_site_metadata.py`
   - `scripts/validate_site.py`
   - `scripts/note.py`
2. Confirmar:
   - como o bloco `AUTO:now-notes` e gerado
   - como sitemap e feed sao gerados hoje
   - quais validacoes de metadata ja existem
3. Nao editar nada ainda.

Criterio de saida:

- a IA consegue explicar claramente onde cada uma destas responsabilidades mora no codigo

### Etapa 2: Definir o modelo publico das notas

Objetivo:

- enriquecer o modelo de nota para suportar pagina propria, arquivo e teaser no `Now`

Acoes:

1. Em `scripts/notes_pipeline.py`, estender o modelo de nota para expor:
   - `article_id`
   - `slug`
   - `public_url`
   - `canonical_url`
   - `page_title`
   - `description`
   - `excerpt_html` ou equivalente
   - `body_html`
2. Garantir que `description` seja curta, limpa e coerente com SEO.
3. Garantir que `body_html` e `excerpt_html` venham de uma unica fonte de renderizacao, sem duplicar logica.

Regras:

- `public_url` deve seguir `notes/YYYY-MM-DD-slug.html`
- `canonical_url` deve usar o dominio canonico ja adotado pelo site
- se a nota nao tiver `title`, a IA deve criar um fallback seguro para pagina e metadata

Criterio de saida:

- o pipeline consegue representar uma nota como item de feed, item de arquivo e pagina propria

### Etapa 3: Gerar pagina propria para cada nota

Objetivo:

- cada nota publicada deve virar uma pagina HTML completa e indexavel

Acoes:

1. Implementar em `scripts/notes_pipeline.py` uma funcao que renderize a pagina HTML completa da nota.
2. A pagina da nota deve conter:
   - `<!doctype html>`
   - `lang="pt-BR"`
   - `title`
   - `meta name="description"`
   - `canonical`
   - Open Graph
   - Twitter Card
   - JSON-LD apropriado
   - um `h1`
   - data de publicacao
   - corpo completo da nota
   - link visivel de volta para `/now.html`
   - link visivel para o arquivo de notas
3. Reaproveitar o header, footer e convencoes estruturais do site.
4. Nao inventar um layout completamente novo; preservar a linguagem visual atual.

Decisao editorial:

- a pagina propria da nota deve exibir o conteudo completo da nota
- nao usar teaser truncado na pagina individual

Criterio de saida:

- para cada nota publicada, existe um HTML proprio funcional em `notes/`

### Etapa 4: Criar o arquivo paginado de notas

Objetivo:

- criar uma superficie estavel de descoberta de todas as notas

Acoes:

1. Implementar geracao de:
   - `notes/index.html`
   - `notes/page/N.html`
2. Cada pagina do arquivo deve ter:
   - `title`
   - `description`
   - canonical proprio
   - `h1`
   - lista de notas com links para as paginas proprias
   - navegacao com links reais para pagina anterior e proxima
3. Nao usar fragmentos `#` para paginacao.
4. Nao usar JS para carregar mais itens.
5. Se houver apenas uma pagina, ainda assim `notes/index.html` deve existir.

Decisoes:

- 20 notas por pagina
- pagina 1 em `notes/index.html`
- pagina 2+ em `notes/page/N.html`

Criterio de saida:

- o arquivo de notas e crawlavel, estatico e navegavel por links simples

### Etapa 5: Reposicionar o `Now`

Objetivo:

- fazer `now.html` ser a porta de entrada editorial, sem virar arquivo infinito

Acoes:

1. Ajustar a geracao do bloco `AUTO:now-notes` para mostrar apenas as 12 notas mais recentes.
2. Cada nota mostrada no `Now` deve linkar para sua pagina propria em `notes/`.
3. Incluir um link claro para `notes/index.html`, com texto visivel do tipo:
   - `Ver arquivo completo de notas`
4. Manter o restante da estrutura editorial de `now.html`.
5. Nao transformar `now.html` em pagina de listagem bruta.

Criterio de saida:

- `now.html` segue vivo editorialmente e deixa de concentrar o arquivo inteiro

### Etapa 6: Integrar notas em sitemap e feed

Objetivo:

- tratar notas como conteudo de primeira classe no ecossistema do site

Acoes:

1. Atualizar `scripts/build_site_metadata.py` para incluir paginas de nota em:
   - `sitemap.xml`
   - `sitemap.txt`, se aplicavel
2. Atualizar o feed para incluir notas publicadas.
3. Se o feed atual mistura apenas blog e paginas, adaptar para aceitar notas sem quebrar itens existentes.
4. Garantir ordem cronologica correta.

Regras:

- notas com `status: draft` nao entram em sitemap nem feed
- somente paginas publicas entram no sitemap

Criterio de saida:

- notas publicadas sao descobriveis por sitemap e feed

### Etapa 7: Preparar a base de paginacao do blog

Objetivo:

- aproveitar a mudanca para deixar a arquitetura pronta para listagens longas no blog

Acoes:

1. Auditar como `blog.html` e gerado hoje.
2. Refatorar o codigo de geracao de listagens para permitir reaproveitamento entre blog e notes, sem exagerar na abstracao.
3. Preparar o blog para suportar:
   - pagina 1 em `blog.html`
   - paginas seguintes em `blog/page/N.html`, somente quando necessario
4. Se o volume atual de posts nao exigir paginas extras, deixar a infraestrutura pronta e validada mesmo assim.

Regras:

- nao reescrever o blog inteiro
- nao mover posts existentes para novas URLs

Criterio de saida:

- a arquitetura de listagem suporta notes e blog de forma consistente

### Etapa 8: Atualizar a validacao

Objetivo:

- evitar regressao estrutural e editorial

Acoes:

1. Expandir `scripts/validate_site.py` para validar:
   - paginas individuais de nota
   - canonical correto em cada nota
   - metadata minima em cada nota
   - existencia do `h1`
   - presenca da nota no sitemap
   - integridade da paginacao de notas
   - integridade da pagina `notes/index.html`
2. Garantir que o validador continue cobrindo `now.html`.
3. Garantir que rascunhos nao sejam tratados como paginas publicas.

Criterio de saida:

- falhas estruturais em notes e paginacao passam a ser detectadas automaticamente

### Etapa 9: Ajustar a CLI de notas

Objetivo:

- manter o fluxo editorial simples depois da migracao

Acoes:

1. Adaptar `scripts/note.py` para que criar/publicar uma nota:
   - gere o Markdown-fonte
   - regenere `now.html`
   - gere a pagina propria da nota
   - regenere o arquivo de notas
   - atualize sitemap/feed
   - rode validacao
2. Preservar o modo `--direct-main`.
3. O fluxo recomendado para agentes deve continuar sendo:

```bash
python3 scripts/note.py new "Titulo da nota" --body "Texto da nota" --direct-main
```

4. Nao obrigar PR.

Criterio de saida:

- uma IA consegue criar e publicar uma nota funcional com um comando simples

### Etapa 10: Atualizar a documentacao e os artefatos para agentes

Objetivo:

- deixar o novo fluxo claro para IAs futuras

Acoes:

1. Atualizar `README.md`.
2. Atualizar `AGENTS.md`.
3. Atualizar `.github/copilot-instructions.md`.
4. Atualizar `.github/skills/portfolio-notes-editorial/SKILL.md`.
5. Atualizar `.github/skills/portfolio-notes-editorial/references/note-patterns.md`.
6. Atualizar `.github/agents/note-editor.agent.md`.
7. Atualizar `.github/prompts/new-note.prompt.md`.
8. Em todos eles, deixar explicito:
   - que o ponto de entrada editorial e `now.html`
   - que a source of truth e `content/notes/*.md`
   - que a nota publicada ganha pagina propria em `notes/`
   - que o arquivo de notas e paginado
   - que o fluxo sem friccao usa `--direct-main`

Criterio de saida:

- outra IA consegue inferir o fluxo correto apenas lendo os artefatos do repositorio

### Etapa 11: Migrar as notas ja existentes

Objetivo:

- garantir que o acervo atual entre na nova arquitetura

Acoes:

1. Gerar paginas proprias para todas as notas existentes em `content/notes/`.
2. Atualizar `now.html` para apontar para as novas URLs.
3. Garantir que o arquivo de notas liste tambem as notas antigas.
4. Nao apagar as notas existentes nem mudar seu source.

Opcional, se simples:

- manter anchors estaveis em `now.html` para compatibilidade de navegacao interna

Criterio de saida:

- o acervo atual de notas funciona sem tratamento manual caso a caso

### Etapa 12: Validacao final obrigatoria

Objetivo:

- garantir que tudo ficou funcional

Acoes:

1. Rodar:

```bash
python3 scripts/build_site_metadata.py
python3 scripts/validate_site.py
```

2. Verificar manualmente pelo menos:
   - `now.html`
   - uma pagina individual de nota
   - `notes/index.html`
   - uma pagina 2 do arquivo, se existir
   - `blog.html`
3. Confirmar que:
   - links funcionam
   - metadata esta presente
   - canonical esta correto
   - header/footer nao quebraram
   - sitemap e feed refletem o novo estado

Criterio de saida:

- a validacao automatica passa
- a verificacao manual nao encontra regressao evidente

## Criterios de aceite

O trabalho so pode ser considerado concluido se tudo abaixo for verdadeiro:

- cada nota publicada tem URL propria em `notes/`
- `now.html` mostra apenas as 12 notas mais recentes
- existe arquivo paginado de notas
- notas entram em sitemap e feed
- `scripts/note.py` gera todo o ciclo completo
- `--direct-main` continua funcional
- documentacao e artefatos de agente estao alinhados
- `python3 scripts/build_site_metadata.py` passa
- `python3 scripts/validate_site.py` passa

## O que nao fazer

- nao criar uma pagina por nota em JavaScript
- nao usar infinite scroll
- nao usar `#` como URL principal da nota
- nao deixar `now.html` como unico endereco da nota
- nao criar uma arquitetura diferente para cada tipo de conteudo
- nao adicionar dependencias pesadas sem necessidade clara
- nao depender de PR para notas

## Observacoes para futuras IAs

Depois desta migracao:

- notas sao conteudo publico de primeira classe
- `now.html` e uma superficie editorial de entrada, nao o unico armazenamento publico da nota
- futuras IAs que criarem notas devem:
  - escrever em `content/notes/*.md`
  - publicar via `scripts/note.py`
  - assumir que existe pagina propria em `notes/`
- futuras IAs que mexerem em blog e notes devem preservar a consistencia da paginacao e dos metadados

