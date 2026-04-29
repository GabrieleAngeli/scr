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
    ALLOWED_SCR_MODES = {"unified", "legacy_pipeline"}

    def __init__(self, output_path: str | Path | None = None, scr_mode: str = "unified") -> None:
        self.output_path = Path(output_path) if output_path is not None else None
        self.baseline_runner = BaselineRunner()
        if scr_mode not in self.ALLOWED_SCR_MODES:
            raise ValueError("scr_mode must be either 'unified' or 'legacy_pipeline'")
        self.scr_mode = scr_mode

    def run(self, task_path: str | Path) -> Path:
        task_dir = Path(task_path)
        task_id = task_dir.name
        result_path = self.output_path or self._build_default_output_path(task_id)

        initial_field = FieldState(task_signal={"task_id": task_id, "task_path": str(task_dir)})
        kpi_segmentation = self._build_kpi_segmentation(initial_field)
        run_field = FieldState(task_signal=dict(initial_field.task_signal))
        scr_field, scr_validation_time_ms = self._run_scr(
            task_dir,
            task_id,
            mode=self.scr_mode,
            initial_field=run_field,
        )
        baseline_result = self.baseline_runner.run(task_dir)
        reference_model_result = self._load_reference_model_result(task_dir)
        scr_result = self._build_scr_result(scr_field, scr_validation_time_ms)
        baseline_section = self._build_baseline_result(baseline_result)
        reference_section = self._build_reference_result(reference_model_result)
        comparison = self._build_comparison(scr_result, baseline_section, reference_section)

        benchmark_result = {
            "task_id": task_id,
            "scr_outcome": scr_field.outcome,
            "baseline_outcome": baseline_result["outcome"],
            "scr_ticks": scr_field.tick,
            "scr_hypothesis_count": len(scr_field.hypothesis_pool),
            "scr_validated_hypothesis_count": len(scr_field.context_map.get("validation_results", [])),
            "scr_validation_time_ms": scr_validation_time_ms,
            "baseline_validation_time_ms": baseline_result["validation_time_ms"],
            "winner": comparison["winner"],
            "scr_mode": self.scr_mode,
            "scr_execution_model": "single_runtime" if self.scr_mode == "unified" else "staged_runtimes",
            "baseline_result": baseline_section,
            "scr_result": scr_result,
            "reference_model_result": reference_section,
            "comparison": comparison,
            "kpi_segmentation": kpi_segmentation,
        }

        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(benchmark_result, indent=2, sort_keys=True), encoding="utf-8")
        return result_path

    @staticmethod
    def _run_scr(
        task_dir: Path,
        task_id: str,
        mode: str = "unified",
        initial_field: FieldState | None = None,
    ) -> tuple[FieldState, float]:
        if mode not in BenchmarkRunner.ALLOWED_SCR_MODES:
            raise ValueError("mode must be either 'unified' or 'legacy_pipeline'")
        if mode == "legacy_pipeline":
            return BenchmarkRunner._run_scr_legacy_pipeline(task_dir, task_id, initial_field=initial_field)
        return BenchmarkRunner._run_scr_unified(task_dir, task_id, initial_field=initial_field)

    @staticmethod
    def _run_scr_unified(
        task_dir: Path,
        task_id: str,
        initial_field: FieldState | None = None,
    ) -> tuple[FieldState, float]:
        field = initial_field or FieldState(task_signal={"task_id": task_id, "task_path": str(task_dir)})
        runtime = SCRRuntime(
            units=[
                InputStructuringUnit(),
                StandardizationUnit(),
                DivergenceUnit(),
                CompetitionUnit(),
                ValidationUnit(),
                ConsolidationUnit(),
            ],
            config=RuntimeConfig(max_ticks=10),
        )
        validation_start = time.perf_counter()
        field = runtime.run(field)
        validation_time_ms = round((time.perf_counter() - validation_start) * 1000, 3)
        return field, validation_time_ms

    @staticmethod
    def _run_scr_legacy_pipeline(
        task_dir: Path,
        task_id: str,
        initial_field: FieldState | None = None,
    ) -> tuple[FieldState, float]:
        field = initial_field or FieldState(task_signal={"task_id": task_id, "task_path": str(task_dir)})
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
    def _build_default_output_path(task_id: str) -> Path:
        run_id = datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S_%f")
        return Path(".scr") / "benchmarks" / run_id / f"{task_id}.json"

    @staticmethod
    def _load_reference_model_result(task_dir: Path) -> dict:
        reference_path = task_dir / "reference_model_result.json"
        if reference_path.exists():
            payload = json.loads(reference_path.read_text(encoding="utf-8"))
            payload.setdefault("task_id", task_dir.name)
            return payload
        return {
            "task_id": task_dir.name,
            "outcome": "FAILED",
            "quality_score": 0.0,
            "resource_cost_score": 1.0,
            "storage_footprint_estimate": 0,
            "activated_competences": [],
            "unused_competences": [],
        }

    @staticmethod
    def _build_scr_result(field: FieldState, validation_time_ms: float) -> dict:
        activated_competences = BenchmarkRunner._extract_activated_competences(field.trace)
        unused_competences = BenchmarkRunner._compute_unused_competences(activated_competences)
        quality_score = BenchmarkRunner._quality_score_from_outcome(str(field.outcome))
        resource_cost_score = round(
            1.0
            + (field.tick * 0.15)
            + (len(field.context_map.get("validation_results", [])) * 0.35)
            + (len(activated_competences) * 0.1),
            4,
        )
        storage_footprint_estimate = len(json.dumps(field.trace)) + len(json.dumps(field.hypothesis_pool))
        efficiency_score = round(quality_score / resource_cost_score, 4) if resource_cost_score else 0.0
        return {
            "outcome": field.outcome,
            "quality_score": quality_score,
            "resource_cost_score": resource_cost_score,
            "storage_footprint_estimate": storage_footprint_estimate,
            "activated_competences": activated_competences,
            "unused_competences": unused_competences,
            "efficiency_score": efficiency_score,
            "ticks": field.tick,
            "hypothesis_count": len(field.hypothesis_pool),
            "validated_hypothesis_count": len(field.context_map.get("validation_results", [])),
            "validation_time_ms": validation_time_ms,
        }

    @staticmethod
    def _build_baseline_result(result: dict) -> dict:
        quality_score = BenchmarkRunner._quality_score_from_outcome(str(result["outcome"]))
        resource_cost_score = 1.2
        storage_footprint_estimate = len(result.get("stdout", "")) + len(result.get("stderr", ""))
        return {
            "outcome": result["outcome"],
            "quality_score": quality_score,
            "resource_cost_score": resource_cost_score,
            "storage_footprint_estimate": storage_footprint_estimate,
            "activated_competences": ["baseline_runner"],
            "unused_competences": [],
            "efficiency_score": round(quality_score / resource_cost_score, 4),
            "validation_time_ms": result["validation_time_ms"],
        }

    @staticmethod
    def _build_reference_result(result: dict) -> dict:
        quality_score = float(result.get("quality_score", 0.0))
        resource_cost_score = float(result.get("resource_cost_score", 1.0))
        efficiency_score = round(quality_score / resource_cost_score, 4) if resource_cost_score else 0.0
        return {
            "task_id": result.get("task_id"),
            "outcome": result.get("outcome"),
            "quality_score": quality_score,
            "resource_cost_score": resource_cost_score,
            "storage_footprint_estimate": result.get("storage_footprint_estimate", 0),
            "activated_competences": result.get("activated_competences", []),
            "unused_competences": result.get("unused_competences", []),
            "efficiency_score": efficiency_score,
        }

    @staticmethod
    def _build_comparison(scr_result: dict, baseline_result: dict, reference_result: dict) -> dict:
        contenders = {
            "SCR": scr_result,
            "BASELINE": baseline_result,
            "REFERENCE_MODEL": reference_result,
        }
        winner = max(
            contenders.items(),
            key=lambda item: (
                float(item[1].get("quality_score", 0.0)),
                float(item[1].get("efficiency_score", 0.0)),
                -float(item[1].get("resource_cost_score", 0.0)),
            ),
        )[0]
        return {
            "winner": winner,
            "scores": {
                "SCR": scr_result["efficiency_score"],
                "BASELINE": baseline_result["efficiency_score"],
                "REFERENCE_MODEL": reference_result["efficiency_score"],
            },
        }

    @staticmethod
    def _extract_activated_competences(trace: list[dict]) -> list[str]:
        seen: list[str] = []
        for entry in trace:
            unit = str(entry.get("unit", ""))
            if not unit or unit == "runtime" or unit in seen:
                continue
            seen.append(unit)
        return seen

    @staticmethod
    def _compute_unused_competences(activated_competences: list[str]) -> list[str]:
        known = [
            "input_structuring",
            "standardization",
            "divergence",
            "competition",
            "validation",
            "consolidation",
        ]
        return [name for name in known if name not in activated_competences]

    @staticmethod
    def _quality_score_from_outcome(outcome: str) -> float:
        if outcome == "SUCCESS":
            return 1.0
        if outcome == "REOPENED":
            return 0.4
        return 0.0

    @staticmethod
    def _build_kpi_segmentation(field: FieldState) -> dict:
        profile = BenchmarkRunner._field_profile(field)
        scenario = "task_fresh" if profile == "fresh_from_zero" else "thread_prestructured"
        return {
            "field_profile": profile,
            "scenario": scenario,
            "kpi_bucket": f"{scenario}:{profile}",
        }

    @staticmethod
    def _field_profile(field: FieldState) -> str:
        if field.outcome is not None:
            return "outcome_defined"
        if "validation_results" in field.context_map:
            return "post_validation"
        if field.context_map.get("active_hypotheses"):
            return "post_competition"
        if field.hypothesis_pool:
            return "post_divergence"
        if field.context_map.get("code_artifact") is not None:
            return "post_standardization"
        if field.context_map:
            return "post_input_structuring"
        return "fresh_from_zero"
