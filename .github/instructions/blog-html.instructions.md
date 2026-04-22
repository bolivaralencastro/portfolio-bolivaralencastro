---
name: "Blog HTML Conventions"
description: "Rules for writing and editing blog post HTML files in this portfolio."
applyTo: "blog/**/*.html"
---

# Blog HTML conventions

Apply the general workspace rules from [AGENTS.md](../../AGENTS.md).

- Keep exactly one strong `h1`, one visible summary, and one `time.dt-published`.
- Keep the body inside `.e-content`.
- Use section headings only when they sharpen the text.
- Prefer lean paragraphs over long explanatory blocks.
- Link cited people, organizations, products, events, and docs when the references are stable.
- Avoid redundant conclusions. Closing paragraphs should compress the argument, not restate the whole post.
- Avoid contrast templates such as `menos X, mais Y` and `não foi X, foi Y`.
- Avoid vague abstractions when the concrete layers, tools, or actions can be named.
- The author card may carry a small contextual twist, but should still read as part of the same authorial voice.
- Store images in `assets/images/blog/<slug>/` and use `webp` when possible.
- If the post becomes the newest entry, remember that `index.html`, `blog.html`, `feed.xml`, `feed.txt`, and `sitemap.xml` will change after regeneration.
