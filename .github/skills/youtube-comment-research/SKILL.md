---
name: youtube-comment-research
description: Collect transcript, top-level comments, and comment replies from a YouTube video URL and turn that material into audience research. Also supports Instagram URLs in a limited mode that reuses media transcription when comments are unavailable.
---

# YouTube Comment Research

Use this skill when a task starts from a YouTube URL and the useful output is not just raw data, but editorial research derived from the audience around the video. For Instagram URLs, the useful output is transcript-driven research, because comments are not collected in this workflow.

## Before running

- Confirm `YOUTUBE_API_KEY` exists in the repository `.env`.
- Confirm `OPENROUTER_API_KEY` exists if transcript fallback by audio is required.
- Work from the repository root so output paths resolve correctly.
- Treat transcript capture as a two-stage workflow:
  - public captions first
  - audio fallback with `yt-dlp` + `ffmpeg` + OpenRouter STT when captions are unavailable

## Default command

```bash
python3 youtube-research/scripts/collect_video_research.py 'https://www.youtube.com/watch?v=VIDEO_ID'
```

Useful variants:

```bash
python3 youtube-research/scripts/collect_video_research.py 'https://youtu.be/VIDEO_ID' --lang pt
python3 youtube-research/scripts/collect_video_research.py 'https://www.youtube.com/watch?v=VIDEO_ID' --max-comments 500
python3 youtube-research/scripts/collect_video_research.py 'https://www.youtube.com/watch?v=VIDEO_ID' --output-dir youtube-research/videos/custom-name
python3 youtube-research/scripts/collect_video_research.py 'https://www.youtube.com/watch?v=VIDEO_ID' --force-stt
```

If the spoken language is obvious and important, pass `--lang <code>`. Otherwise let STT auto-detect.
Language resolution priority is:
- explicit `--lang`
- video `defaultAudioLanguage`
- video `defaultLanguage`
- STT auto-detect

## Output contract

The script writes a folder under `youtube-research/videos/<video-title>--<video_id>/` containing:

- `video.json`: video metadata and counts
- `transcript.json`: structured transcript segments when available
- `transcript.txt`: plain transcript text when available
- `comments.json`: top-level comments plus replies
- `summary.json`: compact metrics and extracted candidates
- `report.md`: human-readable research report
- `transcript_debug.json`: chunk-level STT debug data when audio fallback runs
- `ai_insights.json`: DeepSeek/OpenRouter insight extraction output when available

For Instagram inputs, `comments.json` will usually be empty and the report will
note that the platform is being used only for transcript-driven research.

## How to use the output

- Read `report.md` first.
- Use `summary.json` when another script or agent needs structured signals.
- Mine `comments.json` directly only when you need exact phrasing, author names, or thread context.
- Read `transcript_debug.json` when the audio fallback transcript needs auditing by chunk.
- If the task is editorial, convert the report into:
  - new blog post angles
  - follow-up video ideas
  - FAQ sections
  - objections to address
  - concrete user language to reuse in titles or summaries
  - complementary learning points that the audience surfaced beyond the original video

## Interpretation rules

- Prefer viewer questions and friction points over generic praise.
- Separate transcript-derived themes from comment-derived themes.
- Treat repeated phrasing as audience vocabulary, not final copy.
- Use OpenRouter STT for raw speech-to-text and reserve DeepSeek for cleanup and research synthesis.
- Treat the comments as a second layer of teaching material: what they clarify, contest, extend, or request beyond the original video.
- If transcript is unavailable even after fallback, do not fill the gap with fabricated summary. Base findings on comments and video metadata only.

## Relevant files

- `youtube-research/scripts/collect_video_research.py`
- `.env`
- `youtube-research/videos/`
