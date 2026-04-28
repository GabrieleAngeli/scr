from __future__ import annotations

from pathlib import Path

from ..delta import FieldDelta
from ..field import FieldState
from .base import CompetenceUnit


class InputStructuringUnit(CompetenceUnit):
    def __init__(
        self,
        threshold: float = 0.0,
        sensitivity: float = 1.0,
        weight: float = 1.0,
        decay: float = 0.0,
    ) -> None:
        self.name = "input_structuring"
        self.threshold = threshold
        self.sensitivity = sensitivity
        self.weight = weight
        self.decay = decay

    def activation(self, field: FieldState) -> float:
        required_keys = {"task_id", "task_path"}
        if not required_keys.issubset(field.task_signal):
            return 0.0
        return self.sensitivity * self.weight

    def transform(self, field: FieldState) -> FieldDelta:
        task_id = str(field.task_signal["task_id"])
        task_path = Path(str(field.task_signal["task_path"]))
        bug_file = task_path / "bug.py"
        test_file = task_path / "test_bug.py"
        meta_file = task_path / "meta.txt"

        bug_text = bug_file.read_text(encoding="utf-8")
        test_text = test_file.read_text(encoding="utf-8")
        meta_text = meta_file.read_text(encoding="utf-8") if meta_file.exists() else ""
        meta_present = bool(meta_text.strip())

        expected_failure = self._extract_expected_failure(meta_text)

        context_updates = {
            "task_id": task_id,
            "task_path": str(task_path),
            "files": {
                "bug.py": str(bug_file),
                "test_bug.py": str(test_file),
                "meta.txt": str(meta_file),
            },
            "artifacts": {
                "bug.py": bug_text,
                "test_bug.py": test_text,
                "meta.txt": meta_text,
            },
            "expected_failure": expected_failure,
        }

        salience_updates = {
            "code": 1.0,
            "tests": 0.9,
            "failure_signal": 0.8 if expected_failure else 0.4,
        }

        trace_events = [
            {
                "tick": field.tick,
                "unit": self.name,
                "event_type": "unit_delta_applied",
                "reason": "task_signal contains task_id and task_path",
                "input_summary": {
                    "task_id": task_id,
                    "task_path": str(task_path),
                    "files_detected": ["bug.py", "test_bug.py", "meta.txt"],
                    "expected_failure_present": meta_present,
                },
                "changes": {
                    "context_keys": sorted(context_updates.keys()),
                    "salience_updates": salience_updates,
                },
            },
        ]

        return FieldDelta(
            source_unit=self.name,
            context_updates=context_updates,
            salience_updates=salience_updates,
            trace_events=trace_events,
        )

    @staticmethod
    def _extract_expected_failure(meta_text: str) -> str | None:
        for raw_line in meta_text.splitlines():
            line = raw_line.strip()
            if not line or ":" not in line:
                continue
            key, value = line.split(":", 1)
            if key.strip().lower() in {"expected_failure", "failure_signal", "error"}:
                cleaned = value.strip()
                return cleaned or None
        return None
