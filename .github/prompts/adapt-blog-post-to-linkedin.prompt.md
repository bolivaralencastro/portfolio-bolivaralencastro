---
name: "adapt-blog-post-to-linkedin"
description: "Adapt a portfolio blog post into a concise LinkedIn post while keeping the site as the canonical version."
agent: "Blog Editor"
argument-hint: "[post path or url] [tone: direct, personal, incisive, etc.]"
---

Adapt a portfolio blog post into a LinkedIn post.

Use:

- [AGENTS.md](../../AGENTS.md)
- [portfolio-editorial skill](../skills/portfolio-editorial/SKILL.md)

Rules:

- the website remains the canonical long-form version
- keep the LinkedIn post concise unless the user explicitly asks otherwise
- extract the root idea, not a changelog of details
- mention relevant people, companies, products, and events if they matter to the point
- when appropriate, point back to the canonical URL at the end
- avoid generic engagement bait and generic AI hype language

Output:

- one strong default version
- optionally one sharper alternative if the user seems undecided on tone
