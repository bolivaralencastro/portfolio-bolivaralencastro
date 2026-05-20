# Carousel Reprocess Audit

Date: 2026-05-06

## Context

This audit reran the incomplete Instagram image posts listed in `data/instagram-research/carousel-reprocess-queue.tsv`.
The run used:

- exported Netscape cookies from local Chrome
- strict validation via `--require-carousel`
- per-item reruns through `scripts/enrich_social_image.py`

## Commands used

```bash
/usr/local/bin/python3 scripts/export_instagram_cookies.py data/instagram-research/instagram-cookies.txt
scripts/reprocess_instagram_carousels.sh data/instagram-research/instagram-cookies.txt
```

## Outcome

The cookies export succeeded, but none of the queued carousel posts could be recovered as full slide sets.
All affected items still failed at metadata/download stage and were blocked by strict validation.

## Failed items

- DX11nCCiPlM
- DX7DjZujNHc
- DX7ONeAkY7h
- DX9lAWVNff4
- DXh0iFmEiEN
- DXlzCb5gCdm
- DXotI-aDe_-
- DXowcZ6DNYn
- DXspVQNCRHp
- DXuT1tdDKvm
- DXzkj4TkaBa

## Error pattern

All items ended with the same effective blocker:

`Validação de carrossel exigida, mas metadados não confirmaram múltiplos slides. Use cookies válidos e tente novamente.`

Typical upstream extractor error:

`ERROR: [Instagram] <post_id>: No video formats found!`

## Conclusion

Exported browser cookies were not enough to unlock full carousel extraction for these posts.
These items should remain invalid for editorial synthesis until a collection method retrieves all carousel slides explicitly.
