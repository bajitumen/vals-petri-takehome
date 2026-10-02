#!/usr/bin/env bash
# Part B: custom seeds + custom judge dimensions from part_b/.
#   LIMIT=3 ./scripts/run_part_b.sh    # iterate on prompts with a few seeds first
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/config.sh
args=(-T instructions=part_b/instructions.json -T dimensions=part_b/dimensions.json
      -T transcript_save_dir=./outputs/part_b --tags part_b)
[[ -f part_b/judge_prompt.md ]] && args+=(-T judge_prompt=part_b/judge_prompt.md)
[[ -f part_b/auditor_prompt.md ]] && args+=(-T auditor_system_message=part_b/auditor_prompt.md)
[[ -n "${LIMIT:-}" ]] && args+=(--limit "$LIMIT")
for target in $TARGETS; do
  run_target vals_petri/custom_audit "$target" "${args[@]}"
done
