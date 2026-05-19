---
name: portfolio-notes-editorial
description: Create, classify, revise, and publish short notes for this static portfolio. Use when the user sends a phrase, paragraph, rough idea, commented link, video, site, image, audio, video, group of photos, or unfinished thought that should become a complete feed item in now.html rather than a standalone blog post.
argument-hint: "[raw note input, link, media, photos, draft idea, or feed update request]"
user-invocable: true
---

# Portfolio Notes Editorial

Use this skill when turning raw inputs into notes for the portfolio feed.

## Core idea

Notes are complete feed items published on `now.html`, usually inside
`Em foco` or `Em maturação`.
They do not get their own page. Each note must be readable in full in the
feed and must have a stable anchor permalink.

Use notes for:

- a short phrase or paragraph
- a rough idea to deepen later
- a commented link to a site, article, tool, repository, post, or video
- one image, audio, or video with commentary
- a group of photos converted into a carousel
- a small observation that is not yet a blog post

Suggest a blog post only when the input already has a complete argument,
multiple sections, or enough evidence to become long-form.

## Before editing

Read:

- [AGENTS.md](../../../AGENTS.md)
- [README.md](../../../README.md)
- [blog-html.instructions.md](../../instructions/blog-html.instructions.md) only if the note should become a blog post
- [portfolio-editorial/references/editorial-voice.md](../portfolio-editorial/references/editorial-voice.md) when rewriting or tightening tone
- [references/note-patterns.md](./references/note-patterns.md) when adding or changing note HTML

## Classification

Classify the input before writing:

- `thought`: phrase, paragraph, intuition, draft idea
- `link`: URL with commentary, including a website, article, video, repo, tool, or social post
- `image`: one image plus optional text
- `carousel`: multiple photos/images that should be shown as a grouped sequence
- `audio`: audio file or transcript with optional player
- `video`: video file, external video link, or embed with commentary
- `seed`: incomplete idea that should keep its unfinished quality
- `blog-candidate`: should probably become a full post instead of a note

If the user asks to publish as a note, do not overrule them unless the result
would be incoherent or too large for the feed.

## Writing rules

- Preserve the note scale. Do not inflate a note into an essay.
- Keep the authorial voice direct, precise, and slightly essayistic.
- Preserve incompleteness when the input is a seed.
- Add only enough context for the note to stand alone in the feed.
- For links, explain why the link matters, not just what it is.
- For videos, identify the idea, question, or tension worth saving.
- For groups of photos, write a short caption for the carousel as a whole and concise alt text per image.
- Use concrete nouns and tools instead of generic abstractions.
- Avoid formulaic contrast structures such as `menos X, mais Y` and `não foi X, foi Y`.

## HTML requirements

Each note is an `article.h-entry` with:

- stable `id`, e.g. `nota-2026-05-19-contexto-ia`
- `time.dt-published`
- complete note content inside `.e-content`
- visible `a.u-url` permalink pointing to `/now.html#<id>`
- one or more `p-category` tags when useful

Use media classes from [references/note-patterns.md](./references/note-patterns.md).

For a commented URL:

- include the source link in the content
- use `u-bookmark-of` for bookmarked articles/sites/tools/repos
- use `u-video` or normal link markup for video, depending on whether it is embedded or just referenced

For a group of photos:

- create one note
- render a carousel/group inside the note, not multiple notes
- keep the photo group self-contained with captions and alt text

## Asset rules

- Store note assets in `assets/images/notes/<note-id>/` when the site starts using note media.
- Prefer `webp` for images used on the site.
- Keep original source images only when useful for future edits.
- Do not place large source dumps directly in the public path unless intentionally retained.

## Workflow

1. Decide whether the input is a note, carousel, commented link, media note, seed, or blog candidate.
2. Add the note to `now.html`, choosing `Em foco` for active work and `Em maturação` for seeds that may later become posts or projects.
3. Create a stable note id using date + short slug.
4. Add the note near the top of the feed in reverse chronological order.
5. Preserve all content in the feed; do not create a standalone note page.
6. If adding media, place assets in the appropriate note folder and use accessible alt text/captions.
7. Run:

```bash
python3 scripts/build_site_metadata.py
python3 scripts/validate_site.py
```

## Do not

- Do not turn every note into a blog post.
- Do not create one page per note.
- Do not hide the full note behind a preview/read-more pattern.
- Do not embed remote media when a simple cited link is more durable.
- Do not add frameworks, CMS layers, or client-side feed machinery.
