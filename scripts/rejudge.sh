#!/usr/bin/env bash
# Re-score existing logs with a second judge (e.g. from the other model family)
# to measure judge agreement and same-family bias. Writes new logs to
# logs_rejudged/; originals are untouched.
#   JUDGE2=openai/gpt-6.1-sol ./scripts/rejudge.sh logs/<file>.eval [...]
#   DIMENSIONS=part_b/dimensions.json JUDGE2=... ./scripts/rejudge.sh logs/<part_b>.eval
set -euo pipefail
cd "$(dirname "$0")/.."
: "${JUDGE2:=openai/gpt-6.1-sol}"
args=(--scorer src/vals_petri/scorers.py@judge)
[[ -n "${DIMENSIONS:-}" ]] && args+=(-S dimensions="$DIMENSIONS")
[[ -f "${JUDGE_PROMPT:-}" ]] && args+=(-S prompt="$JUDGE_PROMPT")
mkdir -p logs_rejudged
for log in "$@"; do
  uv run inspect score "$log" "${args[@]}" \
    --model-role "judge=$JUDGE2" \
    --action overwrite \
    --output-file "logs_rejudged/$(basename "${log%.eval}")__judge-${JUDGE2//\//_}.eval"
done
