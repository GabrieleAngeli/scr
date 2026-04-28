from pathlib import Path

from scr.field import FieldState
from scr.runtime import RuntimeConfig, SCRRuntime
from scr.units.divergence import DivergenceUnit
from scr.units.input_structuring import InputStructuringUnit
from scr.units.standardization import StandardizationUnit


def build_standardized_field() -> FieldState:
    task_path = Path("tasks/task_001").resolve()
    field = FieldState(
        task_signal={
            "task_id": "task_001",
            "task_path": str(task_path),
        }
    )
    input_runtime = SCRRuntime(units=[InputStructuringUnit()])
    standardized_runtime = SCRRuntime(units=[StandardizationUnit()], config=RuntimeConfig(max_ticks=2))
    return standardized_runtime.run(input_runtime.run(field))


def test_divergence_generates_at_least_three_hypotheses() -> None:
    field = build_standardized_field()
    runtime = SCRRuntime(units=[DivergenceUnit()], config=RuntimeConfig(max_ticks=3))

    result = runtime.run(field)

    assert len(result.hypothesis_pool) >= 3


def test_divergence_hypotheses_respect_minimum_schema() -> None:
    field = build_standardized_field()
    runtime = SCRRuntime(units=[DivergenceUnit()], config=RuntimeConfig(max_ticks=3))

    result = runtime.run(field)

    required_keys = {
        "hypothesis_id",
        "target_file",
        "suspected_issue",
        "proposed_change_summary",
        "confidence",
        "source_unit",
    }
    for hypothesis in result.hypothesis_pool:
        assert set(hypothesis) >= required_keys
        assert hypothesis["source_unit"] == "divergence"


def test_divergence_targets_bug_py() -> None:
    field = build_standardized_field()
    runtime = SCRRuntime(units=[DivergenceUnit()], config=RuntimeConfig(max_ticks=3))

    result = runtime.run(field)

    for hypothesis in result.hypothesis_pool:
        assert Path(str(hypothesis["target_file"])).name == "bug.py"


def test_divergence_does_not_modify_original_files() -> None:
    task_path = Path("tasks/task_001").resolve()
    original_bug = (task_path / "bug.py").read_text(encoding="utf-8")
    original_test = (task_path / "test_bug.py").read_text(encoding="utf-8")
    original_meta = (task_path / "meta.txt").read_text(encoding="utf-8")

    field = build_standardized_field()
    runtime = SCRRuntime(units=[DivergenceUnit()], config=RuntimeConfig(max_ticks=3))
    runtime.run(field)

    assert (task_path / "bug.py").read_text(encoding="utf-8") == original_bug
    assert (task_path / "test_bug.py").read_text(encoding="utf-8") == original_test
    assert (task_path / "meta.txt").read_text(encoding="utf-8") == original_meta


def test_divergence_trace_is_replayable_with_hypotheses_added() -> None:
    field = build_standardized_field()
    runtime = SCRRuntime(units=[DivergenceUnit()], config=RuntimeConfig(max_ticks=3))

    result = runtime.run(field)
    event = next(item for item in result.trace if item["unit"] == "divergence")

    assert event["event_type"] == "unit_delta_applied"
    assert "hypotheses_added" in event["changes"]
    assert len(event["changes"]["hypotheses_added"]) >= 3
