Source: https://bolivaralencastro.com.br/blog/agent-speedrun-bedrock-agentcore-e-o-que-ficou-do-workshop-no-cubo.html

# No Cubo, o Agent Speedrun expôs a infraestrutura por trás de um agente utilizável 

 Por [Bolívar Alencastro](https://bolivaralencastro.com.br/about.html) 18 Abr 2026 • AI Workflow • Agentes • 5 min de leitura • [permalink](https://bolivaralencastro.com.br/blog/agent-speedrun-bedrock-agentcore-e-o-que-ficou-do-workshop-no-cubo.html)  

No Cubo Itaú, o Agent Speedrun expôs memória, guardrails, runtime e o tipo de estrutura que sustenta um agente quando a demo acaba. 

 

Resposta rápida 

Um agente utilizável não nasce da tela de chat; depende de memória, runtime, guardrails, permissões e integração com ferramentas reais. O workshop no Cubo deixou visível que a infraestrutura por trás da demo é onde a experiência começa a ficar séria.  ![Arte editorial do post sobre o workshop Agent Speedrun no Cubo](https://bolivaralencastro.com.br/assets/images/blog/agent-speedrun-bedrock-agentcore-e-o-que-ficou-do-workshop-no-cubo/cover.webp) 

 

Na sexta-feira, 17 de abril de 2026, participei do **Agent Speedrun: de horas para minutos**, no [Cubo Itaú](https://www.linkedin.com/company/cubo-network/), em São Paulo. O encontro foi organizado por [**Eduardo “Dug” Hilpert**](https://www.linkedin.com/in/dug-hilpert/) e conduzido por [**Vitor Guimarães**](https://www.linkedin.com/in/vitorguimap) e [**Lucas Nunes**](https://www.linkedin.com/in/lucnun/), da [**DNX Brasil**](https://www.linkedin.com/company/dnxbrasil). A promessa do título era velocidade. O ponto mais interessante, porém, apareceu em outro lugar: na infraestrutura que torna um agente utilizável fora da demo. ![Três registros do workshop Agent Speedrun no Cubo, com participantes, projeção e ambiente do encontro](https://bolivaralencastro.com.br/assets/images/blog/agent-speedrun-bedrock-agentcore-e-o-que-ficou-do-workshop-no-cubo/agent-speedrun-bedrock-agentcore-cubo-galeria-01.webp) 

Ao longo do workshop, a stack da [Amazon Bedrock](https://aws.amazon.com/bedrock/) foi apresentada menos como vitrine de modelos e mais como um arranjo operacional para agentes: ferramentas, memória, políticas, runtime, guardrails e observabilidade. A intuição geral era simples. O que faz um agente sair do campo da curiosidade e entrar no da utilidade não é apenas a LLM; é o conjunto de restrições e capacidades ao redor dela. 

## Dois speedruns, uma tese 

Na prática, isso apareceu em dois labs do workshop [Create an Agent](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/en-US/workshop/20-create-an-agent). O ritmo de speedrun não vinha de escrever um agente do zero em poucas horas. Os scripts já estavam preparados. O que fizemos foi percorrer esses blocos, executar etapas e observar os resultados. No **Lab 01**, isso significou acompanhar um agente de suporte ao cliente com *custom tools*, busca web, base de conhecimento e um prompt de sistema suficientemente organizado para coordenar essas peças. No **Lab 02**, ver esse mesmo agente ganhar [AgentCore](https://aws.amazon.com/bedrock/agentcore/) Memory: memória de curto prazo, memória de longo prazo e recuperação semântica de interações anteriores. ![Composição com três cenas do workshop mostrando a plateia, a apresentação e o espaço no Cubo Itaú](https://bolivaralencastro.com.br/assets/images/blog/agent-speedrun-bedrock-agentcore-e-o-que-ficou-do-workshop-no-cubo/agent-speedrun-bedrock-agentcore-cubo-galeria-02.webp) 

Essa sequência foi didática porque deslocou o problema. A pergunta deixou de ser “como fazer a IA responder?” e passou a ser “como fazer esse agente lembrar, agir e operar com alguma confiabilidade?”. O speedrun estava no modo de aprender, não no ato de programar. Ainda assim, a estrutura apresentada ali permite uma inferência importante: quando memória, runtime, identidade, guardrails, observabilidade e integração com *tools* já aparecem como fundação, a construção de agentes tende de fato a se acelerar. 

## O que apareceu com mais clareza 

O workshop insistiu em alguns pontos que me pareceram mais importantes do que o discurso usual sobre “IA mais poderosa”. Um agente útil precisa de **memória** para não recomeçar do zero, de **tools** para sair da superfície do texto, de **políticas e identidade** para não acessar tudo o que pode, e de **guardrails** para não se desviar do escopo quando encontra inputs ambíguos ou maliciosos. Em outras palavras: precisa de arcabouço. 

Esse ponto ficou ainda mais nítido nos exemplos de atendimento e nos alertas sobre *prompt attack*, exposição indevida de dados e risco reputacional. A mensagem era quase anti-hype: antes de pensar no brilho da interface, vale pensar em contenção, rastreabilidade e custo. Talvez seja justamente aí que comece uma engenharia de agentes mais séria. ![Sequência de três imagens do evento com slides, participantes e detalhes da dinâmica do workshop](https://bolivaralencastro.com.br/assets/images/blog/agent-speedrun-bedrock-agentcore-e-o-que-ficou-do-workshop-no-cubo/agent-speedrun-bedrock-agentcore-cubo-galeria-03.webp) 

## Kiro entrou como sintoma de uma mudança maior 

Foi também nesse contexto que achei interessante conhecer o [Kiro](https://kiro.dev/), a partir do compartilhamento do Vitor. O que chamou atenção não foi apenas a ideia de um fork do VS Code com IA. Foi o fato de ele aparecer como parte de uma mesma família de ferramentas que tentam organizar melhor a relação entre modelo, contexto, ferramentas, memória e fluxo de execução. ![Montagem final com três registros do workshop Agent Speedrun no Cubo, incluindo tela, público e ambiente](https://bolivaralencastro.com.br/assets/images/blog/agent-speedrun-bedrock-agentcore-e-o-que-ficou-do-workshop-no-cubo/agent-speedrun-bedrock-agentcore-cubo-galeria-04.webp) 

Saí do Cubo com uma impressão parecida à que tive em outros encontros recentes sobre IA: o centro de gravidade está mudando. Menos fascínio por um chat “que responde tudo”, mais interesse por ambientes e arquiteturas que disciplinam como essa resposta é produzida. Se essa hipótese estiver correta, o próximo diferencial competitivo não será só o modelo. Será o modo como cada stack monta o seu próprio *harness*. ![Autorretrato no elevador após o workshop Agent Speedrun no Cubo Itaú](https://bolivaralencastro.com.br/assets/images/blog/agent-speedrun-bedrock-agentcore-e-o-que-ficou-do-workshop-no-cubo/agent-speedrun-bedrock-agentcore-cubo-workshop-photo.webp) 

 

Sobre o autor 

 ![Foto de Bolívar Alencastro](https://bolivaralencastro.com.br/assets/images/author/bolivar-alencastro.webp) 

 

### [Bolívar Alencastro](https://bolivaralencastro.com.br/about.html) 

Product Designer em São Paulo, escrevendo sobre produto, interfaces e, cada vez mais, sobre o tipo de estrutura que faz agentes parecerem menos truque de palco e mais software de verdade. 
 
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
