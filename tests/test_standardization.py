from pathlib import Path

from scr.field import FieldState
from scr.runtime import RuntimeConfig, SCRRuntime
from scr.units.input_structuring import InputStructuringUnit
from scr.units.standardization import StandardizationUnit

def build_populated_field() -> FieldState:
    task_path = Path("tasks/task_001").resolve()
    input_runtime = SCRRuntime(units=[InputStructuringUnit()])
    field = FieldState(
        task_signal={
            "task_id": "task_001",
            "task_path": str(task_path),
        }
    )
    return input_runtime.run(field)


def test_standardization_detects_bug_py_as_code_artifact() -> None:
    field = build_populated_field()
    runtime = SCRRuntime(units=[StandardizationUnit()], config=RuntimeConfig(max_ticks=2))

    result = runtime.run(field)

    assert result.context_map["code_artifact"]["name"] == "bug.py"
    assert "return a - b" in result.context_map["code_artifact"]["content"]


def test_standardization_detects_test_bug_py_as_test_artifact() -> None:
    field = build_populated_field()
    runtime = SCRRuntime(units=[StandardizationUnit()], config=RuntimeConfig(max_ticks=2))

    result = runtime.run(field)

    assert result.context_map["test_artifact"]["name"] == "test_bug.py"
    assert "assert add(2, 3) == 5" in result.context_map["test_artifact"]["content"]


def test_standardization_detects_meta_txt_as_metadata_artifact() -> None:
    field = build_populated_field()
    runtime = SCRRuntime(units=[StandardizationUnit()], config=RuntimeConfig(max_ticks=2))

    result = runtime.run(field)

    assert result.context_map["metadata_artifact"]["name"] == "meta.txt"
    assert "expected_failure: wrong operator in add" in result.context_map["metadata_artifact"]["content"]


def test_standardization_produces_structured_trace() -> None:
    field = build_populated_field()
    runtime = SCRRuntime(units=[StandardizationUnit()], config=RuntimeConfig(max_ticks=2))

    result = runtime.run(field)
    event = next(item for item in result.trace if item["unit"] == "standardization")

    assert set(event) >= {"seq", "tick", "unit", "event_type", "reason", "input_summary", "changes"}
    assert event["event_type"] == "unit_delta_applied"
    assert event["reason"] == "context_map contains task artifacts to normalize"
    assert event["input_summary"]["artifact_names"] == ["bug.py", "meta.txt", "test_bug.py"]
    assert "normalized_artifacts" in event["changes"]["context_keys"]


def test_standardization_does_not_modify_original_files() -> None:
    task_path = Path("tasks/task_001").resolve()
    original_bug = (task_path / "bug.py").read_text(encoding="utf-8")
    original_test = (task_path / "test_bug.py").read_text(encoding="utf-8")
    original_meta = (task_path / "meta.txt").read_text(encoding="utf-8")

    field = build_populated_field()
    runtime = SCRRuntime(units=[StandardizationUnit()], config=RuntimeConfig(max_ticks=2))
    runtime.run(field)

    assert (task_path / "bug.py").read_text(encoding="utf-8") == original_bug
    assert (task_path / "test_bug.py").read_text(encoding="utf-8") == original_test
    assert (task_path / "meta.txt").read_text(encoding="utf-8") == original_meta

def test_print_standardization_trace() -> None:
    field = build_populated_field()
    runtime = SCRRuntime(units=[StandardizationUnit()], config=RuntimeConfig(max_ticks=2))
    result = runtime.run(field)

    print("\nSTANDARDIZATION TRACE:")
    for entry in result.trace:
        print(entry)
