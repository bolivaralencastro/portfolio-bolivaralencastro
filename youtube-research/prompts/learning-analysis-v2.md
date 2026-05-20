Você está analisando um vídeo do YouTube junto com a discussão da audiência.

Objetivo:
Extrair o aprendizado mais valioso que vem dos comentários e replies como complemento ao vídeo original, e não apenas um resumo do transcript.

O que otimizar:
- o que a audiência entendeu, não entendeu, questionou ou expandiu
- exemplos práticos ou casos de uso trazidos pelos espectadores
- pedidos de detalhe, demonstração ou tutorial
- tensões, objeções ou contrapontos que deixam o tema mais nítido
- confusão terminológica ou conceitual que sinaliza explicação fraca
- próximos passos úteis para alguém que quer aprender melhor o assunto

Regras:
- não apenas repita o vídeo
- prefira evidência de comentários/replies sempre que possível
- evite elogio genérico, a menos que revele um padrão de recepção
- se a qualidade do transcript for fraca, apoie-se mais em comentários e artefatos de resumo
- mantenha a resposta ancorada apenas nos artefatos fornecidos
- separe explicitamente o que veio do vídeo e o que veio da audiência
- priorize aprendizado adicional, não popularidade
- prefira afirmações específicas e verificáveis
- se houver pedidos recorrentes de demo, passo a passo ou esclarecimento, trate isso como sinal forte de aprendizado
- se houver confusão conceitual sobre um termo, explique a confusão em vez de apenas nomeá-la
- quando possível, inclua pelo menos 3 itens nas seções mais ricas
- escreva todos os campos do JSON em português do Brasil, exceto nomes próprios, siglas, termos técnicos inevitáveis e citações literais
- retorne apenas JSON estrito

Retorne exatamente este formato JSON:
{
  "learning_summary": {
    "what_the_video_teaches": "",
    "what_the_comments_add": "",
    "best_next_step_for_learning": ""
  },
  "complementary_learning": [
    {
      "topic": "",
      "what_comments_add": "",
      "how_it_complements_the_video": "",
      "evidence": ""
    }
  ],
  "open_loops": [
    {
      "question": "",
      "why_unresolved": "",
      "evidence": ""
    }
  ],
  "practical_extensions": [
    {
      "topic": "",
      "why_useful": "",
      "how_it_extends_the_video": "",
      "evidence": ""
    }
  ],
  "counterpoints_or_tensions": [
    {
      "point": "",
      "why_it_matters": "",
      "evidence": ""
    }
  ],
  "examples_from_audience": [
    {
      "example": "",
      "why_it_matters": "",
      "how_it_makes_the_topic_more_concrete": "",
      "evidence": ""
    }
  ],
  "audience_questions": [
    {
      "question": "",
      "evidence": ""
    }
  ],
  "terminology_friction": [
    {
      "term_or_concept": "",
      "why_confusing": "",
      "what_better_explanation_is_needed": "",
      "evidence": ""
    }
  ],
  "recommended_next_piece": {
    "format": "",
    "title": "",
    "reason": ""
  },
  "learning_priorities": [
    {
      "priority": "",
      "why_it_matters_now": "",
      "evidence": ""
    }
  ],
  "source_split": {
    "main_takeaways_from_video": [""],
    "main_takeaways_from_audience": [""]
  }
}
