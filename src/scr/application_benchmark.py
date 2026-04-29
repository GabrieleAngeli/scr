from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .baseline import BaselineRunner
from .benchmark import BenchmarkRunner


@dataclass
class ApplicationThread:
    thread_id: str
    request: str
    expected_outcome: str
    required_competences: list[str]
    input_artifacts: list[str]
    constraints: list[str]
    success_criteria: list[str]

    @classmethod
    def from_dict(cls, payload: dict) -> "ApplicationThread":
        return cls(
            thread_id=str(payload["thread_id"]),
            request=str(payload["request"]),
            expected_outcome=str(payload["expected_outcome"]),
            required_competences=list(payload.get("required_competences", [])),
            input_artifacts=list(payload.get("input_artifacts", [])),
            constraints=list(payload.get("constraints", [])),
            success_criteria=list(payload.get("success_criteria", [])),
        )


class ApplicationThreadBenchmark:
    def __init__(self, output_path: str | Path | None = None, scr_mode: str = "unified") -> None:
        self.output_path = Path(output_path) if output_path is not None else None
        self.baseline_runner = BaselineRunner()
        self.scr_mode = scr_mode

    def load_thread(self, path: str | Path) -> ApplicationThread:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return ApplicationThread.from_dict(payload)

    def run(self, thread_path: str | Path, task_path: str | Path) -> Path:
        thread = self.load_thread(thread_path)
        task_dir = Path(task_path)
        result_path = self.output_path or self._build_default_output_path(thread.thread_id)

        scr_field, scr_validation_time_ms = BenchmarkRunner._run_scr(task_dir, task_dir.name, mode=self.scr_mode)
        baseline_result = self.baseline_runner.run(task_dir)

        scr_thread_result = self._build_scr_thread_result(thread, scr_field, scr_validation_time_ms)
        baseline_thread_result = self._build_baseline_thread_result(thread, baseline_result)

        payload = {
            "thread_id": thread.thread_id,
            "baseline_thread_result": baseline_thread_result,
            "scr_thread_result": scr_thread_result,
            "quality_delta": round(
                scr_thread_result["quality_score"] - baseline_thread_result["quality_score"], 4
            ),
            "cost_delta": round(
                scr_thread_result["resource_cost_score"] - baseline_thread_result["resource_cost_score"], 4
            ),
            "value_delta": round(
                scr_thread_result["efficiency_score"] - baseline_thread_result["efficiency_score"], 4
            ),
        }

        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return result_path

    def _build_scr_thread_result(self, thread: ApplicationThread, field, validation_time_ms: float) -> dict:
        activated_competences = BenchmarkRunner._extract_activated_competences(field.trace)
        unused_competences = [
            competence for competence in thread.required_competences if competence not in activated_competences
        ]
        quality_score = self._quality_score(str(field.outcome), thread.required_competences, activated_competences)
        storage_footprint_kb = self._storage_footprint_kb(field.trace, field.hypothesis_pool)
        validated_hypothesis_count = len(field.context_map.get("validation_results", []))
        resource_cost_score = round(
            validation_time_ms
            + validated_hypothesis_count * 100
            + len(activated_competences) * 50
            + storage_footprint_kb * 2,
            4,
        )
        efficiency_score = round(quality_score / resource_cost_score, 6) if resource_cost_score else 0.0
        return {
            "thread_id": thread.thread_id,
            "outcome": field.outcome,
            "quality_score": quality_score,
            "resource_cost_score": resource_cost_score,
            "storage_footprint_kb": storage_footprint_kb,
            "activated_competences": activated_competences,
            "unused_competences": unused_competences,
            "validated_hypothesis_count": validated_hypothesis_count,
            "validation_time_ms": validation_time_ms,
            "efficiency_score": efficiency_score,
        }

    def _build_baseline_thread_result(self, thread: ApplicationThread, result: dict) -> dict:
        activated_competences = ["baseline_runner"]
        unused_competences = list(thread.required_competences)
        quality_score = self._quality_score(str(result["outcome"]), thread.required_competences, activated_competences)
        storage_footprint_kb = round(
            (len(result.get("stdout", "")) + len(result.get("stderr", ""))) / 1024,
            4,
        )
        resource_cost_score = round(
            float(result["validation_time_ms"])
            + 100
            + len(activated_competences) * 50
            + storage_footprint_kb * 2,
            4,
        )
        efficiency_score = round(quality_score / resource_cost_score, 6) if resource_cost_score else 0.0
        return {
            "thread_id": thread.thread_id,
            "outcome": result["outcome"],
            "quality_score": quality_score,
            "resource_cost_score": resource_cost_score,
            "storage_footprint_kb": storage_footprint_kb,
            "activated_competences": activated_competences,
            "unused_competences": unused_competences,
            "validated_hypothesis_count": 1,
            "validation_time_ms": result["validation_time_ms"],
            "efficiency_score": efficiency_score,
        }

    @staticmethod
    def _quality_score(outcome: str, required_competences: list[str], activated_competences: list[str]) -> float:
        if outcome == "SUCCESS":
            base = 1.0
        elif outcome == "REOPENED":
            base = 0.5
        else:
            base = 0.0

        covered = sum(1 for competence in required_competences if competence in activated_competences)
        bonus = 0.0
        if required_competences:
            bonus = min(0.2, covered / len(required_competences) * 0.2)
        return round(base + bonus, 4)

    @staticmethod
    def _storage_footprint_kb(trace: list[dict], hypothesis_pool: list[dict]) -> float:
        bytes_estimate = len(json.dumps(trace)) + len(json.dumps(hypothesis_pool))
        return round(bytes_estimate / 1024, 4)

    @staticmethod
    def _build_default_output_path(thread_id: str) -> Path:
        return Path(".scr") / "thread_benchmarks" / f"{thread_id}.json"
