from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .baseline import BaselineRunner
from .field import FieldState
from .runtime import RuntimeConfig, SCRRuntime
from .units.competition import CompetitionUnit
from .units.consolidation import ConsolidationUnit
from .units.divergence import DivergenceUnit
from .units.input_structuring import InputStructuringUnit
from .units.standardization import StandardizationUnit
from .units.validation import ValidationUnit


class BenchmarkRunner:
    def __init__(self, output_path: str | Path | None = None) -> None:
        self.output_path = Path(output_path) if output_path is not None else None
        self.baseline_runner = BaselineRunner()

    def run(self, task_path: str | Path) -> Path:
        task_dir = Path(task_path)
        task_id = task_dir.name
        result_path = self.output_path or self._build_default_output_path(task_id)

        scr_field, scr_validation_time_ms = self._run_scr(task_dir, task_id)
        baseline_result = self.baseline_runner.run(task_dir)

        benchmark_result = {
            "task_id": task_id,
            "scr_outcome": scr_field.outcome,
            "baseline_outcome": baseline_result["outcome"],
            "scr_ticks": scr_field.tick,
            "scr_hypothesis_count": len(scr_field.hypothesis_pool),
            "scr_validated_hypothesis_count": len(scr_field.context_map.get("validation_results", [])),
            "scr_validation_time_ms": scr_validation_time_ms,
            "baseline_validation_time_ms": baseline_result["validation_time_ms"],
            "winner": self._determine_winner(
                scr_outcome=str(scr_field.outcome),
                baseline_outcome=str(baseline_result["outcome"]),
                scr_validation_time_ms=scr_validation_time_ms,
                baseline_validation_time_ms=float(baseline_result["validation_time_ms"]),
            ),
        }

        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(benchmark_result, indent=2, sort_keys=True), encoding="utf-8")
        return result_path

    @staticmethod
    def _run_scr(task_dir: Path, task_id: str) -> tuple[FieldState, float]:
        field = FieldState(task_signal={"task_id": task_id, "task_path": str(task_dir)})
        input_runtime = SCRRuntime(units=[InputStructuringUnit()])
        standardization_runtime = SCRRuntime(units=[StandardizationUnit()], config=RuntimeConfig(max_ticks=2))
        divergence_runtime = SCRRuntime(units=[DivergenceUnit()], config=RuntimeConfig(max_ticks=3))
        competition_runtime = SCRRuntime(units=[CompetitionUnit()], config=RuntimeConfig(max_ticks=4))
        validation_runtime = SCRRuntime(units=[ValidationUnit()], config=RuntimeConfig(max_ticks=5))
        consolidation_runtime = SCRRuntime(units=[ConsolidationUnit()], config=RuntimeConfig(max_ticks=6))

        field = input_runtime.run(field)
        field = standardization_runtime.run(field)
        field = divergence_runtime.run(field)
        field = competition_runtime.run(field)

        validation_start = time.perf_counter()
        field = validation_runtime.run(field)
        validation_time_ms = round((time.perf_counter() - validation_start) * 1000, 3)

        field = consolidation_runtime.run(field)
        return field, validation_time_ms

    @staticmethod
    def _determine_winner(
        scr_outcome: str,
        baseline_outcome: str,
        scr_validation_time_ms: float,
        baseline_validation_time_ms: float,
    ) -> str:
        if scr_outcome == "SUCCESS" and baseline_outcome != "SUCCESS":
            return "SCR"
        if baseline_outcome == "SUCCESS" and scr_outcome != "SUCCESS":
            return "BASELINE"
        if scr_validation_time_ms <= baseline_validation_time_ms:
            return "SCR"
        return "BASELINE"

    @staticmethod
    def _build_default_output_path(task_id: str) -> Path:
        run_id = datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S_%f")
        return Path(".scr") / "benchmarks" / run_id / f"{task_id}.json"
