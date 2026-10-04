# Shared model choices. Override any of these from the environment, e.g.
#   AUDITOR=openai/gpt-5 ./scripts/run_part_a.sh
# Every model used must have a price in model_costs.yaml for --cost-limit to work.
: "${TARGETS:=openai/gpt-5-mini anthropic/claude-haiku-4-5-20251001}"
: "${AUDITOR:=anthropic/claude-sonnet-5}"   # no classifier refusals (see notes/pilot_findings.md)
: "${JUDGE:=anthropic/claude-sonnet-5-5}"
# If Sonnet 5.5's safety classifiers refuse a judge call, retry it on Sonnet 5 (no classifiers).
: "${JUDGE_FALLBACK:=claude-sonnet-5}"   # bare name: the only allowed_fallback_models entry
: "${AUDITOR_EFFORT:=medium}"   # auditor reasoning effort; Sonnet 5's default produced ~2x the pilot auditor's output
: "${MAX_TURNS:=15}"
: "${EPOCHS:=1}"
: "${COST_LIMIT:=}"             # optional per-sample $ cap (off by default)
: "${MAX_CONNECTIONS:=10}"
export INSPECT_LOG_DIR="${INSPECT_LOG_DIR:-./logs}"
# Inspect shells out to git; prefer the system git (an old Intel-only git in
# /usr/local/bin breaks this on some Apple Silicon Macs).
export PATH="/usr/bin:$PATH"

run_target() {
  # run_target <task> <target> [extra inspect args...]
  local task="$1" target="$2"; shift 2
  # --model sets Inspect's default model; Petri only uses the roles, but
  # --cost-limit needs a priced default model, so point it at the target.
  uv run inspect eval "$task" \
    --model "$target" \
    --model-role "auditor={model: $AUDITOR${AUDITOR_EFFORT:+, reasoning_effort: $AUDITOR_EFFORT}}" \
    --model-role "target=$target" \
    --model-role "judge={model: $JUDGE${JUDGE_FALLBACK:+, fallback_models: [$JUDGE_FALLBACK]}}" \
    ${COST_LIMIT:+--model-cost-config model_costs.yaml --cost-limit "$COST_LIMIT"} \
    --epochs "$EPOCHS" \
    --max-connections "$MAX_CONNECTIONS" \
    --max-retries 8 \
    --fail-on-error 0.2 \
    -T max_turns="$MAX_TURNS" \
    "$@"
}
