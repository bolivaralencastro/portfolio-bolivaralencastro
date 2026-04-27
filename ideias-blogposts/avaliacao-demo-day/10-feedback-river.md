# Feedback River

## Resumo Executivo
- Tese do produto: consolidar feedbacks espalhados em varios canais, quebrar, resumir, classificar, priorizar e transformar isso em inteligencia acionavel para produto.
- ICP / comprador: times de produto, pesquisa e CX que recebem alto volume de feedback qualitativo.
- Caso de uso principal: transformar feedback textual disperso em dashboard de temas, sentimento, prioridade e contexto para tomada de decisao.
- Status da avaliacao: preliminar a partir de pitch, demo e feedback da banca.

## Scorecard
### Pitch Score (/50)
- Clareza do problema e da proposta de valor (/10): 7
- Narrativa e estrutura do pitch (/10): 6
- Demo e capacidade de explicacao (/10): 7
- Mercado, modelo de negocio e ROI (/10): 4
- Credibilidade geral da apresentacao (/10): 7

### Product Score (/50)
- Intensidade da dor (/10): 7
- Atratividade do mercado (/10): 6
- Diferenciacao e posicionamento competitivo (/10): 5
- Viabilidade de execucao e AI fit (/10): 7
- Trust, risco operacional e compliance (/10): 7

### Nota Total (/100)
- Pitch: 31
- Produto: 32
- Total: 63

## Leitura Critica
### O que esta forte
- O time entendeu uma dor real: feedback chega quebrado, em varios canais, e vira muito trabalho operacional antes de virar decisao.
- A arquitetura em modulos faz sentido: fragmentar, resumir, classificar, priorizar e avaliar.
- Foi um dos poucos projetos que trouxe `evals` de forma explicitamente estruturada.
- Existe uma boa tese de transformar informacao qualitativa em inteligencia quantitativa.

### O que esta fraco
- Cai na mesma pressao competitiva dos produtos para PM: um time maduro pode tentar montar algo parecido com stack generico.
- A demo mostrou pouco da promessa de omnicanalidade; no MVP, apareceu basicamente um formulario.
- Nao ficou claro quem compra, quem usa e como isso monetiza.
- O diferencial frente a opcoes genericas ou plataformas existentes ainda esta fraco.
- O pitch abriu com consolidacao de feedback multicanal, mas a prova de produto ainda esta aquem dessa ambicao.

## Benchmark
### Benchmark Nacional
- Empresa: Track.co
- Tipo de benchmark: adjacente
- O que prova: existe mercado nacional maduro para coleta, organizacao e analise de feedback de clientes, NPS e CX; isso valida a dor, mas eleva a barra para um produto de inteligencia de feedback.
- Fonte oficial: https://track.co/feedback-de-clientes/

### Benchmark Internacional
- Empresa: Productboard
- Tipo de benchmark: direto/adjacente forte
- O que prova: o benchmark internacional para transformar voz do cliente em decisao de produto ja inclui consolidacao de feedback de varias fontes, insights acionaveis e ligacao entre feedback e priorizacao.
- Fonte oficial: https://www.productboard.com/product/insights/ ; https://www.productboard.com/lp/product-trial/

## Leitura Estrategica
- O produto parece mais: feedback intelligence layer para times de produto.
- Risco principal: baixa defensabilidade se continuar parecendo uma composicao de LLM + dashboard para publico com alto letramento em IA.
- Principal pergunta aberta: o valor principal esta na consolidacao multicanal, nos evals, na priorizacao ou na camada de decisao para PM?

## Recomendacao
- Seguir / pivotar / estreitar wedge: seguir, mas estreitar o wedge para uma tese mais dura de intelligence ops multicanal.
- Proxima validacao critica: provar que o produto reduz tempo de analise sem piorar qualidade e gera decisoes melhores do que o fluxo atual.
- Metricas que precisariam aparecer na proxima versao:
- tempo economizado por ciclo de analise
- taxa de classificacao correta
- taxa de prioridade correta
- taxa de aprovacao sem ajuste humano
- quantidade de canais integrados de verdade

## Fontes
- https://track.co/feedback-de-clientes/
- https://www.productboard.com/product/insights/
- https://www.productboard.com/lp/product-trial/
- https://canny.io/
- https://canny.io/features/autopilot
- https://platform.openai.com/docs/guides/evaluation-best-practices
