from pathlib import Path

from scr.field import FieldState
from scr.runtime import RuntimeConfig, SCRRuntime
from scr.units.competition import CompetitionUnit
from scr.units.divergence import DivergenceUnit
from scr.units.input_structuring import InputStructuringUnit
from scr.units.standardization import StandardizationUnit
from scr.units.validation import ValidationUnit


def build_competed_field() -> FieldState:
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
    return competition_runtime.run(divergence_runtime.run(standardization_runtime.run(input_runtime.run(field))))


def test_validation_validates_only_active_hypotheses() -> None:
    field = build_competed_field()
    runtime = SCRRuntime(units=[ValidationUnit()], config=RuntimeConfig(max_ticks=5))

    result = runtime.run(field)
    validated_ids = {item["hypothesis_id"] for item in result.context_map["validation_results"]}

    assert validated_ids == set(result.context_map["active_hypotheses"])


def test_validation_does_not_validate_pruned_hypotheses() -> None:
    field = build_competed_field()
    runtime = SCRRuntime(units=[ValidationUnit()], config=RuntimeConfig(max_ticks=5))

    result = runtime.run(field)
    pruned = [item for item in result.hypothesis_pool if item.get("status") == "pruned"]

    assert pruned
    for hypothesis in pruned:
        assert "validation_result" not in hypothesis


def test_validation_executes_pytest_on_temporary_copy() -> None:
    field = build_competed_field()
    runtime = SCRRuntime(units=[ValidationUnit()], config=RuntimeConfig(max_ticks=5))

    result = runtime.run(field)

    assert result.context_map["validation_results"]
    for validation_result in result.context_map["validation_results"]:
        assert "scr-validation-" in validation_result["temporary_task_path"]
        assert Path(validation_result["temporary_task_path"]).name == "task_001"


def test_validation_does_not_modify_original_files() -> None:
    task_path = Path("tasks/task_001").resolve()
    original_bug = (task_path / "bug.py").read_text(encoding="utf-8")
    original_test = (task_path / "test_bug.py").read_text(encoding="utf-8")
    original_meta = (task_path / "meta.txt").read_text(encoding="utf-8")

    field = build_competed_field()
    runtime = SCRRuntime(units=[ValidationUnit()], config=RuntimeConfig(max_ticks=5))
    runtime.run(field)

    assert (task_path / "bug.py").read_text(encoding="utf-8") == original_bug
    assert (task_path / "test_bug.py").read_text(encoding="utf-8") == original_test
    assert (task_path / "meta.txt").read_text(encoding="utf-8") == original_meta


def test_validation_produces_replayable_trace_with_results() -> None:
    field = build_competed_field()
    runtime = SCRRuntime(units=[ValidationUnit()], config=RuntimeConfig(max_ticks=5))

    result = runtime.run(field)
    event = next(item for item in result.trace if item["unit"] == "validation")

    assert event["event_type"] == "unit_delta_applied"
    assert "validation_results" in event["changes"]
    assert len(event["changes"]["validation_results"]) == len(result.context_map["active_hypotheses"])

def test_print_full_trace() -> None:
    field = build_competed_field()
    runtime = SCRRuntime(units=[ValidationUnit()], config=RuntimeConfig(max_ticks=5))
    result = runtime.run(field)

    print("\nFULL TRACE:")
    for entry in result.trace:
        print(entry)
