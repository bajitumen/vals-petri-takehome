"""Load Inspect .eval logs from Petri runs into tidy DataFrames.

scores_df: one row per (log, sample, epoch, dimension) with the judge score.
usage_df:  one row per (log, sample, epoch, role) with tokens and $ cost.

Three failure modes make Petri emit plausible-looking scores (all 1s) that
aren't measurements, so each is flagged and `valid` is False for any of them:
  - judge_failed:    the judge's output didn't parse; Petri filled in defaults
  - empty_audit:     the audit record is empty, so the judge scored nothing
  - auditor_refused: the auditor's safety filter stopped a majority of its turns,
                     so the scenario was never actually run against the target
"""

from pathlib import Path

import pandas as pd
import yaml
from inspect_ai.log import list_eval_logs, read_eval_log
from inspect_ai.model import ModelUsage

JUDGE_FAILED = "Failed to parse judge's response"
COSTS_FILE = Path(__file__).resolve().parents[1] / "model_costs.yaml"


def _short(model: str | None) -> str | None:
    return model.split("/", 1)[-1] if model else model


def _role_models(log) -> dict[str, str]:
    roles = log.eval.model_roles or {}
    # A role can be bound to a list of models; Petri uses one per role.
    return {role: (cfg[0] if isinstance(cfg, list) else cfg).model for role, cfg in roles.items()}


def _load_costs() -> dict:
    return yaml.safe_load(COSTS_FILE.read_text()) if COSTS_FILE.exists() else {}


def _cost(model: str, usage, costs: dict) -> float | None:
    if usage.total_cost is not None:
        return usage.total_cost
    price = costs.get(model)
    if price is None:
        return None
    return (
        usage.input_tokens * price["input"]
        + usage.output_tokens * price["output"]
        + (usage.input_tokens_cache_write or 0) * price["input_cache_write"]
        + (usage.input_tokens_cache_read or 0) * price["input_cache_read"]
    ) / 1_000_000


def _usage_from_events(sample) -> dict[tuple[str, str], ModelUsage]:
    """Sum token usage per (role, model) over the sample's model-call events."""
    totals: dict[tuple[str, str], ModelUsage] = {}
    for e in sample.events or []:
        if e.event != "model" or e.output is None or e.output.usage is None:
            continue
        key = (e.role or "unknown", e.model)
        totals[key] = totals[key] + e.output.usage if key in totals else e.output.usage
    return totals


def _audit_event_count(sample) -> int:
    return sum(len(v) for k, v in (sample.store or {}).items() if "AuditStore" in k and k.endswith(":events"))


def _auditor_filtered_share(sample) -> float:
    turns = [e for e in sample.events or [] if e.event == "model" and e.role == "auditor" and e.output]
    if not turns:
        return 0.0
    return sum(e.output.stop_reason == "content_filter" for e in turns) / len(turns)


def _prefill_used(sample) -> bool:
    """True if any target call ended on an auditor-written assistant message (Petri's prefill)."""
    return any(
        e.event == "model" and e.role == "target" and e.input and e.input[-1].role == "assistant"
        for e in sample.events or []
    )


def _judge_served_by(sample) -> list[str]:
    """Models that actually served judge calls (differs from the requested judge if a fallback fired)."""
    return sorted({e.output.model for e in sample.events or [] if e.event == "model" and e.role == "judge" and e.output and e.output.model})


def load_logs(log_dir: str | Path = "logs", task: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    costs = _load_costs()
    score_rows, usage_rows = [], []

    for info in list_eval_logs(str(log_dir)):
        log = read_eval_log(info)
        if task and log.eval.task.split("/")[-1] != task:
            continue
        if log.status != "success" and not log.samples:
            continue
        roles = _role_models(log)
        base = {
            "log": Path(info.name).name,
            "task": log.eval.task.split("/")[-1],
            "target": _short(roles.get("target")),
            "auditor": _short(roles.get("auditor")),
            "judge": _short(roles.get("judge")),
        }

        for s in log.samples or []:
            tags = (s.metadata or {}).get("tags", [])
            row = {
                **base,
                "sample_id": str(s.id),
                "epoch": s.epoch,
                "tags": tags,
                "primary_tag": tags[0] if tags else "untagged",
                "error": s.error.message if s.error else None,
                "limit": s.limit.type if s.limit else None,
                "empty_audit": _audit_event_count(s) == 0,
                "auditor_filtered_share": _auditor_filtered_share(s),
                "prefill_used": _prefill_used(s),
                "judge_served_by": ",".join(_judge_served_by(s)),
            }
            row["auditor_refused"] = row["auditor_filtered_share"] > 0.5
            usage_by_role = _usage_from_events(s)
            judges = [m for (r, m) in usage_by_role if r == "judge"]
            if judges:
                # Re-scored logs keep the original judge in the header; events are authoritative.
                row["judge"] = _short(judges[-1])
            for (role, model), usage in usage_by_role.items():
                usage_rows.append(
                    {
                        **row,
                        "role": role,
                        "model": _short(model),
                        "input_tokens": usage.input_tokens,
                        "output_tokens": usage.output_tokens,
                        "cache_read": usage.input_tokens_cache_read or 0,
                        "cache_write": usage.input_tokens_cache_write or 0,
                        "cost": _cost(model, usage, costs),
                    }
                )

            for scorer_name, score in (s.scores or {}).items():
                if not isinstance(score.value, dict):
                    continue
                failed = score.answer == JUDGE_FAILED
                valid = not (failed or row["empty_audit"] or row["auditor_refused"] or row["error"])
                for dim, val in score.value.items():
                    score_rows.append(
                        {
                            **row,
                            "scorer": scorer_name,
                            "dimension": dim,
                            "score": pd.to_numeric(val, errors="coerce"),
                            "judge_failed": failed,
                            "valid": valid,
                        }
                    )

    return pd.DataFrame(score_rows), pd.DataFrame(usage_rows)
