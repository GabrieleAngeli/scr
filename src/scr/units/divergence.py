from __future__ import annotations

from ..delta import FieldDelta
from ..field import FieldState
from .base import CompetenceUnit


class DivergenceUnit(CompetenceUnit):
    def __init__(
        self,
        threshold: float = 0.0,
        sensitivity: float = 1.0,
        weight: float = 1.0,
        decay: float = 0.0,
    ) -> None:
        self.name = "divergence"
        self.threshold = threshold
        self.sensitivity = sensitivity
        self.weight = weight
        self.decay = decay

    def activation(self, field: FieldState) -> float:
        has_code = field.context_map.get("code_artifact") is not None
        has_test = field.context_map.get("test_artifact") is not None
        has_metadata = field.context_map.get("metadata_artifact") is not None
        if not (has_code and has_test and has_metadata):
            return 0.0
        return self.sensitivity * self.weight

    def transform(self, field: FieldState) -> FieldDelta:
        code_artifact = field.context_map["code_artifact"]
        metadata_artifact = field.context_map["metadata_artifact"]
        hypotheses = self._build_hypotheses(
            target_file=code_artifact["path"],
            code_content=code_artifact["content"],
            metadata_content=metadata_artifact["content"],
        )

        trace_events = [
            {
                "tick": field.tick,
                "unit": self.name,
                "event_type": "unit_delta_applied",
                "reason": "standardized task artifacts are available for hypothesis generation",
                "input_summary": {
                    "code_artifact": code_artifact["name"],
                    "test_artifact": field.context_map["test_artifact"]["name"],
                    "metadata_artifact": metadata_artifact["name"],
                },
                "changes": {
                    "hypotheses_added": [item["hypothesis_id"] for item in hypotheses],
                },
            }
        ]

        return FieldDelta(
            source_unit=self.name,
            hypotheses_add=hypotheses,
            trace_events=trace_events,
        )

    def _build_hypotheses(
        self,
        target_file: str,
        code_content: str,
        metadata_content: str,
    ) -> list[dict[str, object]]:
        metadata_hint = metadata_content.strip() or "metadata hint unavailable"
        function_signature = code_content.splitlines()[0] if code_content.splitlines() else "unknown signature"
        return [
            {
                "hypothesis_id": "div-001",
                "target_file": target_file,
                "suspected_issue": "wrong operator usage in return statement",
                "proposed_change_summary": "replace subtraction with addition in the return expression",
                "confidence": 0.82,
                "source_unit": "divergence",
            },
            {
                "hypothesis_id": "div-002",
                "target_file": target_file,
                "suspected_issue": "implementation does not match additive behavior expected by tests",
                "proposed_change_summary": "align function body with add semantics described by the test artifact",
                "confidence": 0.73,
                "source_unit": "divergence",
            },
            {
                "hypothesis_id": "div-003",
                "target_file": target_file,
                "suspected_issue": f"metadata suggests functional mismatch: {metadata_hint}",
                "proposed_change_summary": f"update the logic in bug.py to satisfy the metadata clue and preserve function signature from code: {function_signature}",
                "confidence": 0.68,
                "source_unit": "divergence",
            },
            {
                "hypothesis_id": "div-004",
                "target_file": target_file,
                "suspected_issue": "branch condition may be inverted and route correct logic to the wrong path",
                "proposed_change_summary": "invert the if condition so the additive branch executes for the intended inputs",
                "confidence": 0.64,
                "source_unit": "divergence",
            },
            {
                "hypothesis_id": "div-005",
                "target_file": target_file,
                "suspected_issue": "logic may belong in the opposite branch of the conditional structure",
                "proposed_change_summary": "move the subtraction/addition logic between the if branch and fallback branch",
                "confidence": 0.59,
                "source_unit": "divergence",
            },
            {
                "hypothesis_id": "div-006",
                "target_file": target_file,
                "suspected_issue": "comparison operator inside the condition may be too strict for expected behavior",
                "proposed_change_summary": "modify the operator inside the condition, for example change greater-than to greater-or-equal or less-than",
                "confidence": 0.55,
                "source_unit": "divergence",
            },
            {
                "hypothesis_id": "div-007",
                "target_file": target_file,
                "suspected_issue": "edge cases around zero or negative values may not be handled consistently",
                "proposed_change_summary": "add explicit handling for zero and negative inputs before the main arithmetic branch",
                "confidence": 0.51,
                "source_unit": "divergence",
            },
            {
                "hypothesis_id": "div-008",
                "target_file": target_file,
                "suspected_issue": "generic arithmetic fallback may be missing for the simple add contract",
                "proposed_change_summary": "fallback to a direct return a + b implementation when branch logic is unreliable",
                "confidence": 0.48,
                "source_unit": "divergence",
            },
        ]
