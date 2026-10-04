#!/usr/bin/env bash
# Re-score existing logs with a second judge (e.g. from the other model family)
# to measure judge agreement and same-family bias. Writes new logs to
# logs_rejudged/; originals are untouched.
#   JUDGE2=openai/gpt-6.1-sol ./scripts/rejudge.sh logs/<file>.eval [...]
#   DIMENSIONS=part_b/dimensions.json OUT_DIR=logs_part_b_rejudged ./scripts/rejudge.sh logs_part_b/*.eval
set -euo pipefail
cd "$(dirname "$0")/.."
: "${JUDGE2:=openai/gpt-6.1-sol}"
: "${OUT_DIR:=logs_rejudged}"
args=(--scorer src/vals_petri/scorers.py@judge)
# Absolute paths: inspect score resolves scorer arguments from the scorer file's directory.
[[ -n "${DIMENSIONS:-}" ]] && args+=(-S dimensions="$(cd "$(dirname "$DIMENSIONS")" && pwd)/$(basename "$DIMENSIONS")")
[[ -f "${JUDGE_PROMPT:-}" ]] && args+=(-S prompt="$(cd "$(dirname "$JUDGE_PROMPT")" && pwd)/$(basename "$JUDGE_PROMPT")")
mkdir -p "$OUT_DIR"
for log in "$@"; do
  uv run inspect score "$log" "${args[@]}" \
    --model-role "judge=$JUDGE2" \
    --action overwrite \
    --output-file "$OUT_DIR/$(basename "${log%.eval}")__judge-${JUDGE2//\//_}.eval"
done
