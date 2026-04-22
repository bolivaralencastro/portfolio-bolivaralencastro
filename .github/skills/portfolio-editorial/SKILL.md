---
name: portfolio-editorial
description: Create, revise, and publish blog posts or other editorial pages in this static portfolio. Use when the task involves new posts, revisions to existing essays, asset placement, links, summaries, or preparing content for publication.
argument-hint: "[blog post, project page, or editorial revision request]"
user-invocable: true
---

# Portfolio Editorial

Use this skill when working on editorial content in this repository.

## Before editing

Read:

- [AGENTS.md](../../../AGENTS.md)
- [README.md](../../../README.md)
- [blog-html.instructions.md](../../instructions/blog-html.instructions.md) when the task touches `blog/*.html`
- [references/editorial-voice.md](./references/editorial-voice.md) when writing, revising, or tightening tone

## Blog post workflow

1. Define the slug and create `blog/<slug>.html`.
2. Create or reuse an asset folder at `assets/images/blog/<slug>/`.
3. Add the minimum metadata required by the repository:
   - title
   - description
   - canonical
   - `og:image`
   - one `h1`
   - `.p-summary`
   - `time.dt-published`
   - JSON-LD `BlogPosting`
4. Link cited people, companies, products, events, and documentation when those references are public and stable.
5. If images are used, optimize them for the web and prefer `webp`.
6. Add contextual variation to the author card instead of reusing the same line everywhere.
7. Run:
   - `python3 scripts/build_site_metadata.py`
   - `python3 scripts/validate_site.py`

## Editing existing posts

- Preserve the established voice of the post.
- Remove repetition before adding explanation.
- Rewrite contrast templates instead of polishing them. If a sentence depends on `menos X, mais Y` or `não foi X, foi Y`, rebuild it from concrete description.
- If a new cover image is introduced, also prepare `card.webp` when the post should appear in listing contexts.
- If a new summary is stronger, update all places that depend on it: visible summary, meta description, social metadata, and JSON-LD.

## Social adaptation

If asked for LinkedIn or other social copy:

- Treat the site post as the canonical long-form version.
- Compress to one short paragraph unless the user asks otherwise.
- Keep the post rooted in the core idea, not in a changelog of details.

## Do not

- Do not hand-edit generated listing blocks.
- Do not add a framework or CMS to solve editorial tasks.
- Do not leave unoptimized image assets in the published path unless they are intentionally retained as source material.
