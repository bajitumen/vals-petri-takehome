#!/usr/bin/env bash
# Part B: custom seeds + custom judge dimensions from part_b/ (caseworker scenario).
#   IDS=tax-consent_claimed-pressure ./scripts/run_part_b.sh   # one seed, for a paid test audit
#   ./scripts/run_part_b.sh                            # all 12 seeds on both targets
set -euo pipefail
cd "$(dirname "$0")/.."
export INSPECT_LOG_DIR="${PART_B_LOG_DIR:-./logs_part_b}"   # keep Part B logs out of Part A's logs/
source scripts/config.sh
: "${PART_B_MAX_TURNS:=12}"   # client phase + investigator phase
MAX_TURNS="$PART_B_MAX_TURNS"
args=(-T instructions=part_b/instructions.json -T dimensions=part_b/dimensions.json
      -T prefill=false -T rollback=false -T resources_dir=part_b/resources
      -T transcript_save_dir=./outputs/part_b --tags part_b)
[[ -n "${IDS:-}" ]] && args+=(--sample-id "$IDS")
[[ -f part_b/judge_prompt.md ]] && args+=(-T judge_prompt=part_b/judge_prompt.md)
[[ -f part_b/auditor_prompt.md ]] && args+=(-T auditor_system_message=part_b/auditor_prompt.md)
[[ -n "${LIMIT:-}" ]] && args+=(--limit "$LIMIT")
for target in $TARGETS; do
  run_target vals_petri/custom_audit "$target" "${args[@]}"
done
