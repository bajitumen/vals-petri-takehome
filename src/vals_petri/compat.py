"""Compatibility patch for Petri's judge on Claude 4.7+ models.

Petri's judge hardcodes `GenerateConfig(reasoning_tokens=10_000, reasoning_effort="high")`.
Claude 4.7 and later (e.g. claude-sonnet-5-5) reject `reasoning_tokens` outright, so
every judge call errors, and Petri silently falls back to default scores. A role config
can't unset a field (Inspect merges role config over the scorer's), so we drop
`reasoning_tokens` at the source and keep `reasoning_effort="high"`, which both
Anthropic and OpenAI reasoning models accept.
"""

from inspect_ai.model import GenerateConfig
from petri.scorers import judge as _judge


def _judge_config(**kwargs) -> GenerateConfig:
    if kwargs.get("reasoning_effort") is not None:
        kwargs.pop("reasoning_tokens", None)
    return GenerateConfig(**kwargs)


def apply() -> None:
    _judge.GenerateConfig = _judge_config


apply()
