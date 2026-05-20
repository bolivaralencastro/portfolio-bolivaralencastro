---
name: youtube-learning-analysis
description: Analyze an existing YouTube research folder containing transcript, comments, and summary artifacts, and extract complementary learning from the audience discussion. Use when the goal is to understand what the comments add to the original video content: open questions, practical extensions, counterpoints, examples, and missing explanations.
---

# YouTube Learning Analysis

Use this skill after the raw YouTube research artifacts already exist on disk.

## Before running

- Confirm the research folder already contains at least:
  - `video.json`
  - `comments.json`
  - `summary.json`
  - `transcript.txt` or `transcript.json`
- Confirm `OPENROUTER_API_KEY` exists in the repository `.env`.
- Treat this as a second-pass analysis layer. Do not recollect comments or transcript unless the source artifacts are missing or stale.

## Default command

```bash
python3 youtube-research/scripts/analyze_learning.py youtube-research/videos/<video-title>--<video_id>
```

Useful variants:

```bash
python3 youtube-research/scripts/analyze_learning.py youtube-research/videos/<video-title>--<video_id> --prompt-file youtube-research/prompts/learning-analysis-v2.md
python3 youtube-research/scripts/analyze_learning.py youtube-research/videos/<video-title>--<video_id> --model deepseek/deepseek-chat
python3 youtube-research/scripts/analyze_learning.py youtube-research/videos/<video-title>--<video_id> --max-threads 40
```

## Output contract

The script writes:

- `ai_insights_learning.json`: structured complementary-learning analysis
- `final-learning-report.md`: human-readable final learning report

Keep previous files intact so prompt refinements can be compared across runs.

## Interpretation rules

- Prioritize what the comments teach beyond the original video.
- Separate agreement from real additive signal.
- Look for clarifications, missing steps, objections, practical use cases, and terminology friction.
- Prefer comment-backed evidence over abstract synthesis.
- Treat this as a learning aid first and an editorial aid second.

## Relevant files

- `youtube-research/scripts/analyze_learning.py`
- `youtube-research/prompts/learning-analysis-v2.md`
- `youtube-research/videos/`
