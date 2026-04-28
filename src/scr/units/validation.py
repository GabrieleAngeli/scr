from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from ..delta import FieldDelta
from ..field import FieldState
from .base import CompetenceUnit


class ValidationUnit(CompetenceUnit):
    def __init__(
        self,
        threshold: float = 0.0,
        sensitivity: float = 1.0,
        weight: float = 1.0,
        decay: float = 0.0,
    ) -> None:
        self.name = "validation"
        self.threshold = threshold
        self.sensitivity = sensitivity
        self.weight = weight
        self.decay = decay

    def activation(self, field: FieldState) -> float:
        has_active = bool(field.context_map.get("active_hypotheses"))
        has_hypotheses = bool(field.hypothesis_pool)
        if not (has_active and has_hypotheses):
            return 0.0
        return self.sensitivity * self.weight

    def transform(self, field: FieldState) -> FieldDelta:
        task_path = Path(str(field.task_signal["task_path"]))
        active_ids = set(field.context_map.get("active_hypotheses", []))
        updated_hypotheses: list[dict[str, object]] = []
        validation_results: list[dict[str, object]] = []

        for hypothesis in field.hypothesis_pool:
            updated = dict(hypothesis)
            hypothesis_id = str(updated.get("hypothesis_id", ""))
            if hypothesis_id not in active_ids:
                updated_hypotheses.append(updated)
                continue

            result = self._validate_hypothesis(task_path=task_path, hypothesis=updated)
            updated["status"] = "validated" if result["passed"] else "failed"
            updated["validation_result"] = result
            updated_hypotheses.append(updated)
            validation_results.append(result)

        trace_events = [
            {
                "tick": field.tick,
                "unit": self.name,
                "event_type": "unit_delta_applied",
                "reason": "active hypotheses are available for deterministic validation",
                "input_summary": {
                    "active_hypotheses": sorted(active_ids),
                    "task_path": str(task_path),
                },
                "changes": {
                    "validation_results": validation_results,
                },
            }
        ]

        return FieldDelta(
            source_unit=self.name,
            hypotheses_replace=updated_hypotheses,
            context_updates={"validation_results": validation_results},
            trace_events=trace_events,
        )

    def _validate_hypothesis(self, task_path: Path, hypothesis: dict[str, object]) -> dict[str, object]:
        with tempfile.TemporaryDirectory(prefix="scr-validation-") as temp_dir:
            temp_task_path = Path(temp_dir) / task_path.name
            shutil.copytree(task_path, temp_task_path)

            bug_file = temp_task_path / "bug.py"
            original_code = bug_file.read_text(encoding="utf-8")
            patched_code = self._apply_deterministic_strategy(original_code, hypothesis)
            bug_file.write_text(patched_code, encoding="utf-8")

            completed = subprocess.run(
                [sys.executable, "-m", "pytest", "test_bug.py"],
                cwd=str(temp_task_path),
                capture_output=True,
                text=True,
                check=False,
            )

            return {
                "hypothesis_id": hypothesis["hypothesis_id"],
                "passed": completed.returncode == 0,
                "returncode": completed.returncode,
                "temporary_task_path": str(temp_task_path),
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }

    @staticmethod
    def _apply_deterministic_strategy(code: str, hypothesis: dict[str, object]) -> str:
        summary = str(hypothesis.get("proposed_change_summary", "")).lower()
        issue = str(hypothesis.get("suspected_issue", "")).lower()
        if "subtraction" in summary or "addition" in summary or "wrong operator" in issue:
            return code.replace("return a - b", "return a + b", 1)
        return code
