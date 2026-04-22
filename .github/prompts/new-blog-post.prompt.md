---
name: "new-blog-post"
description: "Create a new portfolio blog post from notes, links, images, and a rough thesis."
agent: "Blog Editor"
argument-hint: "[topic, notes, cited people, links, assets, and preferred tone]"
---

Create a new blog post for this portfolio.

Before editing, inspect:

- [AGENTS.md](../../AGENTS.md)
- [README.md](../../README.md)
- [portfolio-editorial skill](../skills/portfolio-editorial/SKILL.md)
- [blog-html instructions](../instructions/blog-html.instructions.md)

Process:

1. Extract the core thesis from the material provided before writing.
2. Propose or infer a clean slug that fits the existing naming style of the blog.
3. Create the post in `blog/<slug>.html` with all metadata and content.
4. Generate images automatically:
   ```bash
   # Check the visual prompts first
   python3 scripts/generate_post_images.py blog/<slug>.html --inline 2 --dry-run
   # Then generate
   python3 scripts/generate_post_images.py blog/<slug>.html --inline 2
   ```
5. Insert the printed `<img>` tags into the appropriate positions in the post body.
6. Add stable external links for cited people, products, companies, events, and docs.
7. Keep the writing concise, non-redundant, editorial, and aligned with the tone already present in the portfolio.
8. Vary the `Sobre o autor` card so it echoes the post context without losing the author's identity.
9. Regenerate metadata and validate:
   ```bash
   python3 scripts/build_site_metadata.py
   python3 scripts/validate_site.py
   ```

If key information is missing, ask only for the smallest set of missing details.
