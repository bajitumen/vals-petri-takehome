"""Petri's judge exposed with file-based arguments, so `inspect score` can
re-judge existing logs (e.g. with a second judge model) via `-S key=value`."""

import json
from pathlib import Path

from inspect_ai.scorer import Scorer, mean, scorer, stderr
from petri.scorers.judge import alignment_judge

import vals_petri.compat  # noqa: F401  (fixes judge config for Claude 4.7+)


@scorer(metrics={"*": [mean(), stderr()]})
def judge(dimensions: str | None = None, prompt: str | None = None) -> Scorer:
    """`dimensions`: JSON file of {name: rubric} (default: Petri's). `prompt`: judge prompt file."""
    kwargs = {}
    if dimensions:
        kwargs["dimensions"] = json.loads(Path(dimensions).read_text())
    if prompt:
        kwargs["prompt"] = Path(prompt).read_text()
    return alignment_judge(**kwargs)
