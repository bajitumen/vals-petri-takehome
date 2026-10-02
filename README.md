# Petri Research Take-Home

> **Report (≈1 page).** Fill in once results are in. Keep claims tied to a number, a CI, or a quoted transcript.

## TL;DR
_TODO: one sentence per part: who wins Part A and on what; what Part B elicited and how often._

## Part A: GPT-5 Mini vs Claude Haiku 4.5 on Petri's default suite

**Setup.** _TODO: N seeds (stratified across 31 primary tags) × epochs × 2 targets; auditor = …, judge = …, max_turns = …; total cost $…_

**Why these models.** _TODO: auditor/judge choice and rationale (capability vs. cost, and same-family bias, since both judge candidates share a family with one target)._

**Results.** _TODO: forest plot (`figures/part_a_forest.png`), headline dimensions with paired mean difference, 95% CI, BH-adjusted p._

**Robustness.** _TODO: second-judge agreement (`figures/judge_agreement.csv`), whether the target gap survives a judge swap; audit-quality checks (auditor_failure, scenario_realism) similar across targets; eval_awareness._

**Qualitative.** _TODO: 2–3 transcript excerpts that explain the numbers (or contradict them)._

## Part B: _behavior name_

**Behavior & motivation.** _TODO_

**Design.** _TODO: seeds (`part_b/instructions.json`), dimensions/rubrics (`part_b/dimensions.json`), any auditor/judge prompt or tool changes, and how you iterated._

**Results.** _TODO_

## Limitations
_TODO: sample size, judge reliability, single auditor, stochastic audits, budget-driven choices._

---

## Repo layout

```
src/vals_petri/tasks.py      Inspect tasks: petri_subset (Part A), custom_audit (Part B)
src/vals_petri/scorers.py    Petri judge with file-based args, for re-judging logs
analysis/load.py             .eval logs -> tidy scores / per-role usage+cost DataFrames
analysis/part_a.py           paired stats (Wilcoxon, bootstrap CI, BH-FDR) + forest plot
analysis/judge_agreement.py  judge-vs-judge agreement and target-gap stability
analysis/cost.py             spend so far + projection for a planned run
scripts/config.sh            model roles and run limits (one place to change them)
scripts/pilot.sh | run_part_a.sh | run_part_b.sh | rejudge.sh
part_b/                      custom seed instructions + judge dimensions
model_costs.yaml             $/Mtok per model (verify before trusting totals)
```

Petri is pinned to `meridianlabs-ai/inspect_petri@f02b3ec` (branch `petri-v2`).

## Running it

```bash
uv sync --extra dev
cp .env.example .env            # add OPENAI_API_KEY and ANTHROPIC_API_KEY
set -a; source .env; set +a

N=6 ./scripts/pilot.sh          # ~$/seed per target, then a projection for the full run
N=8 SEED=0 ./scripts/run_part_a.sh   # 8 stratified seeds per target, pilot seeds held out; runs analysis at the end
JUDGE2=openai/gpt-6.1-sol ./scripts/rejudge.sh logs/*petri-subset*.eval
uv run python -m analysis.judge_agreement

LIMIT=3 ./scripts/run_part_b.sh # iterate on part_b/ prompts, then drop LIMIT to scale up

uv run inspect view             # Inspect log viewer
uv run petri view --log-dir outputs/part_a   # Petri transcript viewer (builds a Svelte app; needs Node)
uv run pytest -q
```

Model roles, `MAX_TURNS`, `EPOCHS`, and the per-sample `COST_LIMIT` default live in `scripts/config.sh`, and any of them can be overridden from the environment.

### Notes on the analysis
- **Pairing.** Both targets see the same seeds, so every comparison is paired by seed id. 69 of Petri's 181 default seeds have no id; `default_seeds()` assigns `idx<position>` so pairing is stable.
- **Judge failures are excluded, not averaged.** If the judge's output can't be parsed, Petri fills in default scores without any error. The loader flags these (`judge_failed`), and the analysis drops them and reports the count.
- **Polarity.** Most dimensions are higher = worse. `admirable`, `fun_or_funny`, and `scenario_realism` are higher = better. `auditor_failure`, `scenario_realism`, and `high_stakes_setting` describe the audit rather than the target, so they're reported as validity checks and excluded from the FDR family.
- **Re-judged logs** keep the original judge in their header. The loader reads the judge's identity and usage from the model-call events instead.
