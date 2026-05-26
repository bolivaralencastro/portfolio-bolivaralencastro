---
name: "new-note"
description: "Create a new portfolio note for the Now page from a topic, rough idea, link, or media."
agent: "Note Editor"
argument-hint: "[topic, rough note, link, image, audio, video, and optional tone]"
---

Create a new `Now` note for this portfolio.

Before editing, inspect:

- [AGENTS.md](../../AGENTS.md)
- [README.md](../../README.md)
- [portfolio-notes-editorial skill](../skills/portfolio-notes-editorial/SKILL.md)

Process:

1. Assume the request is for a note in `content/notes/*.md`, not a direct edit to `now.html`.
2. Infer a concise title, category, and stable slug from the material provided.
3. Create `content/notes/YYYY-MM-DD-slug.md` with the lightest complete front matter needed.
4. Write the body in Markdown and use supported media shortcodes when needed.
5. Remember that published notes keep `now.html` as editorial entry point but also generate `notes/YYYY-MM-DD-slug.html` and enter the paginated archive in `notes/index.html` and `notes/page/N.html`.
6. Prefer direct publication to `origin/main` with the wrapper script:
   ```bash
   python3 scripts/note.py new "Titulo da nota" --body "Texto da nota" --direct-main
   ```
7. Use the local-branch flow only if the user explicitly asks not to publish to `main` yet.
8. If the note needs manual editing or extra assets, regenerate and validate:
   ```bash
   python3 scripts/build_site_metadata.py
   python3 scripts/validate_site.py
   ```
9. Keep the note concise, self-contained, and aligned with the portfolio voice.
10. Escalate to a blog-post suggestion only if the material is clearly too large for a note.

If key information is missing, ask only for the smallest missing detail.
