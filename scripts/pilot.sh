#!/usr/bin/env bash
# Small stratified pilot on both targets to measure $/seed before committing budget.
#   N=6 ./scripts/pilot.sh
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/config.sh
: "${N:=6}"
for target in $TARGETS; do
  run_target vals_petri/petri_subset "$target" -T n="$N" -T transcript_save_dir=./outputs/pilot --tags pilot
done
uv run python -m analysis.cost
