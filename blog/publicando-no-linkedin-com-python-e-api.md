Source: https://bolivaralencastro.com.br/blog/publicando-no-linkedin-com-python-e-api.html

# Publicando no LinkedIn com Python e a REST API 

 Por [Bolívar Alencastro](https://bolivaralencastro.com.br/about.html) 21 Abr 2026 • Dev Tools • Automação • 5 min de leitura • [permalink](https://bolivaralencastro.com.br/blog/publicando-no-linkedin-com-python-e-api.html)  

Um script Python que detecta o post mais recente, faz upload da imagem e publica no LinkedIn em um comando — o URN correto apareceu no corpo de um erro 422. 

 

Resposta rápida 

Publicar no LinkedIn pela API exigiu transformar tentativa, erro 422 e documentação em um fluxo operacional. O script detecta o post mais recente, envia a imagem e publica a partir do próprio ambiente do portfolio.  ![Ilustração editorial mostrando terminal com saída de script Python conectado a um card do LinkedIn](https://bolivaralencastro.com.br/assets/images/blog/publicando-no-linkedin-com-python-e-api/cover.webp) 

 

Toda vez que publico um post novo, a etapa seguinte é abrir o LinkedIn, colar o link, escolher a imagem, escrever alguma coisa e postar. São dez minutos que sempre parecem desnecessários — não pelo esforço, mas porque toda informação para fazer isso já está no próprio blog. Então resolvi automatizar. 

O resultado é `scripts/linkedin_post.py`: um script Python que lê o post mais recente do blog, faz upload da imagem de capa para a [LinkedIn REST API](https://learn.microsoft.com/en-us/linkedin/) e publica em um único comando. A parte mais interessante do processo não foi a automação em si, mas o que apareceu ao longo do caminho. 

## O que o script faz 

O fluxo tem três etapas. Primeiro, o script detecta automaticamente o post mais recente percorrendo todos os arquivos `blog/*.html` e lendo o atributo `datetime` das tags `<time>` — a mesma fonte que alimenta o feed RSS e a listagem do blog. Segundo, faz upload da imagem `card.webp` do post via `/rest/images?action=initializeUpload`, que retorna uma URL de upload e um URN de imagem para referenciar depois. Terceiro, publica via `POST /rest/posts` com o header `LinkedIn-Version: 202503`. 

A autenticação usa [OAuth 2.0 com Authorization Code Flow](https://learn.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow). O script `scripts/linkedin_auth.py` sobe um servidor local na porta 8080 como callback, captura o código de autorização, troca pelo access token e salva em disco. O `linkedin_post.py` lê esse token e cuida do resto. ![Diagrama do fluxo OAuth 2.0: browser abrindo a autorização e retornando o token para o servidor local na porta 8080](https://bolivaralencastro.com.br/assets/images/blog/publicando-no-linkedin-com-python-e-api/oauth-flow.webp) 

## Os erros que ensinaram mais 

A primeira tentativa de publicar usou o endpoint `/v2/ugcPosts` — que era o padrão documentado por anos. A resposta foi um `403 Forbidden` sem mensagem útil. O motivo, enterrado na documentação da LinkedIn, é que esse endpoint exige verificação de app de terceiros, que não se aplica a scripts pessoais. A solução foi migrar para a nova API `/rest/posts`, que funciona com o scope `w_member_social` sem nenhuma verificação adicional. Essa diferença não está sinalizada de forma óbvia — o `403` parece um problema de credencial, não de endpoint. 

O segundo tropeço foi mais instrutivo. Com o endpoint correto, a chamada retornou um `422 Unprocessable Entity` com esta mensagem: 

```
author value urn:li:person:********** is of type member.
Allowed URN types: urn:li:company, urn:li:member
```

 

A API sinalizava que o prefixo do URN estava errado — e, ao fazer isso, revelou o identificador correto no próprio corpo do erro. Pessoas físicas usam `urn:li:member:{id}`, não `urn:li:person:{id}`. O `id` numérico aparece no painel do LinkedIn Developer. Uma vez corrigido o prefixo, a publicação funcionou. ![Ilustração do erro 422 da API com lupa destacando a informação útil dentro do corpo do erro — o URN correto](https://bolivaralencastro.com.br/assets/images/blog/publicando-no-linkedin-com-python-e-api/erro-422.webp) 

Um detalhe de ambiente: no macOS com Python 3.14+, as requisições HTTPS para a API falham por SSL sem intervenção explícita. A correção é instalar o [certifi](https://pypi.org/project/certifi/) e injetar o bundle de certificados no início do script com `ssl.create_default_context(cafile=certifi.where())`. 

## O fluxo funcionando 

Com tudo resolvido, o ciclo de publicação ficou assim: 
 
1. Escrever o post HTML no blog 
1. `python3 scripts/build_site_metadata.py` 
1. `python3 scripts/linkedin_post.py` 
 ![Pipeline de três etapas: arquivo HTML, comando no terminal com sucesso, e post publicado no LinkedIn](https://bolivaralencastro.com.br/assets/images/blog/publicando-no-linkedin-com-python-e-api/pipeline.webp) 

O script também aceita `--dry-run` para simular a publicação sem postar de fato, e `--slug <slug>` para publicar um post específico em vez do mais recente. A saída no terminal confirma cada etapa: detecção do post, upload da imagem, publicação, URL do post publicado. 

A [LinkedIn REST API](https://learn.microsoft.com/en-us/linkedin/) tem documentação razoável, mas a distância entre o que está escrito e o que funciona para apps pessoais não verificados é suficiente para fazer alguns endpoints parecerem quebrados quando não estão. A migração de `/v2/ugcPosts` para `/rest/posts` não aparece como requisito óbvio em nenhum lugar central. O erro 422 foi mais útil do que qualquer página de docs. 

 

Sobre o autor 

 ![Foto de Bolívar Alencastro](https://bolivaralencastro.com.br/assets/images/author/bolivar-alencastro.webp) 

 

### [Bolívar Alencastro](https://bolivaralencastro.com.br/about.html) 

Product Designer em São Paulo que prefere automatizar a própria presença digital a terceirizar para uma ferramenta que decide o formato, o horário e o texto por você. 
 
- [LinkedIn](https://www.linkedin.com/in/bolivaralencastro/) 
- [Instagram](https://www.instagram.com/bolivar.alencastro/) 
      

 

## Outras Publicações 

 [![Capa do post: Do excesso à execução: o custo invisível da IA dentro das empresas](https://bolivaralencastro.com.br/assets/images/blog/do-excesso-a-execucao-o-custo-invisivel-da-ia-dentro-das-empresas/card.webp)](https://bolivaralencastro.com.br/blog/do-excesso-a-execucao-o-custo-invisivel-da-ia-dentro-das-empresas.html) 

### [Do excesso à execução: o custo invisível da IA dentro das empresas](https://bolivaralencastro.com.br/blog/do-excesso-a-execucao-o-custo-invisivel-da-ia-dentro-das-empresas.html) 

No STATE, quatro perspectivas sobre finanças, arquitetura, neurociência e cultura ajudam a deslocar a conversa sobre inteligência artificial: da capacidade das ferramentas para o custo de reorganizar empresas e pessoas ao redor delas.  

 [![Capa do post: O dia seguinte](https://bolivaralencastro.com.br/assets/images/blog/o-dia-seguinte/card.webp)](https://bolivaralencastro.com.br/blog/o-dia-seguinte.html) 

### [O dia seguinte](https://bolivaralencastro.com.br/blog/o-dia-seguinte.html) 

Sobre ovos, imagem e o momento em que decidi me tornar vegano: uma cena guardada desde a pandemia, uma citação de Bataille e a manhã em que finalmente a fotografei.  

 [![Capa do post: Antes do CicloFest Rural: uma rota vivida com a Triskel Bike](https://bolivaralencastro.com.br/assets/images/blog/antes-do-ciclofest-rural/card.webp)](https://bolivaralencastro.com.br/blog/antes-do-ciclofest-rural.html) 

### [Antes do CicloFest Rural: uma rota vivida com a Triskel Bike](https://bolivaralencastro.com.br/blog/antes-do-ciclofest-rural.html) 

Em 2021, Lica nos convidou a percorrer em primeira mão uma rota que preparava para o CicloFest Rural. Entre bicicleta, fotografia e encontros em São Pedro de Alcântara, a Triskel Bike me deu uma experiência que continuo guardando com carinho.
