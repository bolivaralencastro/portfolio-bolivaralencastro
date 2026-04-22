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
