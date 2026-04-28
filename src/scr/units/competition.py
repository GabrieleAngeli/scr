from __future__ import annotations

import re

from ..delta import FieldDelta
from ..field import FieldState
from .base import CompetenceUnit


class CompetitionUnit(CompetenceUnit):
    def __init__(
        self,
        threshold: float = 0.0,
        sensitivity: float = 1.0,
        weight: float = 1.0,
        decay: float = 0.0,
        max_active_hypotheses: int = 2,
    ) -> None:
        self.name = "competition"
        self.threshold = threshold
        self.sensitivity = sensitivity
        self.weight = weight
        self.decay = decay
        self.max_active_hypotheses = max_active_hypotheses

    def activation(self, field: FieldState) -> float:
        if not field.hypothesis_pool:
            return 0.0
        return self.sensitivity * self.weight

    def transform(self, field: FieldState) -> FieldDelta:
        code_artifact = field.context_map.get("code_artifact") or {}
        code_content = str(code_artifact.get("content", ""))
        ranked = sorted(
            (self._score_hypothesis(hypothesis, code_content) for hypothesis in field.hypothesis_pool),
            key=lambda hypothesis: float(hypothesis.get("score", 0.0)),
            reverse=True,
        )

        updated_hypotheses: list[dict[str, object]] = []
        active_hypotheses: list[str] = []
        pruned_hypotheses: list[str] = []

        for index, hypothesis in enumerate(ranked):
            updated = dict(hypothesis)
            if index < self.max_active_hypotheses:
                updated["status"] = "active"
                active_hypotheses.append(str(updated["hypothesis_id"]))
            else:
                updated["status"] = "pruned"
                pruned_hypotheses.append(str(updated["hypothesis_id"]))
            updated_hypotheses.append(updated)

        trace_events = [
            {
                "tick": field.tick,
                "unit": self.name,
                "event_type": "unit_delta_applied",
                "reason": "hypothesis_pool is available for score-based competition",
                "input_summary": {
                    "hypothesis_count": len(field.hypothesis_pool),
                    "max_active_hypotheses": self.max_active_hypotheses,
                },
                "changes": {
                    "active_hypotheses": active_hypotheses,
                    "pruned_hypotheses": pruned_hypotheses,
                },
            }
        ]

        return FieldDelta(
            source_unit=self.name,
            hypotheses_replace=updated_hypotheses,
            context_updates={"active_hypotheses": active_hypotheses},
            trace_events=trace_events,
        )

    def _score_hypothesis(self, hypothesis: dict[str, object], code_content: str) -> dict[str, object]:
        updated = dict(hypothesis)
        confidence = float(updated.get("confidence", 0.0))
        suspected_issue = str(updated.get("suspected_issue", "")).lower()
        summary = str(updated.get("proposed_change_summary", "")).lower()

        score = confidence
        if self._contains_arithmetic(code_content):
            if any(token in suspected_issue or token in summary for token in ("operator", "addition", "subtraction", "arithmetic", "return a + b")):
                score += 0.35
            if any(token in suspected_issue or token in summary for token in ("condition", "branch", "greater-than", "greater-or-equal", "less-than")):
                score += 0.15

        issue_terms = self._extract_terms(suspected_issue)
        if issue_terms and any(term in code_content.lower() for term in issue_terms):
            score += 0.25

        if any(token in summary for token in ("replace", "invert", "change greater-than", "direct return a + b", "fallback to a direct return a + b")):
            score += 0.20
        if "invert the if condition" in summary:
            score += 0.08
        if "modify the operator inside the condition" in summary:
            score -= 0.05
        if any(token in summary for token in ("align function body", "update the logic", "move the subtraction/addition logic")):
            score -= 0.10
        if any(token in suspected_issue or token in summary for token in ("generic", "fallback", "unreliable")):
            score -= 0.12

        updated["score"] = round(score, 4)
        return updated

    @staticmethod
    def _contains_arithmetic(code_content: str) -> bool:
        return any(operator in code_content for operator in ("+", "-", "*", "/"))

    @staticmethod
    def _extract_terms(text: str) -> set[str]:
        return {
            term
            for term in re.findall(r"[a-z][a-z\\-]+", text)
            if len(term) > 3 and term not in {"branch", "logic", "input", "values", "expected"}
        }
