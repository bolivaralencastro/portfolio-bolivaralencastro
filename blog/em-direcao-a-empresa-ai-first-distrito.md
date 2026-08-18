Source: https://bolivaralencastro.com.br/blog/em-direcao-a-empresa-ai-first-distrito.html

# Em direção à empresa AI First: Lições do Notion, Fhinck e Gabriel no Distrito 

 Por [Bolívar Alencastro](https://bolivaralencastro.com.br/about.html) 30 Abr 2026 • Engenharia • IA • 7 min de leitura • [permalink](https://bolivaralencastro.com.br/blog/em-direcao-a-empresa-ai-first-distrito.html)  

O que significa ser uma empresa AI First? No Gen AI Lab do Distrito, a resposta envolveu construir segundos cérebros para LLMs e reescrever a Lei de Conway. 

 

Resposta rápida 

Ser AI First exige mais do que adotar chatbots: envolve memória, arquitetura, processos e novas formas de organizar trabalho. No Gen AI Lab do Distrito, Notion, Fhinck e Gabriel ajudaram a mostrar essa mudança por camadas concretas.  ![Cartaz de divulgação do evento Gen AI Lab Meetup no Distrito com fotos de Arthur Rozenblit e Vitor Finger](https://bolivaralencastro.com.br/assets/images/blog/em-direcao-a-empresa-ai-first-distrito/cover.webp?v=2) 

 

A transição para modelos baseados em inteligência artificial costuma ser narrada como a adoção de uma nova ferramenta. Você mantém o fluxo atual e adiciona um atalho. No [**Distrito**](https://distrito.me/), em 29 de abril, durante um encontro focado no impacto da IA na gestão e na engenharia, a tônica foi inversa: a inteligência artificial exige desmontar a estrutura original. 

O evento fez parte do [**Gen AI Lab**](https://materiais.distrito.me/ai-lab), um laboratório e hub de inovação criado pelo Distrito para conectar startups nativas em IA, grandes corporações e provedores de infraestrutura (como Notion, Oracle, AWS e Microsoft). O objetivo do programa é justamente tirar a inteligência artificial do estágio de testes isolados e integrá-la ao centro das operações de negócios. 

As apresentações de [**Arthur Rozenblit**](https://www.linkedin.com/in/arthur-rozenblit/) ([Notion](https://www.notion.so/)), [**Paulo Castello**](https://www.linkedin.com/in/paulocastello/) ([Fhinck](https://www.fhinck.com/)) e [**Vitor Finger**](https://www.linkedin.com/in/vitorfinger/) ([Gabriel](https://gabriel.com.br/)) mapearam diferentes estágios de uma mesma mudança estrutural. Eles não falaram sobre como fazer o mesmo trabalho com mais velocidade, e sim sobre como a natureza do trabalho se reconfigura quando a máquina deixa de ser apenas uma interface e passa a ser um agente. ![Composição com três imagens dos registros fotográficos do evento AI First no Distrito](https://bolivaralencastro.com.br/assets/images/blog/em-direcao-a-empresa-ai-first-distrito/distrito-galeria-01.webp) 

 

 

## O Contexto como Infraestrutura 

Como [já havia ficado claro quando discutimos o GitHub Copilot](https://bolivaralencastro.com.br/blog/github-copilot-contexto-e-o-que-ficou-do-workshop-na-fiap.html), para que modelos de linguagem funcionem além de sua base de treinamento estática, eles precisam de contexto atualizado e legível. A limitação imediata de plugar o ChatGPT em um Google Drive é a natureza dos arquivos: apresentações e planilhas exigem interpretação de layout antes da extração de dados. O conhecimento fica preso no formato. 

No evento, a adoção do Notion foi descrita não como um sistema de organização visual para humanos, mas como um banco de dados estruturado em texto desenhado para ser consumido por APIs. O conceito de “segundo cérebro”, que antes servia para aliviar a carga cognitiva pessoal, escala para a infraestrutura da empresa. Quando as informações estão nativamente em *markdown* ou blocos estruturados, os agentes de IA ganham a capacidade de acessar o contexto histórico e operacional sem fricção, tornando-se precisos.  

 

Não tem como você construir um segundo cérebro só com um hard drive e uma IA. Você precisa de um lugar para armazenar conhecimento em formato de texto. Gustavo Araújo, Distrito   

 

 

## APIs Acima de Interfaces 

A Fhinck tomou a decisão radical de operar como uma empresa *AI First* há três anos, quando as capacidades dos modelos ainda geravam ceticismo. Paulo Castello — que subiu ao palco usando seus discretos [smart glasses da Even Realities](https://www.evenrealities.com/smart-glasses/selection), rendendo piadas de que estaria “colando” durante a apresentação — descreveu o desgaste inicial dessa escolha: metade da equipe saiu por rejeitar a premissa de que agentes autônomos assumiriam o papel central no desenvolvimento e na execução de processos. 

A consequência imediata de colocar a máquina para executar fluxos no [n8n](https://bolivaralencastro.com.br/blog/oracle-n8n-vercel-elevenlabs-e-a-stack-ai-first-no-cubo.html) foi a obsolescência da interface gráfica. Ferramentas consolidadas como o Jira foram substituídas porque, embora tivessem uma interface familiar para humanos, ofereciam integrações ineficientes para agentes. A nova métrica de avaliação de software corporativo passou a ser a qualidade de sua API e sua aderência ao padrão MCP (Model Context Protocol). 

A Fhinck hoje opera com o Notion como sistema operacional e repositório central, onde os agentes leem o que são, para quem trabalham e o que devem executar. Há até mesmo um *Agent Builder*: uma inteligência artificial designada apenas para gerenciar, aprovar, cobrar e supervisionar as outras dezenas de agentes que operam simultaneamente no desenvolvimento de software.  

 

Toda escolha de sistema dentro da empresa não vai mais ser pela interface bonitinha. Os sistemas precisam ser API First. Paulo Castello, Fhinck   ![Composição com três imagens das apresentações sobre a integração de agentes e ferramentas corporativas](https://bolivaralencastro.com.br/assets/images/blog/em-direcao-a-empresa-ai-first-distrito/distrito-galeria-02.webp) 

 

 

## A Nova Lei de Conway 

Na Gabriel, a transição exigiu renegociar o pacto de trabalho das áreas de tecnologia. Vitor Finger detalhou como a velocidade imposta pelos novos fluxos quebrou premissas fundamentais da engenharia tradicional. Se o custo e o tempo para gerar código caem drasticamente, a prática de preservar e evoluir sistemas legados dá lugar à disposição de descartar e reescrever código sem apego. 

A mudança estrutural atingiu o modelo de gestão. A divisão clássica entre Produto (o que construir) e Engenharia (como construir) perde sentido quando a execução técnica se torna rápida e autônoma. A Gabriel unificou a liderança dessas frentes. O gargalo deixou de ser a capacidade de codificar e passou a ser a capacidade de fornecer contexto correto e validar o resultado das máquinas. 

Para organizar essa validação, a Gabriel passou a usar agentes para criticar o planejamento. Antes de um plano chegar à gestão, um robô emula a perspectiva do CEO exigindo retorno financeiro, outro emula o CPO focado no cliente e um terceiro atua como CTO alertando sobre escalabilidade. Essa fricção artificial garante que o humano responsável entregue propostas já estressadas sob múltiplos pontos de vista, acelerando a aprovação final.  

 

A estrutura definida da organização define como o software é feito. Dependendo do que eu quero fazer, eu tenho que mexer nas estruturas. Vitor Finger, Gabriel   

## A Máquina como Treinadora 

Nem tudo pode ser executado por agentes, especialmente no contexto sensível da segurança pública operado pela central 24 horas da Gabriel. Pessoas ainda precisam atender a chamados críticos. Mas o processo de treinar esses humanos foi invertido: em vez de ler manuais, os operadores praticam com bots que simulam usuários desesperados ou síndicos resistentes à tecnologia. 

O robô atua como um supervisor incansável, avaliando o tom de voz e a precisão das informações passadas pelo humano em treinamento, corrigindo desvios com base no contexto unificado armazenado no Notion. A máquina potencializa a eficiência humana antes de assumir o processo inteiro. ![Composição com três imagens do encerramento do encontro AI First e adoção de agentes autônomos](https://bolivaralencastro.com.br/assets/images/blog/em-direcao-a-empresa-ai-first-distrito/distrito-galeria-03.webp) 

O que ficou claro no Distrito é que a adoção da inteligência artificial não é uma camada superficial. Ela exige aceitar mais quebras no ambiente de produção, abraçar a entrega contínua de protótipos e admitir que os sistemas que escolhemos amanhã precisam agradar muito mais aos agentes que os integram do que aos olhos de quem os contratou. 

 

Sobre o autor 

 ![Foto de Bolívar Alencastro](https://bolivaralencastro.com.br/assets/images/author/bolivar-alencastro.webp) 

 

### [Bolívar Alencastro](https://bolivaralencastro.com.br/about.html) 

Product Designer em São Paulo. Acostumado a desenhar interfaces para pessoas, mas cada vez mais intrigado com a ideia de projetar sistemas cujo principal usuário é um agente autônomo. 
 
- [LinkedIn](https://www.linkedin.com/in/bolivaralencastro/) 
- [Instagram](https://www.instagram.com/bolivar.alencastro/) 
      

 

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
