Source: https://bolivaralencastro.com.br/blog/publicando-no-linkedin-com-python-e-api.html

# Publicar no LinkedIn e no Instagram sem abrir os apps 

 Por [Bolívar Alencastro](https://bolivaralencastro.com.br/about.html) 21 Abr 2026 • Dev Tools • Automação • 7 min de leitura • [permalink](https://bolivaralencastro.com.br/blog/publicando-no-linkedin-com-python-e-api.html)  

Dois scripts Python leem o post mais recente do blog e publicam no LinkedIn e no Instagram sozinhos. A parte difícil não foi automatizar, foi decifrar o que cada API exige de verdade. 

 

Resposta rápida 

Escrevo o post uma vez no blog e dois scripts publicam nas redes: `linkedin_post.py` e `instagram_post.py` leem o HTML mais recente, resolvem imagem e legenda, e publicam via API. Nunca mais abro os apps para postar — que era exatamente o objetivo, mesmo que na primeira versão desta publicação eu tenha contado a história como se fosse sobre depurar um erro 422 do LinkedIn.  ![Ilustração editorial mostrando terminal com saída de script Python conectado a cards do LinkedIn e do Instagram](https://bolivaralencastro.com.br/assets/images/blog/publicando-no-linkedin-com-python-e-api/cover.webp) 

 

Toda vez que publico um post novo, a etapa seguinte era abrir o LinkedIn, colar o link, escolher a imagem, escrever alguma coisa e postar — e depois repetir o mesmo ritual no Instagram, com uma imagem em outro formato e uma legenda mais curta. Dez, quinze minutos que sempre pareceram desnecessários, porque toda informação para fazer isso já está no próprio blog: título, resumo, imagem de capa, data. Resolvi automatizar, e o resultado hoje são dois scripts, não um. 

Quando escrevi a primeira versão deste post, em abril, só existia `scripts/linkedin_post.py` e a história que eu tinha para contar era sobre depurar a API do LinkedIn — o que era verdade, mas incompleta: o script do Instagram já estava em construção no dia seguinte. Meio ano e algumas migrações de API depois, os dois publicam lado a lado, e o ponto real nunca foi resolver um erro específico. Foi parar de precisar abrir qualquer um dos dois apps. 

## Um comando por post, dois destinos 

Os dois scripts compartilham a mesma lógica de entrada: percorrem `blog/*.html`, leem o atributo `datetime` das tags `<time>` — a mesma fonte que alimenta o feed RSS e a listagem do blog — e extraem título, resumo e imagem de capa do post mais recente (ou de um slug específico, via `--slug`). A partir daí, cada um resolve o que a rede exige. 

## LinkedIn: OAuth, upload de imagem e dois erros que ensinaram mais 

`scripts/linkedin_post.py` faz upload da imagem de capa via `/rest/images?action=initializeUpload`, que retorna uma URL de upload e um URN de imagem, e publica via `POST /rest/posts` com o header `LinkedIn-Version: 202503`. A autenticação usa [OAuth 2.0 com Authorization Code Flow](https://learn.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow): `scripts/linkedin_auth.py` sobe um servidor local na porta 8080 como callback, captura o código de autorização, troca pelo access token e salva em disco. ![Diagrama do fluxo OAuth 2.0: browser abrindo a autorização e retornando o token para o servidor local na porta 8080](https://bolivaralencastro.com.br/assets/images/blog/publicando-no-linkedin-com-python-e-api/oauth-flow.webp) 

A primeira tentativa de publicar usou o endpoint `/v2/ugcPosts` — o padrão documentado por anos. A resposta foi um `403 Forbidden` sem mensagem útil: esse endpoint exige verificação de app de terceiros, que não se aplica a scripts pessoais. A solução foi migrar para `/rest/posts`, que funciona com o scope `w_member_social` sem verificação adicional. Com o endpoint correto, a chamada seguinte retornou um `422 Unprocessable Entity`: 

```
author value urn:li:person:********** is of type member.
Allowed URN types: urn:li:company, urn:li:member
```

 

A API sinalizava que o prefixo do URN estava errado — e, ao fazer isso, revelou o identificador correto no próprio corpo do erro. Pessoas físicas usam `urn:li:member:{id}`, não `urn:li:person:{id}`; o `id` numérico aparece no painel do LinkedIn Developer. Um detalhe de ambiente à parte: no macOS com Python 3.14+, as requisições HTTPS falham por SSL sem intervenção explícita, e a correção é instalar o [certifi](https://pypi.org/project/certifi/) e injetar o bundle de certificados com `ssl.create_default_context(cafile=certifi.where())`. Em agosto, adicionei ainda a flag `--link-card`, que publica como card de link com preview automático da URL em vez de subir a imagem como mídia solta. ![Ilustração do erro 422 da API com lupa destacando a informação útil dentro do corpo do erro — o URN correto](https://bolivaralencastro.com.br/assets/images/blog/publicando-no-linkedin-com-python-e-api/erro-422.webp) 

## Instagram: contêiner em duas etapas e regras que a API não deixa óbvias 

`scripts/instagram_post.py` publica pela Instagram Graph API, que funciona por contêiner em duas chamadas: `POST /{user_id}/media` cria o contêiner com a imagem e a legenda e devolve um `container_id`; `POST /{user_id}/media_publish` publica esse contêiner. Nada disso aceita WEBP — o formato editorial que uso no resto do site — então o script procura por `instagram.jpg` ou `card.jpg` na pasta de assets do post e serve a imagem via URL pública no `raw.githubusercontent.com`, para evitar o atraso de propagação do GitHub Pages. 

A legenda é montada à parte, porque o Instagram não renderiza links clicáveis nela: o texto vem do resumo do post, seguido de um aviso de "link na bio" e da URL com parâmetros UTM (`utm_source=instagram`, campanha pelo slug), para eu saber depois, no analytics, o que veio de onde. A autenticação trocou de fornecedor no meio do caminho: comecei publicando via `graph.facebook.com` com um token de app Facebook e migrei em julho para `graph.instagram.com` com Instagram Login direto, depois que um token do tipo IGAA passou a ser rejeitado com `OAuthException 190` no host antigo. `scripts/instagram_auth.py` cuida da troca e salva `INSTAGRAM_ACCESS_TOKEN` e `INSTAGRAM_IG_USER_ID` no `.env`. 

## O fluxo hoje 

Com os dois scripts funcionando, o ciclo de publicação ficou assim: 
 
1. Escrever o post HTML no blog 
1. `python3 scripts/build_site_metadata.py` 
1. `python3 scripts/linkedin_post.py` 
1. `python3 scripts/instagram_post.py` 
 ![Pipeline de etapas: arquivo HTML, comandos no terminal com sucesso, e posts publicados no LinkedIn e no Instagram](https://bolivaralencastro.com.br/assets/images/blog/publicando-no-linkedin-com-python-e-api/pipeline.webp) 

Ambos aceitam `--dry-run` para simular sem publicar de fato, e a saída no terminal confirma cada etapa: detecção do post, resolução da imagem, publicação, URL final. Nenhum dos dois exige que eu toque em um app de celular. 

A distância entre o que a documentação de cada rede promete e o que de fato funciona para uma conta pessoal, não verificada, é grande o bastante para fazer endpoints inteiros parecerem quebrados quando só estão desatualizados ou vetados para esse uso. Isso valeu tanto para o `403` do LinkedIn quanto para o `OAuthException 190` do Instagram. Mas o que ficou, passados os dois debugs, não foi a lista de erros — foi o hábito que mudou: escrevo uma vez, publico duas. 

 

Sobre o autor 

 ![Foto de Bolívar Alencastro](https://bolivaralencastro.com.br/assets/images/author/bolivar-alencastro.webp) 

 

### [Bolívar Alencastro](https://bolivaralencastro.com.br/about.html) 

Product Designer em São Paulo que prefere automatizar a própria presença digital a terceirizar para uma ferramenta que decide o formato, o horário e o texto por você. 
 
- [LinkedIn](https://www.linkedin.com/in/bolivaralencastro/) 
- [Instagram](https://www.instagram.com/bolivar.alencastro/) 
      

 

## Outras Publicações 

 [![Capa do post: Paramos de desenhar telas. Aí o marketing pediu uma vista explodida](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/card.webp)](https://bolivaralencastro.com.br/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida.html) 

### [Paramos de desenhar telas. Aí o marketing pediu uma vista explodida](https://bolivaralencastro.com.br/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida.html) 

Deixamos de desenhar telas e passamos a prototipar em código. Quando o marketing pediu uma vista explodida da interface, a saída foi criar o stage-viewer: uma base real de cena 3D para a IA generativa refinar, em vez de recriar do zero.  

 [![Capa do post: A segunda corda](https://bolivaralencastro.com.br/assets/images/blog/a-segunda-corda/card.webp)](https://bolivaralencastro.com.br/blog/a-segunda-corda.html) 

### [A segunda corda](https://bolivaralencastro.com.br/blog/a-segunda-corda.html) 

A linha de vida que impediu a queda de Mayk abre uma reflexão sobre trabalho, propriedade, tecnologia e as proteções que sustentam quem trabalha.  

 [![Capa do post: Há Quedas Por Vir](https://bolivaralencastro.com.br/assets/images/blog/ha-quedas-por-vir/card.webp)](https://bolivaralencastro.com.br/blog/ha-quedas-por-vir.html) 

### [Há Quedas Por Vir](https://bolivaralencastro.com.br/blog/ha-quedas-por-vir.html) 

Um relato em cinco tempos sobre Há Quedas Por Vir, de Érica Storer e Sansa: shibari, um escritório suspenso e a queda que nunca chega.
