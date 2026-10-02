#!/usr/bin/env bash
# Part A: default seed suite on both targets, paired by seed.
#   N=60 ./scripts/run_part_a.sh          # stratified subset of 60 seeds
#   IDS=1,7,9 ./scripts/run_part_a.sh     # specific seeds
#   TAGS=sycophancy ./scripts/run_part_a.sh
#   (no vars)                             # all 181 seeds; check the pilot projection first
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/config.sh
# Pilot seeds are held out: the pilot's observations were formed on them, so the main
# sample must not reuse them (see notes/pilot_findings.md).
: "${EXCLUDE_IDS:=18,30,99,103,idx162,idx163}"
args=(-T transcript_save_dir=./outputs/part_a --tags part_a)
[[ -n "$EXCLUDE_IDS" ]] && args+=(-T exclude_ids="$EXCLUDE_IDS")
[[ -n "${N:-}" ]] && args+=(-T n="$N")
[[ -n "${IDS:-}" ]] && args+=(-T ids="$IDS")
[[ -n "${TAGS:-}" ]] && args+=(-T tags="$TAGS")
[[ -n "${SEED:-}" ]] && args+=(-T seed="$SEED")
for target in $TARGETS; do
  run_target vals_petri/petri_subset "$target" "${args[@]}"
done
uv run python -m analysis.part_a
