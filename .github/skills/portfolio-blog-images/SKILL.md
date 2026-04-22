---
name: portfolio-blog-images
description: Prepare blog image assets for this portfolio. Use when the task involves combining exactly three images side by side, batching remaining source photos into triptychs, converting blog assets to webp, or replacing blog cover and card images with optimized outputs.
argument-hint: "[blog asset folder, source images, compose groups, webp conversion request]"
user-invocable: true
---

# Portfolio Blog Images

Use this skill when working on blog image assets in this repository.

## Before editing

Read:

- [AGENTS.md](../../../AGENTS.md)
- [README.md](../../../README.md)

## Primary tool

Use [`scripts/blog_image_workflow.py`](../../../scripts/blog_image_workflow.py) instead of rebuilding the image workflow ad hoc.

## Supported workflows

### Compose one triptych

Use when the user names exactly three files.

```bash
python3 scripts/blog_image_workflow.py compose-triptych \
  path/to/1.jpg path/to/2.jpg path/to/3.jpg \
  --output path/to/galeria-01.jpg
```

Behavior:

- applies EXIF orientation
- keeps the full image content
- resizes images to a common height
- avoids white bars by matching height before composing

### Batch remaining images in groups of three

Use when the user says “combine the rest three by three” and the directory only contains source images meant for that batch.

```bash
python3 scripts/blog_image_workflow.py batch-triptychs \
  --dir assets/images/blog/<slug>/originais \
  --output-prefix blog-galeria
```

Only use batch mode when the source directory is clean enough that sorted groups of three are actually the intended result.

### Convert to webp

Use after selecting covers, cards, or gallery images for publication.

```bash
python3 scripts/blog_image_workflow.py to-webp \
  assets/images/blog/<slug>/galeria-01.jpg \
  assets/images/blog/<slug>/galeria-02.jpg
```

Defaults:

- `--max-width 2400`
- `--quality 84`

For listing cards, keep `card.webp` at `960x540` through the existing editorial workflow or a dedicated crop/resize step before conversion.

## Output conventions

- Blog covers live at `assets/images/blog/<slug>/cover.webp`
- Listing cards live at `assets/images/blog/<slug>/card.webp`
- Combined gallery images should use stable names such as `galeria-01.jpg` or a project-specific prefix

## After asset work

If the edited assets affect published blog posts or listing cards, run:

- `python3 scripts/build_site_metadata.py`
- `python3 scripts/validate_site.py`

## Do not

- Do not crop editorial photos unless the user explicitly wants that
- Do not leave raw PNG/JPG covers in the published path unless they are intentionally kept as source material
- Do not batch arbitrary directories without confirming the sorting order makes sense for the post
