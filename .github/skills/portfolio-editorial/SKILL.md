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
2. Write the full post content and metadata.
   - Keep the long-form post precise, concrete, and structurally clear.
   - Preserve authorial intent without forcing intimate tone in every paragraph.
   - Prefer concrete observations and lived context over detached summaries.
3. Generate all images automatically:
   ```bash
   # Preview prompts first (no cost)
   python3 scripts/generate_post_images.py blog/<slug>.html --inline 2 --dry-run

   # Generate cover, card and inline images in parallel
   python3 scripts/generate_post_images.py blog/<slug>.html --inline 2
   ```
4. Insert the printed `<img>` tags into the post body at the appropriate positions.
5. If images were provided by the user (photos, screenshots), use `blog_image_workflow.py` to compose triptychs and convert to webp.
6. Link cited people, companies, products, events, and documentation when those references are public and stable.
7. Add contextual variation to the author card instead of reusing the same line everywhere.
8. Run:
   ```bash
   python3 scripts/build_site_metadata.py
   python3 scripts/validate_site.py
   ```
9. Publish to social channels in order:
   1) LinkedIn (preview + publish)
   2) Instagram (preview + publish)

## Social voice (derived text)

Scope: this voice applies to the second text written for LinkedIn/Instagram,
derived from the full post. It is not a requirement to make the full post
itself equally intimate.

Goal: unfold the long-form into a short social invitation that carries
personal intention, proximity, and continuity.

Rules:

- Keep it short, fluid, and direct.
- Sound like a person sharing work in progress, not a campaign announcement.
- Make the author's intention legible (`o que estou construindo`, `por que publico aqui`).
- Invite the reader into an ongoing space, not a one-off drop.
- Replace abstract claims with concrete nouns and actions.
- End with a clean CTA suited to each platform.

Quick self-check before publishing social copy:

- `desdobramento`: Does this read like a true unfolding of the full post, not a detached summary?
- `pessoalidade`: Is the author present as someone talking with people, not at them?
- `convite`: Is there a clear invitation to visit/read/follow the work?
- `fluidez`: Can the text be read in one breath without corporate phrasing?

## Image generation reference

`generate_post_images.py` reads the post HTML, uses a cheap text model to write contextual visual prompts, then generates all images in parallel via OpenRouter.

| Flag | Effect |
|------|--------|
| `--inline N` | Number of inline images (default: 2) |
| `--dry-run` | Shows prompts without generating images |
| `--only cover\|card\|inline` | Generate only one image type |

Output files land in `assets/images/blog/<slug>/` automatically.
Use `generate_image.py` (singular) only when you need a one-off image with a specific prompt.

## Publishing to LinkedIn (optional)

```bash
python3 scripts/linkedin_post.py              # latest post
python3 scripts/linkedin_post.py --dry-run    # preview
python3 scripts/linkedin_post.py --slug <slug>
```

Requires `LINKEDIN_ACCESS_TOKEN` in `.env`. If expired, run `linkedin_auth.py` first.

## Publishing to Instagram (optional)

```bash
python3 scripts/instagram_post.py              # latest post
python3 scripts/instagram_post.py --dry-run    # preview
python3 scripts/instagram_post.py --slug <slug>
```

Requires `INSTAGRAM_ACCESS_TOKEN` and `INSTAGRAM_USER_ID` in `.env`.
If expired, run `python3 scripts/instagram_auth.py` first.

Important: Instagram Graph API only accepts `JPG/PNG` by URL (`image_url`),
not `WEBP`. The `generate_post_images.py` workflow now generates `card.jpg`
automatically alongside `card.webp`.

## Full publication order (recommended)

```bash
# 1) Write/update post HTML
# 2) Generate images
python3 scripts/generate_post_images.py blog/<slug>.html --inline 2

# 3) Rebuild generated metadata and validate
python3 scripts/build_site_metadata.py
python3 scripts/validate_site.py

# 4) Publish to LinkedIn
python3 scripts/linkedin_post.py --dry-run --slug <slug>
python3 scripts/linkedin_post.py --slug <slug>

# 5) Publish to Instagram
python3 scripts/instagram_post.py --dry-run --slug <slug>
python3 scripts/instagram_post.py --slug <slug>
```

## Editing existing posts

- Preserve the established voice of the post.
- Remove repetition before adding explanation.
- Rewrite contrast templates instead of polishing them. If a sentence depends on `menos X, mais Y` or `não foi X, foi Y`, rebuild it from concrete description.
- If a new cover image is introduced, also prepare `card.webp` when the post should appear in listing contexts.
- If a new summary is stronger, update all places that depend on it: visible summary, meta description, social metadata, and JSON-LD.

## Social adaptation

If asked for LinkedIn or other social copy:

- Treat the site post as the canonical long-form version.
- Keep the post rooted in the core idea, not in a changelog of details.
- Default to short, direct invitations that sound personal and intentional.
- Make the reader feel invited into an ongoing body of work, not into a one-off announcement.

LinkedIn default:

- 1 to 3 short paragraphs.
- Tone: clear, personal, slightly informal, no corporate cadence.
- Include direct site CTA with full URL.
- Prefer explicit invitation to the author's own space/site.

Instagram default:

- 2 to 5 short lines.
- Tone: warmer and more informal than LinkedIn, still precise.
- Do not place URL in body as primary CTA; end with `link na bio` unless the user requests otherwise.
- Prioritize intimacy and continuity (`espaço que venho construindo`, `processo em andamento`, `o que venho testando`).
- Treat caption as conversation: less declarative broadcast, more personal sharing.

## Do not

- Do not hand-edit generated listing blocks.
- Do not add a framework or CMS to solve editorial tasks.
- Do not leave unoptimized image assets in the published path unless they are intentionally retained as source material.
