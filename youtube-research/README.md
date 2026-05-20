# Video Research

Organizacao local para pesquisa de videos do YouTube e, em modo limitado, de
Reels/posts publicos do Instagram dentro deste repositorio.

## Estrutura

- `scripts/collect_video_research.py`: coleta transcript, comentarios e replies
  de YouTube e faz transcricao por audio para Instagram
- `scripts/analyze_learning.py`: segunda camada de analise guiada por prompt
- `prompts/learning-analysis-v2.md`: prompt versionavel para extrair aprendizado complementar
- `videos/<titulo-do-video>--<video_id>/`: uma pasta por video analisado

## Arquivo final por video

Leia primeiro:

- `videos/<titulo-do-video>--<video_id>/final-learning-report.md`

Arquivos auxiliares por video:

- `video.json`
- `transcript.json`
- `transcript.txt`
- `comments.json`
- `summary.json`
- `report.md`
- `transcript_debug.json`
- `ai_insights.json`
- `ai_insights_learning.json`

## Fluxo

```bash
# 1. Coletar material do video
python3 youtube-research/scripts/collect_video_research.py 'https://www.youtube.com/watch?v=VIDEO_ID'
python3 youtube-research/scripts/collect_video_research.py 'https://www.instagram.com/rndyrbrts/reel/DWpSK4uDhIO/'

# 2. Rodar a segunda camada de analise
python3 youtube-research/scripts/analyze_learning.py youtube-research/videos/<titulo-do-video>--VIDEO_ID
```
