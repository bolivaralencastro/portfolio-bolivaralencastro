---
name: portfolio-notes-editorial
description: Create, classify, revise, and publish short notes for this static portfolio. Use when the user sends a phrase, paragraph, rough idea, commented link, video, site, image, audio, video, group of photos, or unfinished thought that should become a complete note linked from now.html rather than a standalone blog post.
argument-hint: "[raw note input, link, media, photos, draft idea, or feed update request]"
user-invocable: true
---

# Portfolio Notes Editorial

Use this skill when turning raw inputs into notes for the portfolio feed.

## Core idea

Notes are complete feed items published from `content/notes/*.md`.
`now.html` remains the editorial entry point, but each published note also
gets its own page in `notes/` and enters the paginated archive.

Source of truth:

- note sources live in `content/notes/*.md`
- `now.html` is the entry surface for the newest notes
- each published note generates `notes/YYYY-MM-DD-slug.html`
- the complete archive lives in `notes/index.html` and `notes/page/N.html`
- `python3 scripts/build_site_metadata.py` regenerates the `AUTO:now-notes` block and the public note pages

Agents should write or edit note source files, not hand-edit the published
`now.html` block.

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
- [references/note-patterns.md](./references/note-patterns.md) when choosing media patterns, classes, and note structure

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

## Source format

Each note should be authored as one Markdown file in `content/notes/`,
preferably with a date-prefixed filename:

- `content/notes/2026-05-20-lendo-o-infinito-em-um-junco.md`
- `content/notes/2026-05-19-notas-como-superficie.md`

Front matter fields:

- `title`: optional but recommended
- `date`: required unless already encoded in the filename prefix
- `category`: optional, default `Nota`
- `classes`: optional, for cases like `note-seed`
- `status`: optional, `published` or `draft`

Example:

```md
---
title: Notas como superfície
date: 2026-05-19
category: Ideia em aberto
classes: note-seed
status: published
---

Estou testando o Now como superfície viva...
```

## Body format

Supported body patterns:

- regular Markdown paragraphs
- links, emphasis, lists, and blockquotes
- raw HTML when the note needs a custom fragment
- shortcodes for common media:

```md
{{ image src="/assets/images/now/exemplo.webp" alt="Descricao da imagem." width="1440" height="1280" }}
{{ audio src="/assets/audio/notas/exemplo.m4a" caption="Trecho de audio." }}
{{ video src="/assets/video/notas/exemplo.mp4" poster="/assets/images/now/exemplo-poster.webp" caption="Clip curto." }}
```

Use media classes and visual patterns from
[references/note-patterns.md](./references/note-patterns.md) as guidance for
what the generated HTML should feel like.

## Asset rules

- Store note assets in stable public folders such as `assets/images/now/`,
  `assets/audio/notas/`, or `assets/video/notas/` unless a more specific
  convention already exists.
- Prefer `webp` for images used on the site.
- Keep original source images only when useful for future edits.
- Do not place large source dumps directly in the public path unless intentionally retained.

## Workflow

1. Decide whether the input is a note, carousel, commented link, media note, seed, or blog candidate.
2. Create or update one file in `content/notes/`.
3. Prefer a stable date-prefixed filename with a short slug.
4. Write front matter and body in the lightest format that preserves the note well.
5. If adding media, place assets in the appropriate public folder and use accessible alt text/captions.
6. Preserve note scale; do not expand into blog-post structure unless needed.
7. Prefer the wrapper script with direct publication to `origin/main` when the task should publish immediately:

```bash
python3 scripts/note.py new "Titulo da nota" --body "Texto da nota" --direct-main
python3 scripts/note.py publish content/notes/YYYY-MM-DD-slug.md
```

Use the version without `--direct-main` only when the user explicitly wants to keep the note on the current local branch before publishing.

8. If working manually, run:

```bash
python3 scripts/build_site_metadata.py
python3 scripts/validate_site.py
```

## Do not

- Do not turn every note into a blog post.
- Do not hand-maintain note pages in `notes/`; they are generated.
- Do not hide the full note behind a preview/read-more pattern on the individual note page.
- Do not embed remote media when a simple cited link is more durable.
- Do not add frameworks, CMS layers, or client-side feed machinery.
- Do not hand-edit the generated `AUTO:now-notes` block in `now.html`.
