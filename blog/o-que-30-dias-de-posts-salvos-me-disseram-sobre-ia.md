Source: https://bolivaralencastro.com.br/blog/o-que-30-dias-de-posts-salvos-me-disseram-sobre-ia.html

# O que 30 dias de posts salvos me disseram sobre IA 

 Por [Bolívar Alencastro](https://bolivaralencastro.com.br/about.html) 22 Abr 2026 • AI Workflow • Curadoria • 6 min de leitura • [permalink](https://bolivaralencastro.com.br/blog/o-que-30-dias-de-posts-salvos-me-disseram-sobre-ia.html)  

Salvei posts no LinkedIn por 30 dias. O acúmulo não virou hype — virou padrão. Cinco temas que apareceram com consistência: custo de uso, agentes em produção, MCP, voz como interface, e o Brasil na posição 61 de 116. 

 

Resposta rápida 

Trinta dias de posts salvos no LinkedIn revelaram padrões mais úteis que hype: custo de uso, agentes em produção, MCP, voz como interface e posição do Brasil. A curadoria transforma acúmulo em leitura de sinais.  ![Feed do LinkedIn visto como painel de sinais, com posts agrupados em categorias temáticas sobre IA](https://bolivaralencastro.com.br/assets/images/blog/o-que-30-dias-de-posts-salvos-me-disseram-sobre-ia/cover.webp) 

 

Tenho o hábito de salvar posts no [LinkedIn](https://www.linkedin.com/) quando alguma coisa parece densa o suficiente para merecer atenção depois. Não é curadoria intencional — é mais um reflexo. Salvo, fecho a aba, e raramente volto. 

Dessa vez voltei. Depois de 30 dias, olhei para o conjunto e tentei entender o que o acúmulo dizia. Não post por post, mas como padrão. Classifiquei os itens por tema com ajuda de um modelo de linguagem e li os agrupamentos. O que apareceu não foi hype — foi infraestrutura em formação, com os custos e as arestas que acompanham qualquer infraestrutura nova. 

Cinco temas se repetiram com frequência suficiente para merecer descrição. 

## 1. O custo de usar mal as ferramentas 

Um dos posts mais circulados no período foi o de [Ruben Hassid](https://www.linkedin.com/in/rubenhassid/), que começa com um diagnóstico direto: *"You're paying $20/month for Claude. But you're burning through it by 2 pm."* A razão não é o plano — é o hábito. Cada mensagem de follow-up relê a conversa inteira. A mensagem 30 custa 31 vezes mais do que a mensagem 1. O mesmo PDF vai para cinco chats diferentes. O modelo mais poderoso é acionado para revisar gramática. 

[Alena Panshina](https://www.linkedin.com/in/alena-panshina/) aprofundou o mesmo problema pelo lado técnico: 9.900 desenvolvedores votaram em uma técnica de [Claude Code](https://www.anthropic.com/claude-code) que corta custos em até 75%, que consiste basicamente em escrever prompts sem formatação elaborada — o que ela chamou de "escrever como um homem das cavernas". O ponto não é irônico. É que o modelo não precisa de apresentação para funcionar. Contexto bem estruturado importa mais do que estilo. 

Esses dois posts juntos indicam algo além da economia de tokens: ferramentas de IA já têm usuários suficientes para gerar um mercado secundário inteiro de dicas de uso eficiente. Isso é um sinal de maturidade, ainda que seja maturidade de consumo, não de domínio. 

## 2. Agentes saíram do slide de apresentação 

[Shubham Saboo](https://www.linkedin.com/in/shubhamsaboo/) publicou dois posts que mostram a extensão do que está se chamando de agente hoje. No primeiro, um agente de IA avaliou mais de 740 vagas de emprego, gerou 100 currículos adaptados por ATS e resultou em uma contratação para uma posição de Head of Applied AI. O repositório foi aberto depois. No segundo, agentes do [OpenClaw](https://openclaw.com/) entram em chamadas no [Google Meet](https://meet.google.com/) com rosto, voz clonada e memória do que foi trabalhado anteriormente. 

No Brasil, [Arthur Farache](https://www.linkedin.com/in/arthurfarache/) contou como começou tentando automatizar a própria rotina e terminou configurando múltiplos agentes no OpenClaw com arquivos de `SOUL.md` e `SKILLS`. A observação dele é útil: a qualidade do agente depende diretamente da qualidade da descrição que você escreve para ele. Não é diferente de escrever uma boa instrução para qualquer sistema. 

O time da [CyberAgent](https://cyberagent.ai/), criadora da plataforma de blog [Ameba](https://www.ameba.jp/), documentou no [Chrome for Developers](https://developer.chrome.com/) a transição de detecção manual de erros em tempo de execução para um workflow automatizado com o Chrome DevTools MCP server. O resultado: cobertura de auditoria em 100% dos 236 componentes do design system [Spindle](https://github.com/openameba/spindle), o que antes levava dias de trabalho manual passou a ser feito em uma hora, com o agente identificando o erro, aplicando a correção e verificando o resultado em loop fechado. Isso é agente em produção. 

## 3. MCP: um protocolo que ainda confunde, mas já funciona ![Diagrama esquemático mostrando MCP servers conectando agentes de IA a bancos de dados e ferramentas externas](https://bolivaralencastro.com.br/assets/images/blog/o-que-30-dias-de-posts-salvos-me-disseram-sobre-ia/mcp-infraestrutura-inline.webp) 

O [Model Context Protocol](https://modelcontextprotocol.io/) apareceu em pelo menos quatro posts distintos no período. [Jaco Silvis](https://www.linkedin.com/in/jaco-silvis/) descreveu o lançamento de MCP servers gerenciados pelo [Google Cloud](https://cloud.google.com/) para [BigQuery](https://cloud.google.com/bigquery), [Cloud SQL](https://cloud.google.com/sql) e [Spanner](https://cloud.google.com/spanner): uma interface padronizada que permite a agentes de IA explorar esquemas e executar queries sem precisar de integrações individuais por API. A justificativa dele para CTOs era segurança e contenção de sprawl arquitetural. 

[Femke Plantinga](https://www.linkedin.com/in/femkeplantinga/) tratou de uma confusão frequente: MCP e Agent Skills não são alternativas — resolvem problemas diferentes dentro do mesmo ecossistema. MCP é um gateway padronizado para dados e ferramentas externas. Skills são capacidades reutilizáveis dentro de um agente. A pergunta certa não é escolher um, mas entender onde cada um opera. 

Num registro mais prático, uma publicação anônima no feed descreveu o **OpenRAG**, construído sobre [Langflow](https://www.langflow.org/), [Docling](https://github.com/DS4SD/docling) e [OpenSearch](https://opensearch.org/): um único comando (`uvx openrag`) para subir ingestão de documentos, busca semântica e chat com IA, sem integrações improvisadas. Aberto, funcional, sem gambiarra. 

O que esses posts têm em comum é que o MCP deixou de ser conceito e passou a ter implementações concretas em escala — Google Cloud, design systems, RAG em produção. A confusão em torno do protocolo ainda existe, mas o protocolo já existe antes dela. 

## 4. IA como viabilizador de criação 

[Meng To](https://www.linkedin.com/in/mengto/), da [Design+Code](https://designcode.io/), publicou sobre uma ferramenta que gera interfaces com um design system inteiramente expresso como prompts — pares de fontes, sistema de cores, espaçamento, sets de ícones, botões, exemplos de Three.js. Tudo copiável. A proposição é que o design system como prompt torna as explorações com [Gemini](https://gemini.google.com/) mais precisas porque o contexto está estruturado de forma que o modelo consegue respeitar. 

[Gábor Pribék](https://www.linkedin.com/in/gabor-pribek/), da equipe de product design da [Spline](https://spline.design/), foi mais direto sobre o que a IA muda no trabalho criativo: não é o one-shot com o prompt perfeito, é o nível de detalhe que se consegue incluir depois. WebGPU, screen space reflections, depth of field, ambient occlusion, áudio espacial procedural — ele adicionou cada um desses elementos iterativamente. O modelo não substituiu o julgamento de craft; liberou tempo para exercê-lo. 

[Rodrigo Rodrigues](https://www.linkedin.com/in/rodrigo-rodrigues-ux/) resumiu a mudança de forma mais econômica: *"Se eu dependesse do caminho tradicional, esse projeto não existiria. Mas com a inteligência artificial o jogo mudou. Um projeto que custaria milhares. Com IA, custou clareza, e execução."* A frase tem o mérito de nomear o custo real: clareza. A IA não elimina a necessidade de saber o que se quer fazer. 

## 5. Voz voltou — e desta vez com infraestrutura ![Interface de voz minimalista com ondas sonoras e indicadores de latência baixa, design editorial escuro](https://bolivaralencastro.com.br/assets/images/blog/o-que-30-dias-de-posts-salvos-me-disseram-sobre-ia/voz-interface-inline.webp) 

[Deedy Das](https://www.linkedin.com/in/deedydas/), da [Menlo Ventures](https://menlovc.com/), escreveu sobre o [Wispr Flow](https://wispr.flow/): uma ferramenta de ditado que atinge uma taxa de 85% de zero edições necessárias. Voz é aproximadamente três vezes mais rápida do que digitação em mobile e desktop. O detalhe que ele menciona — um engenheiro que conectou um pedal de foot switch para acionar o Wispr sem interromper o fluxo de trabalho — ilustra bem o que acontece quando a precisão chega ao ponto em que as pessoas começam a integrar a ferramenta ao ambiente físico. 

[Oliver Molander](https://www.linkedin.com/in/olivermolander/) compartilhou uma atualização da [ElevenLabs](https://elevenlabs.io/) com a afirmação direta de que seus agentes de voz estão passando no Teste de Turing. O modelo conversacional v3 com ultra-baixa latência e controle fino de expressividade é o que sustenta essa afirmação. Feito na Europa. 

Voz como interface de produtividade não é ideia nova. O que mudou é que a cadeia — latência, precisão, naturalidade — ficou funcional o suficiente para uso diário sem fricção de correção constante. 

## Uma nota sobre o Brasil 

[Fabiano Fabricio](https://www.linkedin.com/in/fabianofabricio/) referenciou o [Anthropic Economic Index](https://www.anthropic.com/economic-index), publicado em março de 2026: uma pesquisa com milhões de conversas reais mapeando o uso de IA por profissão em 116 países. O Brasil está na posição 61, com índice de uso de 0,79x — 21% abaixo do esperado para a população ativa. Quando usa, os padrões de uso se concentram em tarefas operacionais e de escrita, não em automação ou raciocínio. 

Não é um dado surpreendente, mas é um dado concreto. E dados concretos são mais úteis do que as afirmações genéricas de adoção acelerada que circulam em paralelo. 

## O que o conjunto diz 

Nenhum desses posts, isolado, diz muita coisa. O padrão aparece quando se olha para os 30 dias juntos: o debate sobre IA no LinkedIn está menos centrado em capacidades do modelo e mais centrado em como operar com o que já existe. Custo de uso, arquitetura de agentes, protocolo de integração, interface de voz — são conversas de quem está usando, não de quem está esperando para ver. 

Há uma exceção que vale nomear. [Cezar Taurion](https://www.linkedin.com/in/cezar-taurion/) escreveu sobre o **Moltbook** — apresentado como uma "rede social para inteligências artificiais" onde agentes interagiriam de forma emergente e autônoma. Sua crítica foi precisa: *"Grande parte das alegações associadas ao Moltbook confunde conceitos fundamentais. LLMs não possuem agência no sentido forte do termo."* A distância entre o que é descrito tecnicamente e o que é vendido narrativamente ainda existe. Saber distinguir os dois continua sendo o trabalho. 

 

Sobre o autor 

 ![Foto de Bolívar Alencastro](https://bolivaralencastro.com.br/assets/images/author/bolivar-alencastro.webp) 

 

### [Bolívar Alencastro](https://bolivaralencastro.com.br/about.html) 

Product Designer em São Paulo que salva posts para não perder o fio e, quando volta para ler, tenta separar infraestrutura de narrativa.      

 

## Outras Publicações 

 [![Capa do post: A camerazinha de R$ 100 e a imagem suficiente](https://bolivaralencastro.com.br/assets/images/blog/a-camerazinha-de-100-reais-e-a-imagem-suficiente/card.webp)](https://bolivaralencastro.com.br/blog/a-camerazinha-de-100-reais-e-a-imagem-suficiente.html) 

### [A camerazinha de R$ 100 e a imagem suficiente](https://bolivaralencastro.com.br/blog/a-camerazinha-de-100-reais-e-a-imagem-suficiente.html) 

Uma câmera de até R$ 100, fotos de 2 MP e vídeo Full HD: um pequeno objeto que mostra o quanto a fabricação de imagens se tornou acessível.  

 [![Capa do post: O sacrilégio necessário](https://bolivaralencastro.com.br/assets/images/blog/o-sacrilegio-necessario/card.webp)](https://bolivaralencastro.com.br/blog/o-sacrilegio-necessario.html) 

### [O sacrilégio necessário](https://bolivaralencastro.com.br/blog/o-sacrilegio-necessario.html) 

Da sistematização da dança de salão no Brasil aos anos discutindo papéis de gênero na Kirinus Escola de Dança: um ensaio sobre por que inventar um passo novo nunca foi sacrilégio, amarrado a Foli, Victor Wooten, Erin McKean e Tarja Branca.  

 [![Capa do post: Tudo o que acontece quando fechamos os olhos](https://bolivaralencastro.com.br/assets/images/blog/tudo-o-que-acontece-quando-fechamos-os-olhos/card.webp)](https://bolivaralencastro.com.br/blog/tudo-o-que-acontece-quando-fechamos-os-olhos.html) 

### [Tudo o que acontece quando fechamos os olhos](https://bolivaralencastro.com.br/blog/tudo-o-que-acontece-quando-fechamos-os-olhos.html) 

Uma mariposa desaparece num banheiro interno. Entre o corpo seco atrás dos vasos, um sonho com cupins, uma mensagem para o pai e séculos de folclore sobre mariposas, um ensaio sobre o que a gente faz com o que não viu.
