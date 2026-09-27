Source: https://bolivaralencastro.com.br/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida.html

# Paramos de desenhar telas. Aí o marketing pediu uma vista explodida 

 Por [Bolívar Alencastro](https://bolivaralencastro.com.br/about.html) 26 Set 2026 • Design de produto • IA generativa • 14 min de leitura • [permalink](https://bolivaralencastro.com.br/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida.html)  

Deixamos de desenhar telas e passamos a prototipar em código. Quando o marketing pediu uma vista explodida da interface, a saída foi criar o stage-viewer: uma base real de cena 3D para a IA generativa refinar, em vez de recriar do zero. 

 

Resposta rápida 

IA generativa de imagem funciona melhor como refinadora do que como autora. Dando a ela uma base real (uma cena 3D com a interface do próprio protótipo, na perspectiva certa) o modelo passa a cuidar só de material, luz e ambiente, sem reinventar a tela.  ![Notebook aberto sobre rochas escuras e úmidas, com névoa roxa e montanhas ao fundo, exibindo uma tela de aprendizagem com banner e cards de trilhas.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/cover.webp) 

 

Na [Keeps](https://keeps.com.br/), deixamos de desenhar telas. Hoje o protótipo é código, e a área de Product Design trabalha direto nele, um pouco na mesma linha do que descrevi ao [adotar a lógica da IndieWeb no meu próprio portfólio](https://bolivaralencastro.com.br/blog/por-que-adotei-a-logica-da-indieweb-no-meu-portfolio.html): menos camada intermediária entre a decisão e o artefato publicado. Foi uma decisão boa, e eu não voltaria atrás. Mas ela cobrou um preço que só apareceu quando alguém do marketing precisou de uma imagem. 

## Uma decisão tomada na era da IA generativa 

Essa mudança não veio de um dia para o outro, e não veio antes da IA. Comecei quando surgiram o [Lovable](https://lovable.dev/), o [v0](https://v0.app/) e o [Bolt](https://bolt.new/) (e outras que já nem existem mais), gerando telas e fluxos direto em código. Fixei por um tempo no [AI Studio](https://aistudio.google.com/), do Google, que oferecia entregas mais consistentes. Com o avanço dos LLMs especializados em código, passei a usá-los na linha de comando e comecei a desenvolver as nossas próprias ferramentas. 

[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/claude-color.svg)Claude](https://claude.ai/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/anthropic.svg)Anthropic](https://www.anthropic.com/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/openai.svg)OpenAI](https://openai.com/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/antigravity-color.svg)Antigravity](https://antigravity.google/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/gemini-color.svg)Gemini](https://gemini.google.com/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/deepmind.svg)DeepMind](https://deepmind.google/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/metaai-color.svg)Meta AI](https://www.meta.ai/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/codex-color.svg)Codex](https://openai.com/codex/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/grok.svg)Grok](https://grok.com/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/mistral-color.svg)Mistral](https://mistral.ai/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/huggingface-color.svg)Hugging Face](https://huggingface.co/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/perplexity-color.svg)Perplexity](https://www.perplexity.ai/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/notebooklm.svg)NotebookLM](https://notebook.google/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/langchain.png)LangChain](https://www.langchain.com/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/ollama.svg)Ollama](https://ollama.com/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/openclaw.svg)OpenClaw](https://openclaw.ai/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/opencode.svg)OpenCode](https://opencode.ai/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/kiro.svg)Kiro](https://kiro.dev/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/n8n-color.svg)n8n](https://n8n.io/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/make.svg)Make](https://www.make.com/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/qwen-color.svg)Qwen](https://qwen.ai/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/deepseek-color.svg)DeepSeek](https://www.deepseek.com/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/minimax-color.svg)MiniMax](https://www.minimax.io/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/zai.svg)GLM](https://z.ai/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/lovable-color.svg)Lovable](https://lovable.dev/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/cursor.svg)Cursor](https://cursor.com/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/jules.svg)Jules](https://jules.google/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/firebase.png)Firebase](https://firebase.google.com/?hl=pt)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/colab-color.svg)Colab](https://colab.research.google.com/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/figma-color.svg)Figma](https://www.figma.com/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/supabase.svg)Supabase](https://supabase.com/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/vercel.svg)Vercel](https://vercel.com/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/langflow.png)Langflow](https://www.langflow.org/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/openrouter.svg)OpenRouter](https://openrouter.ai/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/luma-color.svg)Luma](https://lumalabs.ai/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/spline.png)Spline](https://spline.design/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/sana.svg)Sana](https://sanalabs.com/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/kimi-color.svg)Kimi](https://www.kimi.com/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/bolt.svg)Bolt](https://bolt.new/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/bfl.svg)BFL](https://bfl.ai/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/copilot-color.svg)Copilot](https://copilot.microsoft.com/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/aistudio.svg)AI Studio](https://aistudio.google.com/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/v0.svg)v0](https://v0.app/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/elevenlabs.svg)ElevenLabs](https://elevenlabs.io/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/suno.png)Suno](https://suno.com/pt-br)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/wisprflow.png)Wispr Flow](https://wisprflow.ai/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/heygen.png)HeyGen](https://www.heygen.com/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/midjourney.svg)Midjourney](https://www.midjourney.com/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/krea.svg)Krea](https://www.krea.ai/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/magnific.svg)Magnific](https://www.magnific.com/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/replit-color.svg)Replit](https://replit.com/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/adobefirefly.svg)Adobe Firefly](https://firefly.adobe.com/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/manus.svg)Manus](https://manus.im/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/kling-color.svg)Kling](https://klingai.com/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/capcut.svg)CapCut](https://www.capcut.com/pt-br/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/dreamina.png)Dreamina](https://dreamina.capcut.com/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/higgsfield.png)Higgsfield](https://higgsfield.ai/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/runway.svg)Runway](https://runwayml.com/)[![](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/logos/bytedance-color.svg)ByteDance](https://www.bytedance.com/)

Modelos e ferramentas que explorei desde que foram aparecendo no mercado. 

Uma dessas ferramentas é a Central de Homologação, um painel que vive dentro do próprio protótipo. Ela permite navegar rapidamente entre as diferentes áreas, verificar casos de borda (corner e edge cases), popular o protótipo com dados mockados e abrir issues de correção que ficam registradas no repositório. Toda essa arquitetura facilita a integração com IAs e com processos automatizados. Vale um gostinho antes de seguir. 

![Captura da tela “Criar curso interno” com o formulário da etapa Informações e, à direita, um painel com as abas Áreas, Cenários, Feedback e Requisitos, listando atalhos para as etapas 1 a 5 da criação.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/homologacao.webp)

A Central de Homologação aberta na primeira etapa da criação de curso interno, na aba Cenários. 

Como a Central de Homologação funciona e como estamos construindo esses protótipos ficam para o próximo post. 

## O que ganhamos ao prototipar em código 

Um protótipo em código é a própria interface. Ele tem estados reais, navegação, componentes que se comportam como no produto e dados de demonstração que dão vida às telas. A conversa com quem avalia o fluxo muda: em vez de "imagine que este botão abre um painel", o painel abre. 

Também acabou o trabalho duplo de manter um arquivo de design e um protótipo dizendo coisas parecidas. O Figma deixou de ser parte do nosso processo de criação e validação. Um pouco desse produto, já publicado, dá para ver no case de [Keeps Products](https://bolivaralencastro.com.br/projects/keeps-learning-konquest.html), no meu portfólio. 

Essa forma de prototipar também facilita o handoff para a equipe de devs. O que se valida é código navegável, com estados, casos de borda e dados de exemplo ao alcance, e não um arquivo de design que alguém precisa interpretar e reconstruir. A Central de Homologação, que mostrei acima, é um exemplo: o time percorre as áreas, confere os casos difíceis e registra as correções direto no repositório. 

![Captura da tela inicial de uma plataforma de aprendizagem com menu lateral roxo, campo de busca, banner com estrada de terra ao entardecer e cards de trilhas em destaque.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/prototipo-home.webp)

O protótipo em código: a tela inicial do TalentOS, navegável e com estados reais.

![Captura de uma tela de feed com painel de canais e filtros à esquerda, um post com foto de bicicleta em frente a uma casa amarela ao centro e uma lista de pulses salvos à direita.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/prototipo-feed.webp)

A tela Feed do mesmo protótipo, com filtros, canais e pulses salvos. 

## O custo escondido 

O Figma nunca foi só um lugar para desenhar telas. Para o marketing, era uma bancada de montagem. Dava para pegar uma tela, separar um card, levantá-lo em camadas, colocar num mockup, aplicar vidro, sombra e perspectiva. Tudo isso sem escrever uma linha de código. 

Quando a interface virou código, essa liberdade sumiu para quem não trabalha com código. Ninguém decidiu tirá-la. Ela foi uma consequência. 

Percebemos isso recentemente, numa demanda de marketing: o preparo da apresentação do TalentOS, um deck com dezenas de slides. Não havia contexto em Figma para recorrer, porque tudo tinha sido feito do zero, já em código. O designer gráfico precisava de imagens da interface com elementos isolados: um card flutuando sobre o notebook, um modal em destaque, uma vista explodida. O que existia eram prints. Para isolar um componente a partir de um print, a única saída era redesenhá-lo à mão. 

![Captura do Figma com o arquivo “Konquest Components” marcado como “Locked”. À esquerda, a lista de páginas; no centro, telas de configuração em miniatura, no tom roxo da plataforma; embaixo, a barra “View only”.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/figma-bloqueado.webp)

O Figma que ficou para trás: o arquivo do design system, agora bloqueado e só para visualização. 

## A tentativa óbvia: só prompt 

Se existe IA generativa de imagem, por que não pedir? Tentamos. Com prompts longos, bem escritos, cheios de parâmetros. 

O resultado tinha sempre a mesma cara: o estilo "padrão" de imagem gerada. E a IA errava justamente no que importava: ou separava componentes demais, ou destacava o elemento errado, ou inventava detalhes na interface. Um prompt descreve uma intenção. Não entrega a tela certa, no ângulo certo, com o componente certo isolado. 

Vale comparar dois resultados lado a lado. À esquerda, o que saiu só com prompt: a IA reinterpretou a interface. O texto perdeu acentos ("voce", "criacao") e o logotipo virou "kee". À direita, o que saiu de uma cena do stage-viewer: o card, o título, o selo e as informações são os do protótipo, e a IA só cuidou de material, luz e ambiente. 

![Interface em camadas de vidro roxo brilhante, com a tela “Criar curso interno” e, à frente, um diálogo “Como voce quer criar o quiz?” com as opções “Criacao manual” e “Usar assistente de IA”.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/comparacao-so-prompt.webp)

Só com prompt: a IA reinterpretou a interface. O texto perdeu acentos (“voce”, “criacao”) e o logotipo virou “kee”.

![Close de um card de vidro “Onboarding Essentials”, com selo “Matriculado”, barra de progresso e as informações PT-BR, 4h30min e Onboarding, flutuando sobre um notebook desfocado ao fundo.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/comparacao-com-ferramenta.webp)

Com a ferramenta: a cena do stage-viewer define o card, o título e os selos, e a IA cuida de material e luz. 

## O insight: dar à IA uma base real 

A conclusão foi simples e mudou o rumo: **a IA precisa receber uma base correta**. Se a imagem de entrada já tem a interface real, na posição e na perspectiva desejadas, o modelo deixa de ser o autor da tela e vira um refinador de materiais, luz e ambiente. 

Já tinha esbarrado numa versão desse mesmo problema, de outro ângulo, ao produzir vídeo com IA generativa: no [experimento com OpenRouter, Veo e Seedance](https://bolivaralencastro.com.br/blog/do-elevador-ao-making-of-openrouter-veo-seedance.html), o que resolvia a cena não era um prompt mais elaborado, era ter uma referência visual concreta para o modelo seguir. Aqui, o padrão se repetiu: a saída depende muito mais da base que você entrega do que do texto que você escreve. 

Precisávamos de uma ferramenta que produzisse essa base. Como o protótipo já era código, ela podia morar ao lado dele. 

![Card horizontal com miniatura de paisagem, o título “Comunicação Assertiva na Prática”, a duração “Aula · 12 min” e o botão “Assistir”, como uma peça 3D cinza sobre uma grade.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/componente-3d-card-aula.webp)

Um componente extraído da tela e extrudado como peça 3D.

![Card de vidro translúcido com o título “Comunicação Assertiva na Prática” e o botão “Assistir”, sobre uma superfície reflexiva roxa com luzes.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/componente-ia-card-vidro.webp)

O mesmo componente como peça de vidro, em ambiente roxo espelhado, gerado por IA. 

![Notebook aberto exibindo a tela inicial de aprendizagem corporativa roxa, apoiado sobre um modelo 3D escuro de rocha, com fundo cinza claro.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/mockup-3d-notebook-rocha.webp)

O notebook com a tela real do protótipo sobre um modelo 3D de rocha importado. 

## O stage-viewer 

![Captura da ferramenta com painel de objetos à esquerda, notebook 3D no centro com cards elevados e painel de propriedades à direita, com os botões Componente, Notebook 3D e Celular 3D.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/interface-notebook-cards.webp)

Lista de objetos, cards extraídos e painel de apresentação. 

O stage-viewer vive dentro do nosso site de protótipos. Ele se conecta diretamente às telas do protótipo, e qualquer pessoa da equipe pode montar cenas sem tocar em código. Na prática: 
 
- **Escolhe a tela** do protótipo (desktop ou mobile) e navega nela até o estado desejado antes de capturar. 
- **Aplica a tela real** em modelos 3D: notebook, celular ou como uma placa plana. É a tela viva do protótipo, não um print recortado. 
- **Destaca componentes, e não só telas inteiras**: em vez de levar a tela toda, seleciona só o que interessa (um card, um banner, um botão, um modal ou uma parte dele) e o eleva em camada. Dá para capturar a tela com esses destaques ou apenas os componentes escolhidos, como objetos independentes, sem a tela de fundo. 
- **Controla câmera e luz**: ângulo, enquadramento, iluminação, fundo. Dá para importar modelos 3D e compor com vários objetos na mesma cena. 
- **Exporta a cena** em imagem. 
 

A cena pode ser a imagem final, e serve muito bem como base para a IA. 

## O fluxo completo 

![Interface dividida em quatro quadros. O superior esquerdo mostra um notebook e um celular renderizados; os outros mostram as vistas superior, frontal e lateral, com a câmera desenhada em linhas roxas. À esquerda, a lista de objetos; à direita, as propriedades do celular.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/interface-4-vistas.webp)

O stage-viewer em quatro vistas: câmera da composição, superior, frontal e lateral.

Seu navegador não suporta vídeo HTML5.

O card se descola da tela do celular em etapas e a câmera gira em volta. 
 
1. Tela real do protótipo. 
1. Cena no stage-viewer: dispositivo, componente em destaque, câmera. 
1. Exportação em PNG. 
1. Envio para uma IA generativa de imagem, com uma instrução que virou regra de casa: **edite a imagem, não recrie do zero**. A IA refina material, luz e ambiente e não mexe na interface. 
1. Retoque em editor de imagem e aplicação no slide. 
 

Nos slides do TalentOS, isso deu consistência: mesma linguagem visual, dispositivos diferentes, e componentes que de fato existem no produto. Uma ideia que surgiu no caminho: usar a mesma cena como quadro inicial e final de animações. 

## Do mockup ao escritório inteiro 

![Notebook em ângulo três quartos com uma tela de aprendizagem roxa; dois cards de trilha, com título e selo, saem da tela e flutuam à frente do teclado.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/cena-notebook-cards.webp)

Notebook 3D com dois cards de trilha em camada à frente da tela.

![Celular em perspectiva mostrando “Criar curso interno” e a lista de cinco etapas; um cartão com a etapa 4, “Conteúdos”, flutua à frente da tela, sobre fundo cinza.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/cena-celular-card.webp)

Celular com a lista de etapas da criação de curso interno; a etapa “Conteúdos” se descola da tela. 

![Notebook exibindo a tela “Conteúdos” da criação de curso interno, com um botão “Novo Tópico” e outros elementos elevados; ao lado, um celular com a lista de etapas e a etapa “Conteúdos” em destaque.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/cena-desktop-mobile.webp)

Duas telas na mesma cena: o notebook na etapa Conteúdos da criação de curso e o celular com a lista de etapas.

![Notebook e celular vistos de um ângulo mais baixo, com a tela de conteúdos da criação de curso e a lista de etapas, sobre fundo cinza.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/cena-angulo-baixo.webp)

A mesma cena com a câmera em outro ângulo, mais baixo e lateral. 

![Notebook com o Feed do protótipo e, ao lado, um celular com o Feed mobile; um card de post com foto de bicicleta em frente a uma casa amarela flutua à frente do celular.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/cena-feed-desktop-mobile.webp)

A tela Feed no notebook e no celular, com o card do post elevado. 

Com o notebook e o celular funcionando, testamos o que mais a ferramenta aguentava. Colocamos o mesmo notebook sobre um modelo 3D de rocha importado, para depois pedir à IA um ambiente escuro e nebuloso. Extrudamos um card de aula em uma peça de vidro. Fizemos o celular ganhar um ambiente de loja. Em cada caso, a cena 3D define composição, ângulo e o que está na tela, e a IA só cuida de materiais, luz e clima. 

Um caso mostra por que o ajuste fino importa. Na primeira tentativa do celular na loja, o aparelho estava em um ângulo que produziu uma imagem final ruim. 

![Celular 3D inclinado e visto de baixo, com a tela de trilhas e cursos em perspectiva forçada, sobre fundo cinza claro.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/ajuste-antes-cena-3d.webp)

Antes: o celular na cena 3D em um ângulo que levou a uma imagem final ruim.

![Celular sobre um suporte branco numa loja de eletrônicos, inclinado para frente e com a tela em perspectiva distorcida, com pessoas desfocadas ao fundo.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/ajuste-antes-ia.webp)

Antes: a imagem gerada por IA herdou o ângulo, e o aparelho aparece inclinado e desproporcional. 

Como a base é uma cena 3D, o caminho foi reposicionar o smartphone, com o modelo de referência certo, e gerar de novo. A segunda imagem saiu com o aparelho reto no expositor. Em vez de reescrever um prompt, mudamos a posição de um objeto. 

![Celular inclinado exibindo trilhas em destaque e cursos recomendados, com cards de fotos de paisagens, sobre fundo cinza claro.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/ajuste-depois-cena-3d.webp)

Depois: o celular reposicionado na cena 3D, com o modelo de referência certo.

![Celular sobre um suporte branco numa loja de eletrônicos ampla com janelas, plantas e pessoas desfocadas ao fundo, exibindo cards de trilhas e cursos.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/ajuste-depois-ia.webp)

Depois: o resultado da IA, com o aparelho reto no expositor. 

O teste mais interessante veio depois: um escritório virtual. É uma maquete 3D simples, com sete pessoas em poses fixas, mesas com monitores, uma mesa redonda, sofá, plantas, janelas e um quadro de atividades. Não tem rosto, textura ou luz realistas, e não precisa ter. 

![Maquete 3D de um escritório em vista isométrica, com pessoas de formas simples sentadas em mesas de madeira com monitores, duas pessoas em pé conversando, um sofá verde, uma mesa redonda, janelas e um quadro na parede, sobre fundo cinza.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/escritorio-isometrica.webp)

A maquete 3D do escritório vista de cima, em isométrica: sete pessoas, quatro mesas, mesa redonda, sofá, janelas e quadro de atividades. 

Dentro dela, movemos a câmera como numa sessão de fotos: vista isométrica de cima, câmera na altura dos olhos com lente aberta, vista de cima da mesa, close com profundidade de campo. Cada enquadramento vai para a IA, que o transforma em fotografia. 

![Cena 3D vista de cima de uma mesa, com teclado, monitor, caderno verde e uma cabeça de pessoa na parte de baixo. No canto superior direito, setas coloridas de transformação.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/escritorio-vista-de-cima.webp)

Vista de cima do teclado; o gizmo colorido mostra que cada objeto da cena pode ser movido.

![Foto aérea de uma mesa de madeira com monitor exibindo uma tabela de cargos, teclado, caderno, planta, xícara de café e uma pessoa digitando, vista por trás.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/escritorio-ia-vista-de-cima.webp)

Foto gerada por IA com a vista de cima da mesa. A pessoa digitando e a tela “Cargos” vêm do protótipo. 

![Close em 3D de uma pessoa de costas diante de um monitor, com outra pessoa desfocada ao lado e a parede ao fundo.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/escritorio-profundidade-de-campo.webp)

Profundidade de campo: o primeiro plano nítido e o fundo desfocado.

![Foto de um homem de camisa azul visto de costas, diante de um monitor com a tabela “Cargos” e um painel lateral de edição de perfil, com caneca, caderno e escritório desfocado ao fundo.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/escritorio-ia-por-cima-do-ombro.webp)

Câmera por cima do ombro, gerada por IA. 

![Cena 3D vista de perto de duas pessoas em pé, uma de camiseta vermelha e outra de azul, com mesas, monitores, plantas e um quadro ao fundo.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/escritorio-pessoas-em-pe.webp)

Duas pessoas conversando em primeiro plano; o resto do escritório ao fundo.

![Foto de uma mulher de suéter terracota e um homem de camisa azul conversando em pé, em um escritório com mesas, monitores, um quadro branco com notas e janelas ao fundo.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/escritorio-ia-conversa.webp)

Uma cena de conversa no escritório, gerada por IA. 

O que ganhamos é **consistência de direção de cena**. O quadro na parede, o ripado de madeira, as janelas e a posição das mesas são os mesmos em todas as imagens, porque vêm da mesma maquete. Sem ela, cada prompt inventa um escritório novo. 

## Lentes e proporções: fotografar a cena 

O stage-viewer também tem o vocabulário de quem fotografa. Cada cena aceita lentes (padrão, grande-angular, teleobjetiva, olho de peixe e ortográfica), desfoque com escolha do ponto de foco e proporções de exportação (16:9, 9:16, 1:1, 4:5, 4:3, 3:4, 3:2, 2:3 e 21:9). 

Isso muda o que dá para pedir. Com a mesma posição de câmera, o olho de peixe curva o monitor e estica o espaço, enquanto a lente padrão mantém a perspectiva natural. 

![Cena 3D de um personagem de camiseta azul sentado a uma mesa de madeira diante de um monitor, com duas pessoas conversando ao fundo.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/lente-padrao.webp)

Lente padrão, 16:9: perspectiva natural do personagem à mesa.

![O mesmo personagem sentado à mesa, com o monitor à esquerda curvado e as linhas do ambiente distorcidas pela lente de campo amplo.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/lente-olho-de-peixe.webp)

Olho de peixe, mesma posição de câmera: o monitor se curva e o espaço se estica. 

Um plano retrato em 4:5, com foco no rosto e desfoque no fundo, vira algo entre um retrato e uma cena de escritório. Uma teleobjetiva em 21:9 comprime os planos e mantém em foco o personagem que usa o computador, com os outros em camadas desfocadas. 

![Close do rosto e ombros de um personagem 3D de camiseta azul, com uma mulher de camiseta terracota desfocada ao fundo.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/retrato-desfoque.webp)

Plano retrato em 4:5 com desfoque: o rosto nítido e a colega ao fundo suavizada.

![Cena panorâmica de um escritório em 3D: um homem de camiseta azul sentado à mesa, nítido, digitando; à esquerda, um monitor escuro e uma colega desfocados; à direita, outro monitor em primeiro plano, também desfocado.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/teleobjetiva.webp)

Teleobjetiva em 21:9: o personagem que usa o computador nítido, com os monitores e a colega em planos desfocados. 

E o mesmo enquadramento pode sair quadrado, vertical ou panorâmico sem refazer a cena. 

![O personagem de camiseta azul sentado à mesa, em corte panorâmico.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/proporcao-21x9.webp)

21:9

![O personagem de camiseta azul sentado à mesa, em corte quadrado.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/proporcao-1x1.webp)

1:1

![O personagem de camiseta azul sentado à mesa, em corte retrato.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/proporcao-4x5.webp)

4:5

![O personagem de camiseta azul sentado à mesa, em corte vertical.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/proporcao-9x16.webp)

9:16 

## Cenas animadas 

A ferramenta também anima. Uma linha do tempo por keyframes move o celular ou o notebook, a câmera, a separação dos componentes e as luzes, e o próprio app exporta o resultado em vídeo. Neste exemplo, montei uma coreografia de seis segundos que lembra uma apresentação de produto: a câmera começa baixa e distante, se aproxima de frente e termina numa visão em três quartos, enquanto o celular gira e flutua devagar. 

![Interface do stage-viewer com um celular 3D exibindo a tela inicial do protótipo sobre fundo escuro e, abaixo, a linha do tempo de animação com trilhas e losangos de keyframe nos instantes 0, 3 e 6 segundos.](https://bolivaralencastro.com.br/assets/images/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida/editor-de-animacao.webp)

O editor de animação do stage-viewer: uma linha do tempo com keyframes para o celular, a câmera, a separação e as luzes. 

Seu navegador não suporta vídeo HTML5.

O resultado exportado pelo app: a câmera se aproxima e o celular gira, em uma cena de seis segundos. 

Essas cenas animadas também servem de base para vídeos gerados por IA. Os dois exemplos abaixo nasceram assim: em um, a câmera filma o celular parado; no outro, ela se move em volta dele. 

Seu navegador não suporta vídeo HTML5.

Vídeo gerado por IA a partir de uma cena do stage-viewer: a câmera se move em volta do celular.

Seu navegador não suporta vídeo HTML5.

Outro vídeo gerado por IA a partir de uma cena do stage-viewer: a câmera filma o celular parado. 

## Limites e o que aprendemos 
 
- **A IA ainda inventa.** Quando geramos sem imagem de referência, alguns componentes saíram errados. Com a base, o problema diminui, mas revisar continua sendo obrigatório (reparou no erro [nesta imagem](https://bolivaralencastro.com.br/blog/paramos-de-desenhar-telas-o-marketing-pediu-uma-vista-explodida.html#erro-foto-ombro)?). 
- **O PNG sai com o fundo da cena.** Para peças com fundo transparente, o recorte é feito depois. 
- **A IA inventa texto.** Nas fotos do escritório, canecas e paredes ganharam frases diferentes a cada imagem ("ideias pessoas impacto", "Pessoas Produtos Resultados"). Na cena do notebook sobre a rocha, alguns rótulos da interface mudaram de nome. Quanto mais realista a saída, mais é preciso conferir texto. 
- **Direção de arte não desaparece.** Em um caso, o elemento flutuou para o lado errado, e foi mais rápido corrigir no retoque do que na cena. 
- **Não abandonamos o olhar de design.** A ferramenta tira a barreira técnica, não o critério. Sem padrão, dá "Frankenstein": tela plana, mockup e efeito misturados. 
- **Ferramenta interna.** O stage-viewer não é público. Ele existe para o nosso time. Mas, se quiser conversar sobre ele, me chame no [LinkedIn](https://www.linkedin.com/in/bolivaralencastro/). 
 

O que fica é uma lição menos sobre IA e mais sobre processo. Quando você troca de ferramenta, você troca junto tudo o que ela fazia sem ninguém pedir. Vale listar, antes de perceber a perda no meio de uma apresentação. 

E, para trabalhar bem com IA generativa, quase sempre a pergunta certa não é "qual prompt?". É "qual base eu estou entregando?". 

Esse tipo de registro de processo é uma linha que venho puxando por aqui: já escrevi sobre [como automatizei a publicação deste blog no LinkedIn via API](https://bolivaralencastro.com.br/blog/publicando-no-linkedin-com-python-e-api.html) e sobre os limites da geração de vídeo por IA no post citado acima. São bastidores diferentes da mesma pergunta: onde a ferramenta ajuda, e onde o critério continua sendo meu. 

## Sobre a Keeps 

Trabalho na [Keeps](https://keeps.com.br/), uma empresa de tecnologia educacional que atua com educação corporativa. Nossa proposta é transformar treinamentos em resultados, com experiências de aprendizado eficientes, apoiadas em inteligência artificial e análise de dados. 

Hoje temos quatro soluções: 
 
- **Konquest:** plataforma de LMS/LXP com IA, para a experiência de aprendizagem e a gestão do treinamento. 
- **Smartzap:** transforma o WhatsApp em ferramenta de capacitação. 
- **Fábrica de Conteúdos:** serviço de produção de conteúdo para simplificar as operações de T&D. 
- **GoLearning:** streaming de cursos para pessoas do T&D. 
 

Nosso público são empresas que querem modernizar o treinamento e o desenvolvimento de pessoas, do onboarding aos programas de liderança. Já alcançamos mais de 200 empresas e mais de 500 mil colaboradores. 

Foi nesse contexto, o de um time de Product Design que prototipa direto em código, que o stage-viewer nasceu. 

Quer conhecer os produtos e serviços da Keeps? [Fale com o nosso time de vendas pelo WhatsApp](https://wa.me/5548991997306?text=Ol%C3%A1%21%20Vim%20a%20partir%20do%20blogpost%20do%20product%20designer%20de%20voc%C3%AAs%20%28bolivaralencastro.com.br%29%20e%20gostaria%20de%20conhecer%20os%20produtos%20e%20servi%C3%A7os%20da%20Keeps.). 

 

Sobre o autor 

 ![Foto de Bolívar Alencastro](https://bolivaralencastro.com.br/assets/images/author/bolivar-alencastro.webp) 

 

### [Bolívar Alencastro](https://bolivaralencastro.com.br/about.html) 

Product Designer em São Paulo, hoje protótipando direto em código na Keeps e construindo as ferramentas internas (como o stage-viewer) que esse jeito de trabalhar passou a exigir. 
 
- [LinkedIn](https://www.linkedin.com/in/bolivaralencastro/) 
- [Instagram](https://www.instagram.com/bolivar.alencastro/) 
      

 

## Outras Publicações 

 [![Capa do post: A segunda corda](https://bolivaralencastro.com.br/assets/images/blog/a-segunda-corda/card.webp)](https://bolivaralencastro.com.br/blog/a-segunda-corda.html) 

### [A segunda corda](https://bolivaralencastro.com.br/blog/a-segunda-corda.html) 

A linha de vida que impediu a queda de Mayk abre uma reflexão sobre trabalho, propriedade, tecnologia e as proteções que sustentam quem trabalha.  

 [![Capa do post: Há Quedas Por Vir](https://bolivaralencastro.com.br/assets/images/blog/ha-quedas-por-vir/card.webp)](https://bolivaralencastro.com.br/blog/ha-quedas-por-vir.html) 

### [Há Quedas Por Vir](https://bolivaralencastro.com.br/blog/ha-quedas-por-vir.html) 

Um relato em cinco tempos sobre Há Quedas Por Vir, de Érica Storer e Sansa: shibari, um escritório suspenso e a queda que nunca chega.  

 [![Capa do post: Janelas de profundidade: paralaxe com rastreamento facial no navegador](https://bolivaralencastro.com.br/assets/images/blog/janelas-de-profundidade-parallax-facial-no-navegador/card.webp)](https://bolivaralencastro.com.br/blog/janelas-de-profundidade-parallax-facial-no-navegador.html) 

### [Janelas de profundidade: paralaxe com rastreamento facial no navegador](https://bolivaralencastro.com.br/blog/janelas-de-profundidade-parallax-facial-no-navegador.html) 

Construí uma técnica de renderização que transforma a tela do computador numa janela de verdade: a webcam segue a posição da sua cabeça e a cena 3D recalcula a perspectiva a cada quadro, com sombra do seu próprio corpo caindo sobre o cenário.
