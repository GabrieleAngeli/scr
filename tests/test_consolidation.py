from pathlib import Path

from scr.field import FieldState
from scr.runtime import RuntimeConfig, SCRRuntime
from scr.units.competition import CompetitionUnit
from scr.units.consolidation import ConsolidationUnit
from scr.units.divergence import DivergenceUnit
from scr.units.input_structuring import InputStructuringUnit
from scr.units.standardization import StandardizationUnit
from scr.units.validation import ValidationUnit


def build_validated_field() -> FieldState:
    task_path = Path("tasks/task_001").resolve()
    field = FieldState(
        task_signal={
            "task_id": "task_001",
            "task_path": str(task_path),
        }
    )
    input_runtime = SCRRuntime(units=[InputStructuringUnit()])
    standardization_runtime = SCRRuntime(units=[StandardizationUnit()], config=RuntimeConfig(max_ticks=2))
    divergence_runtime = SCRRuntime(units=[DivergenceUnit()], config=RuntimeConfig(max_ticks=3))
    competition_runtime = SCRRuntime(units=[CompetitionUnit()], config=RuntimeConfig(max_ticks=4))
    validation_runtime = SCRRuntime(units=[ValidationUnit()], config=RuntimeConfig(max_ticks=5))
    return validation_runtime.run(
        competition_runtime.run(
            divergence_runtime.run(
                standardization_runtime.run(
                    input_runtime.run(field)
                )
            )
        )
    )


def test_consolidation_sets_success_when_one_hypothesis_passes() -> None:
    field = build_validated_field()
    runtime = SCRRuntime(units=[ConsolidationUnit()], config=RuntimeConfig(max_ticks=6))

    result = runtime.run(field)

    assert result.outcome == "SUCCESS"


def test_consolidation_selects_first_passed_hypothesis() -> None:
    field = build_validated_field()
    runtime = SCRRuntime(units=[ConsolidationUnit()], config=RuntimeConfig(max_ticks=6))

    result = runtime.run(field)

    assert result.selected_hypothesis is not None
    assert result.selected_hypothesis["hypothesis_id"] == "div-001"


def test_consolidation_sets_reopened_when_all_validations_fail() -> None:
    field = build_validated_field()
    for hypothesis in field.hypothesis_pool:
        validation_result = hypothesis.get("validation_result")
        if validation_result is None:
            continue
        validation_result["passed"] = False
        hypothesis["status"] = "failed"
    for result in field.context_map["validation_results"]:
        result["passed"] = False

    runtime = SCRRuntime(units=[ConsolidationUnit()], config=RuntimeConfig(max_ticks=6))
    consolidated = runtime.run(field)

    assert consolidated.outcome == "REOPENED"
    assert consolidated.selected_hypothesis is None


def test_consolidation_sets_failed_no_valid_hypothesis_when_pool_is_empty() -> None:
    field = FieldState(task_signal={"task_id": "empty-task", "task_path": "tasks/task_001"})
    runtime = SCRRuntime(units=[ConsolidationUnit()], config=RuntimeConfig(max_ticks=1))

    result = runtime.run(field)

    assert result.outcome == "FAILED_NO_VALID_HYPOTHESIS"
    assert result.selected_hypothesis is None


def test_consolidation_produces_replayable_trace_with_outcome() -> None:
    field = build_validated_field()
    runtime = SCRRuntime(units=[ConsolidationUnit()], config=RuntimeConfig(max_ticks=6))

    result = runtime.run(field)
    event = next(item for item in result.trace if item["unit"] == "consolidation")

    assert event["event_type"] == "unit_delta_applied"
    assert event["changes"]["outcome"] == "SUCCESS"
    assert event["changes"]["selected_hypothesis"]["hypothesis_id"] == "div-001"
