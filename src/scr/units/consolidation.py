from __future__ import annotations

from ..delta import FieldDelta
from ..field import FieldState
from .base import CompetenceUnit


class ConsolidationUnit(CompetenceUnit):
    def __init__(
        self,
        threshold: float = 0.0,
        sensitivity: float = 1.0,
        weight: float = 1.0,
        decay: float = 0.0,
    ) -> None:
        self.name = "consolidation"
        self.threshold = threshold
        self.sensitivity = sensitivity
        self.weight = weight
        self.decay = decay

    def activation(self, field: FieldState) -> float:
        has_validation_results = "validation_results" in field.context_map
        has_empty_pool = len(field.hypothesis_pool) == 0
        if not (has_validation_results or has_empty_pool):
            return 0.0
        return self.sensitivity * self.weight

    def transform(self, field: FieldState) -> FieldDelta:
        validation_results = field.context_map.get("validation_results", [])

        if not field.hypothesis_pool:
            outcome = "FAILED_NO_VALID_HYPOTHESIS"
            selected_hypothesis = None
        else:
            passed_hypothesis = self._find_first_passed_hypothesis(field)
            if passed_hypothesis is not None:
                outcome = "SUCCESS"
                selected_hypothesis = passed_hypothesis
            elif validation_results:
                outcome = "REOPENED"
                selected_hypothesis = None
            else:
                outcome = "FAILED_NO_VALID_HYPOTHESIS"
                selected_hypothesis = None

        trace_events = [
            {
                "tick": field.tick,
                "unit": self.name,
                "event_type": "unit_delta_applied",
                "reason": "validation results are available for outcome consolidation",
                "input_summary": {
                    "validation_result_count": len(validation_results),
                    "hypothesis_count": len(field.hypothesis_pool),
                },
                "changes": {
                    "outcome": outcome,
                    "selected_hypothesis": selected_hypothesis,
                },
            }
        ]

        context_updates = {
            "outcome": outcome,
            "selected_hypothesis": selected_hypothesis,
        }

        return FieldDelta(
            source_unit=self.name,
            context_updates=context_updates,
            outcome=outcome,
            selected_hypothesis=selected_hypothesis,
            trace_events=trace_events,
        )

    @staticmethod
    def _find_first_passed_hypothesis(field: FieldState) -> dict[str, object] | None:
        for validation_result in field.context_map.get("validation_results", []):
            if not validation_result.get("passed"):
                continue
            hypothesis_id = validation_result.get("hypothesis_id")
            for hypothesis in field.hypothesis_pool:
                if hypothesis.get("hypothesis_id") == hypothesis_id:
                    return hypothesis
        return None
