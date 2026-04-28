from __future__ import annotations

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
        ranked = sorted(
            field.hypothesis_pool,
            key=lambda hypothesis: float(hypothesis.get("confidence", 0.0)),
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
                "reason": "hypothesis_pool is available for confidence-based competition",
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
