---
name: linkedin-publisher
description: >
  Publica posts do blog no LinkedIn via CLI usando a LinkedIn REST API.
  Use quando a tarefa envolve divulgar um post do blog no LinkedIn,
  com ou sem imagem, com controle de slug e dry run.
---

# LinkedIn Publisher Skill

Publica o último post do blog (ou um específico) no LinkedIn com uma imagem `card.webp` automaticamente.

## Pré-requisitos

- Python 3.10+
- `certifi` instalado: `pip3 install certifi`
- `.env` na raiz com as credenciais (ver seção abaixo)

## Fluxo padrão

```bash
# 1. (Primeira vez ou token expirado) Autenticar:
python3 scripts/linkedin_auth.py

# 2. Publicar o post mais recente:
python3 scripts/linkedin_post.py

# 3. Dry run (ver texto sem publicar):
python3 scripts/linkedin_post.py --dry-run

# 4. Publicar post específico:
python3 scripts/linkedin_post.py --slug nome-do-slug
```

## Configuração do `.env`

```
LINKEDIN_CLIENT_ID=<client_id>
LINKEDIN_CLIENT_SECRET=<client_secret>
LINKEDIN_REDIRECT_URI=http://localhost:8080/callback
LINKEDIN_ACCESS_TOKEN=<token_oauth>
LINKEDIN_PERSON_URN=urn:li:person:FptyQBlmzW
```

O `.env` é gitignored. O token tem validade de ~2 meses. Quando expirar, rode `linkedin_auth.py` novamente.

## Como a detecção de post funciona

- Lê todos os `blog/*.html`
- Extrai `<time datetime="...">` de cada arquivo
- Retorna o post com a data mais recente (ISO sort)

## Como a imagem funciona

- Procura `assets/images/blog/<slug>/card.webp` (ou `cover.webp`)
- Se encontrar: upload via `/rest/images?action=initializeUpload` + `PUT` binário
- Post publicado com `"content": {"media": {"id": image_urn}}`
- Se não encontrar: publica com card de artigo (link preview automático)

## API utilizada

- **Endpoint:** `POST https://api.linkedin.com/rest/posts`
- **Versão:** `LinkedIn-Version: 202503`
- **Scopes necessários:** `openid profile w_member_social`
- **Image upload:** `POST https://api.linkedin.com/rest/images?action=initializeUpload`

## Arquivos relevantes

- `scripts/linkedin_post.py` — script principal de publicação
- `scripts/linkedin_auth.py` — fluxo OAuth (salva token no `.env`)
- `.env` — credenciais (gitignored)

## Notas técnicas

- O URN do autor é `urn:li:person:FptyQBlmzW` (pessoa autenticada via OAuth)
- A API `/v2/ugcPosts` (antiga) não funciona com este app — usar `/rest/posts`
- A API `/v2/me` e `/v2/userinfo` retornam 403 para este app; o URN está fixo no `.env`
- SSL fix para Python 3.14+ no macOS: `certifi` é obrigatório
