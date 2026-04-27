# Cortex

## Resumo Executivo
- Tese do produto: automatizar intake, leitura, validacao e preenchimento de formularios em operacoes documentais de planos de saude PME.
- ICP / comprador: corretoras, operacoes de beneficios e gestores de backoffice com alto volume de documentos.
- Caso de uso principal: transformar pacotes documentais dispersos em fichas preenchidas, revisaveis e auditaveis.
- Status da avaliacao: preliminar a partir de pitch, demo e feedback da banca.

## Scorecard
### Pitch Score (/50)
- Clareza do problema e da proposta de valor (/10): 7
- Narrativa e estrutura do pitch (/10): 6
- Demo e capacidade de explicacao (/10): 8
- Mercado, modelo de negocio e ROI (/10): 6
- Credibilidade geral da apresentacao (/10): 7

### Product Score (/50)
- Intensidade da dor (/10): 9
- Atratividade do mercado (/10): 8
- Diferenciacao e posicionamento competitivo (/10): 7
- Viabilidade de execucao e AI fit (/10): 8
- Trust, risco operacional e compliance (/10): 7

### Nota Total (/100)
- Pitch: 34
- Produto: 39
- Total: 73

## Leitura Critica
### O que esta forte
- Escolheu um wedge especifico e nao uma abstracao ampla de "automacao".
- Aplicou IA no lugar certo: OCR, extracao, validacao cruzada, preenchimento e flags de confianca.
- Mistura bem componentes probabilisticos com checagens deterministicas.
- Ja comeca a raciocinar em custo por caso e futura distribuicao via API.

### O que esta fraco
- O pitch e pior que o produto: a demo explica mais do que a abertura.
- O business case ainda nao fecha em dinheiro economizado, so em tempo.
- O risco operacional ainda esta subdimensionado: erro custa caro nesse fluxo.
- "9 modelos orquestrados" soa sofisticado, mas tambem sugere complexidade e fragilidade.
- Faltou benchmark competitivo explicito contra OCR/document AI/RPA vertical.

## Benchmark
### Benchmark Nacional
- Empresa: Docket IA
- Tipo de benchmark: adjacente
- O que prova: existe mercado nacional para automacao documental com IA, com foco em extracao, analise, rastreabilidade e ganho de produtividade em operacoes complexas.
- Fonte oficial: https://docket.com.br/docket-ia/ ; https://docket.com.br/solucoes/

### Benchmark Internacional
- Empresa: Instabase
- Tipo de benchmark: adjacente forte
- O que prova: o padrao internacional para esse tipo de solucao ja exige automacao de workflows document-heavy com validacao, auditabilidade, embedding em fluxo e foco em seguros/beneficios.
- Fonte oficial: https://www.instabase.com/product/ai-hub/automate ; https://www.instabase.com/solutions/insurance

## Leitura Estrategica
- O produto parece mais: software operacional vertical de document intelligence.
- Risco principal: baixa confiabilidade em casos de borda sem um sistema de avaliacao e revisao humana bem desenhado.
- Principal pergunta aberta: a economia por caso compensa o risco e o custo de implantacao?

## Recomendacao
- Seguir / pivotar / estreitar wedge: seguir e aprofundar o wedge atual.
- Proxima validacao critica: acuracia por campo, taxa de revisao manual e economia real por operacao/analista.
- Metricas que precisariam aparecer na proxima versao:
- tempo por caso
- custo por caso em 3 cenarios
- taxa de preenchimento correto
- taxa de documentos com inconsistencia detectada
- percentual de casos que precisam de fallback humano

## Fontes
- https://docket.com.br/docket-ia/
- https://docket.com.br/solucoes/
- https://www.instabase.com/product/ai-hub/automate
- https://www.instabase.com/solutions/insurance
- https://platform.openai.com/docs/guides/evaluation-best-practices
- https://www.anthropic.com/research/building-effective-agents/
