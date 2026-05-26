---
applyTo: "**"
---

# Portfolio Copilot Instructions

- This repository is a static `HTML-first` portfolio. Prefer simple HTML, CSS, and existing scripts over new abstractions.
- Follow the project-wide guidance in [AGENTS.md](../AGENTS.md) and the structural rules in [README.md](../README.md).
- When working on public content, preserve metadata quality, canonical URLs, JSON-LD, and image alts.
- Never hand-maintain generated listings, feed entries, or sitemap content when `scripts/build_site_metadata.py` can regenerate them.
- When asked to create or revise a `Now` note, write the source in `content/notes/*.md` and never hand-edit the generated `AUTO:now-notes` block in `now.html`.
- Treat `now.html` as the entry point for notes, but remember that published notes also generate pages in `notes/` and enter the paginated archive in `notes/index.html` and `notes/page/N.html`.
- Prefer `python3 scripts/note.py new ... --direct-main` when the task is to create/publish a new note from a short prompt or rough idea with minimum friction.
- Use the plain `python3 scripts/note.py new ...` flow only when the user explicitly wants the note to stay on the current local branch first.
- Run `python3 scripts/build_site_metadata.py` after public content changes.
- Run `python3 scripts/validate_site.py` before considering the task complete.
- Keep external links intentional and verifiable.
- Treat the portfolio website as the primary publication surface; social adaptations are secondary summaries.
- In editorial work, avoid formulaic contrast syntax and favor concrete nouns over vague shorthand.
