# Omnidoc

## Resumo Executivo
- Tese do produto: reduzir carga operacional do medico com agendamento, intake, transcricao de consulta e copiloto sobre o historico do paciente.
- ICP / comprador: clinicas e medicos com alta dor administrativa.
- Caso de uso principal: estruturar contexto clinico antes, durante e depois da consulta.
- Status da avaliacao: preliminar a partir de pitch, demo e feedback da banca.

## Scorecard
### Pitch Score (/50)
- Clareza do problema e da proposta de valor (/10): 7
- Narrativa e estrutura do pitch (/10): 6
- Demo e capacidade de explicacao (/10): 8
- Mercado, modelo de negocio e ROI (/10): 5
- Credibilidade geral da apresentacao (/10): 6

### Product Score (/50)
- Intensidade da dor (/10): 9
- Atratividade do mercado (/10): 8
- Diferenciacao e posicionamento competitivo (/10): 7
- Viabilidade de execucao e AI fit (/10): 7
- Trust, risco operacional e compliance (/10): 7

### Nota Total (/100)
- Pitch: 32
- Produto: 38
- Total: 70

## Leitura Critica
### O que esta forte
- Dor intensa e muito facil de entender.
- Momento magico do produto e claro: transformar conversa e documentos em prontuario util.
- Existe uma tese de produtividade real e uma narrativa de validacao com medicos.
- O time ja pensou em custo de tokens, diferenciacao e nao-diagnostico.

### O que esta fraco
- Escopo muito amplo para o estagio atual.
- Abrir uma nova interface para o medico contradiz o benchmark mais forte da categoria.
- A camada de trust clinico ainda esta fraca: faltam referencias de origem, evals e governanca forte.
- O risco LGPD/compliance nao pode ser tratado como detalhe.
- O wedge mais forte nao esta totalmente escolhido: intake, scribe, prontuario, copiloto e agenda aparecem juntos.

## Benchmark
### Benchmark Nacional
- Empresa: Feegow Clinic com Noa Notes
- Tipo de benchmark: direto/adjacente
- O que prova: ja existe no Brasil oferta de software medico com IA que promete cuidar das anotacoes clinicas dentro de um stack de gestao e prontuario.
- Fonte oficial: https://feegowclinic.com.br/software-medico ; https://feegowclinic.com.br/funcionalidades/prontuario

### Benchmark Internacional
- Empresa: Abridge
- Tipo de benchmark: direto
- O que prova: o benchmark internacional de ambient clinical documentation ja exige integracao no workflow, compliance, auditabilidade e ligacao entre output da IA e a fonte da conversa.
- Fonte oficial: https://www.abridge.com/platform/clinicians ; https://www.abridge.com/product

## Leitura Estrategica
- O produto parece mais: ambient scribe + clinical workflow assistant.
- Risco principal: confianca clinica, regulacao e integracao com sistemas ja usados pelo medico.
- Principal pergunta aberta: qual e o wedge inicial certo com menor risco e maior disposicao de compra?

## Recomendacao
- Seguir / pivotar / estreitar wedge: seguir, mas estreitar para documentacao/estrutura de contexto antes de tentar ser copiloto amplo.
- Proxima validacao critica: prova de reducao de tempo com trilha auditavel e baixo risco regulatorio.
- Metricas que precisariam aparecer na proxima versao:
- tempo poupado por consulta
- adesao do medico ao fluxo
- taxa de edicao manual da nota
- erro clinico critico / falso contexto
- percentual de outputs com evidencia rastreavel

## Fontes
- https://feegowclinic.com.br/software-medico
- https://feegowclinic.com.br/funcionalidades/prontuario
- https://www.abridge.com/platform/clinicians
- https://www.abridge.com/product
- https://www.nabla.com/
- https://www.gov.br/anpd/pt-br/acesso-a-informacao/perguntas-frequentes/perguntas-frequentes/2-dados-pessoais/2-6-quais-sao-as
- https://www.gov.br/anpd/pt-br/acesso-a-informacao/institucional/atos-normativos/regulamentacoes_anpd/resolucao-cd-anpd-no-2-de-27-de-janeiro-de-2022
