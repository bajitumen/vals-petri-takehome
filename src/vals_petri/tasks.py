"""Inspect tasks for the take-home.

- `petri_subset`: Petri's default seed suite (Part A), optionally narrowed to
  specific ids, tags, or a stratified sample so runs fit the $20 budget.
  Unlike passing `-T seed_instructions=...` to `petri/audit`, this keeps each
  seed's id and tags, which the analysis needs for per-category breakdowns.
- `custom_audit`: custom seed instructions + custom judge dimensions (Part B).
"""

import json
import random
from collections import defaultdict
from pathlib import Path

from inspect_ai import Task, task, task_with
from inspect_ai.dataset import Sample
from petri.scorers.judge import alignment_judge

import vals_petri.compat  # noqa: F401  (fixes judge config for Claude 4.7+)
from petri.solvers.auditor_agent import auditor_agent
from petri.solvers.prompts import AUDITOR_SYSTEM_PROMPT
from petri.tasks.petri import SEED_INSTRUCTIONS, audit


def _csv(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [v.strip() for v in str(value).split(",") if v.strip()]


def default_seeds() -> list[Sample]:
    """Petri's default seeds with a stable id on every sample.

    69 of the 181 defaults ship without an id; they get `idx<position>` so the
    same scenario can be paired across targets and runs.
    """
    samples = []
    for i, s in enumerate(SEED_INSTRUCTIONS):
        s = s.model_copy(deep=True)
        s.id = str(s.id) if s.id is not None else f"idx{i}"
        samples.append(s)
    return samples


def stratified_seed_ids(n: int, seed: int = 0, pool: set[str] | None = None) -> list[str]:
    """Pick `n` default seed ids, spread across primary tags (a seed's first tag).

    Groups are visited round-robin in a seeded shuffle, so the same (n, seed)
    always yields the same subset, and every category is represented before
    any category gets a second seed.
    """
    rng = random.Random(seed)
    groups: dict[str, list[str]] = defaultdict(list)
    for s in default_seeds():
        if pool is not None and str(s.id) not in pool:
            continue
        tags = (s.metadata or {}).get("tags") or ["untagged"]
        groups[tags[0]].append(str(s.id))
    for ids in groups.values():
        rng.shuffle(ids)
    order = sorted(groups)
    rng.shuffle(order)

    picked: list[str] = []
    total = sum(len(ids) for ids in groups.values())
    while len(picked) < min(n, total):
        for tag in order:
            if groups[tag] and len(picked) < n:
                picked.append(groups[tag].pop())
    return picked


def select_default_seeds(
    ids: str | list[str] | None = None,
    tags: str | list[str] | None = None,
    n: int | None = None,
    seed: int = 0,
    exclude_tags: str | list[str] | None = None,
    exclude_ids: str | list[str] | None = None,
) -> list[Sample]:
    """Filter the default suite: drop `exclude_tags` and `exclude_ids`, then explicit ids, then tags (any match), then n.

    Nothing is excluded by default, to stay on Petri's default suite. Prefill is
    handled in the analysis instead (see notes/pilot_findings.md).
    """
    samples = default_seeds()
    if drop := set(_csv(exclude_tags)):
        samples = [s for s in samples if not drop & set((s.metadata or {}).get("tags", []))]
    if held_out := set(_csv(exclude_ids)):
        samples = [s for s in samples if str(s.id) not in held_out]
    if id_list := _csv(ids):
        wanted = set(id_list)
        samples = [s for s in samples if str(s.id) in wanted]
    if tag_list := _csv(tags):
        wanted = set(tag_list)
        samples = [s for s in samples if wanted & set((s.metadata or {}).get("tags", []))]
    if n is not None:
        pool = {str(s.id) for s in samples}
        if not (id_list or tag_list):
            keep = set(stratified_seed_ids(n, seed, pool=pool))
            samples = [s for s in samples if str(s.id) in keep]
        else:
            samples = random.Random(seed).sample(samples, min(n, len(samples)))
    return samples


@task
def petri_subset(
    ids: str | None = None,
    tags: str | None = None,
    n: int | None = None,
    seed: int = 0,
    exclude_tags: str | None = None,
    exclude_ids: str | None = None,
    prefill: bool = True,
    max_turns: int = 30,
    transcript_save_dir: str = "./outputs/part_a",
) -> Task:
    """Petri's default audit, restricted to a subset of seed instructions.

    Defaults match Petri's default audit. `prefill=False` removes the auditor's prefill
    tool and `exclude_tags="prefill"` drops prefill seeds, for an ablation: prefill is a
    true continuation on Anthropic but a disownable prior turn on OpenAI.
    """
    base = audit(max_turns=max_turns, transcript_save_dir=transcript_save_dir)
    samples = select_default_seeds(
        ids=ids, tags=tags, n=n, seed=seed, exclude_tags=exclude_tags, exclude_ids=exclude_ids
    )
    if not samples:
        raise ValueError("No seed instructions matched the given ids/tags/n.")
    solver = auditor_agent(max_turns=max_turns, prefill=prefill, auditor_system_message=AUDITOR_SYSTEM_PROMPT)
    return task_with(base, dataset=samples, solver=solver, name="petri_subset")


def load_instructions(path: str | Path) -> list[Sample]:
    """Load seeds from JSON: a list of strings, or of {"id", "input", "tags"} objects."""
    items = json.loads(Path(path).read_text())
    samples = []
    for i, item in enumerate(items, start=1):
        if isinstance(item, str):
            item = {"input": item}
        samples.append(
            Sample(
                id=str(item.get("id", i)),
                input=item["input"],
                metadata={"tags": item.get("tags", [])},
            )
        )
    return samples


@task
def custom_audit(
    instructions: str = "part_b/instructions.json",
    dimensions: str = "part_b/dimensions.json",
    max_turns: int = 30,
    auditor_system_message: str | None = None,
    judge_prompt: str | None = None,
    transcript_save_dir: str = "./outputs/part_b",
) -> Task:
    """Custom seeds scored by the Petri judge on custom dimensions (Part B).

    `dimensions` is a JSON object of {dimension_name: rubric}. `judge_prompt`
    optionally points to a file replacing Petri's JUDGE_PROMPT; it must keep the
    `{dimensions_text}` and `{scores_list}` placeholders.
    """
    dims: dict[str, str] = json.loads(Path(dimensions).read_text())
    judge_kwargs = {"dimensions": dims}
    if judge_prompt:
        judge_kwargs["prompt"] = Path(judge_prompt).read_text()

    base = audit(
        max_turns=max_turns,
        transcript_save_dir=transcript_save_dir,
        auditor_system_message=auditor_system_message,
    )
    return task_with(
        base,
        dataset=load_instructions(instructions),
        scorer=alignment_judge(**judge_kwargs),
        name="custom_audit",
    )
