#!/usr/bin/env bash

set -u

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
QUEUE_FILE="$ROOT_DIR/data/instagram-research/carousel-reprocess-queue.tsv"

if [[ $# -lt 1 ]]; then
  echo "Usage: scripts/reprocess_instagram_carousels.sh /path/to/instagram-cookies.txt"
  echo "   or: scripts/reprocess_instagram_carousels.sh --browser chrome"
  exit 1
fi

COOKIES_FILE=""
COOKIE_BROWSER=""
PYTHON_BIN=${PYTHON_BIN:-python3}

if [[ "$1" == "--browser" ]]; then
  if [[ $# -lt 2 ]]; then
    echo "Missing browser name. Example: --browser chrome"
    exit 1
  fi
  COOKIE_BROWSER="$2"
else
  COOKIES_FILE="$1"
fi

if [[ -n "$COOKIES_FILE" && ! -f "$COOKIES_FILE" ]]; then
  echo "Cookies file not found: $COOKIES_FILE"
  exit 1
fi

if [[ ! -f "$QUEUE_FILE" ]]; then
  echo "Queue file not found: $QUEUE_FILE"
  exit 1
fi

FAILURES=0
TOTAL=0

while IFS=$'\t' read -r POST_ID SLIDES_CAPTURED IMAGE_SOURCE URL TITLE ARTIFACT_FOLDER || [[ -n "${POST_ID:-}" ]]; do
  [[ -z "${POST_ID:-}" ]] && continue
  [[ "$POST_ID" == \#* ]] && continue

  TOTAL=$((TOTAL + 1))
  echo
  echo "[$TOTAL] Reprocessing $POST_ID"
  echo "    URL: $URL"

  EXTRA_ARGS=()
  if [[ -n "$COOKIES_FILE" ]]; then
    EXTRA_ARGS+=(--cookies-file "$COOKIES_FILE")
  else
    EXTRA_ARGS+=(--use-browser-cookies --cookies-from-browser "$COOKIE_BROWSER")
  fi

  if ! "$PYTHON_BIN" "$ROOT_DIR/scripts/enrich_social_image.py" \
    --force \
    --require-carousel \
    "${EXTRA_ARGS[@]}" \
    --url "$URL"
  then
    echo "    FAILED: $POST_ID"
    FAILURES=$((FAILURES + 1))
  fi
done < "$QUEUE_FILE"

echo
echo "Done. Total: $TOTAL | Failures: $FAILURES"

if [[ $FAILURES -gt 0 ]]; then
  exit 1
fi