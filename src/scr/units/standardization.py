from __future__ import annotations

from ..delta import FieldDelta
from ..field import FieldState
from .base import CompetenceUnit


class StandardizationUnit(CompetenceUnit):
    def __init__(
        self,
        threshold: float = 0.0,
        sensitivity: float = 1.0,
        weight: float = 1.0,
        decay: float = 0.0,
    ) -> None:
        self.name = "standardization"
        self.threshold = threshold
        self.sensitivity = sensitivity
        self.weight = weight
        self.decay = decay

    def activation(self, field: FieldState) -> float:
        has_artifacts = bool(field.context_map.get("artifacts"))
        has_files = bool(field.context_map.get("files"))
        if not (has_artifacts and has_files):
            return 0.0
        return self.sensitivity * self.weight

    def transform(self, field: FieldState) -> FieldDelta:
        artifacts = field.context_map.get("artifacts", {})
        files = field.context_map.get("files", {})

        normalized_artifacts = {
            name: self._normalize_artifact(name, artifacts.get(name, ""), files.get(name))
            for name in ("bug.py", "test_bug.py", "meta.txt")
            if name in artifacts
        }

        code_artifact = normalized_artifacts.get("bug.py")
        test_artifact = normalized_artifacts.get("test_bug.py")
        metadata_artifact = normalized_artifacts.get("meta.txt")

        salience_updates: dict[str, float] = {}
        if code_artifact is None:
            salience_updates["missing_code_artifact"] = 1.0
        if test_artifact is None:
            salience_updates["missing_test_artifact"] = 1.0
        if metadata_artifact is None:
            salience_updates["missing_metadata_artifact"] = 1.0

        context_updates = {
            "normalized_artifacts": normalized_artifacts,
            "code_artifact": code_artifact,
            "test_artifact": test_artifact,
            "metadata_artifact": metadata_artifact,
        }

        trace_events = [
            {
                "tick": field.tick,
                "unit": self.name,
                "event_type": "unit_delta_applied",
                "reason": "context_map contains task artifacts to normalize",
                "input_summary": {
                    "artifact_names": sorted(artifacts.keys()),
                    "file_names": sorted(files.keys()),
                },
                "changes": {
                    "context_keys": sorted(context_updates.keys()),
                    "salience_updates": salience_updates,
                },
            }
        ]

        return FieldDelta(
            source_unit=self.name,
            context_updates=context_updates,
            salience_updates=salience_updates,
            trace_events=trace_events,
        )

    @staticmethod
    def _normalize_artifact(name: str, content: str, path: str | None) -> dict[str, object]:
        normalized_content = content.replace("\r\n", "\n").strip()
        return {
            "name": name,
            "path": path,
            "content": normalized_content,
            "line_count": len(normalized_content.splitlines()) if normalized_content else 0,
            "is_empty": normalized_content == "",
        }
