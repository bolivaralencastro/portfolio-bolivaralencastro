# Portfolio Agent Notes

## Scope

These instructions apply to the whole repository. Use them for Codex, GitHub Copilot, Claude-based agents, and any other agent that reads workspace instructions.

## Project shape

- This portfolio is `HTML-first` and published as static files on GitHub Pages.
- Do not introduce frameworks, bundlers, CMS layers, or client-side complexity unless explicitly requested.
- Prefer editing existing handcrafted HTML patterns over inventing new structures.

## Public content rules

- Public pages must keep canonical URLs, description meta tags, Open Graph metadata, Twitter Card metadata, JSON-LD, and one clear `h1`.
- Blog posts live in `blog/<slug>.html`.
- Blog assets live in `assets/images/blog/<slug>/`.
- Project assets live in `assets/images/projects/<slug>/`.
- Link cited people, companies, products, and events when a stable public URL exists.
- The `Sobre o autor` card should keep the base identity intact but can vary its copy to echo the tone or subject of the post.

## Asset workflow

- Prefer `webp` for editorial images.
- For blog covers, keep `cover.webp` and `card.webp` in the post asset folder when possible.
- Recommended sizes:
  - `cover.webp`: around `1280-1600px` wide
  - `card.webp`: `960x540`
- Keep original source images only when they are useful as source material for future edits.

## Generated files

- Do not hand-edit `AUTO:` blocks in `index.html`, `blog.html`, or `projects.html`.
- Do not hand-edit feed and sitemap files unless debugging generation itself.
- This repository uses local generation as the source of truth. Do not rely on GitHub Actions to rewrite generated files after push.
- After changing public content, run:
  - `python3 scripts/build_site_metadata.py`
  - `python3 scripts/validate_site.py`

## Editorial stance

- Keep the writing precise, direct, and slightly essayistic.
- Avoid repetition, inflated conclusions, and generic AI boosterism.
- Prefer high-signal summaries over long explanation.
- Avoid formulaic contrast structures such as `menos X, mais Y`, `não foi X, foi Y`, or other opposition templates that flatten the sentence.
- Avoid abstract placeholders such as `pilha` when the concrete layers can be named directly.
- Treat events as reinforcement, clarification, or scale change when that is truer than discovery.
- Let the `Sobre o autor` card echo the post with a small contextual twist rather than defaulting to a fixed generic line.
- When adapting a post for social platforms, treat the site as the source of truth and point back to the canonical URL.

## Existing references

- Structural and SEO rules are documented in [README.md](./README.md).
- Reusable editorial workflow lives in [.github/skills/portfolio-editorial/SKILL.md](./.github/skills/portfolio-editorial/SKILL.md).
