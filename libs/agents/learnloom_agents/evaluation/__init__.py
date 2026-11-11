"""Evaluating the agents: routing, tool use, task success, guardrails, grounding, speed and cost.

    python -m learnloom_agents.evaluation offline        # guardrails only; no server, no model
    python -m learnloom_agents.evaluation live ...        # the real app, as a student (see docs/agents.md)
"""

from learnloom_agents.evaluation.cases import Case, load_cases
from learnloom_agents.evaluation.metrics import CaseResult, check_case, summarize
from learnloom_agents.evaluation.trace import RunRecord, record_from_events

__all__ = ["Case", "CaseResult", "RunRecord", "check_case", "load_cases", "record_from_events", "summarize"]
