from pathlib import Path

from scr.field import FieldState
from scr.runtime import RuntimeConfig, SCRRuntime
from scr.units.competition import CompetitionUnit
from scr.units.consolidation import ConsolidationUnit
from scr.units.divergence import DivergenceUnit
from scr.units.input_structuring import InputStructuringUnit
from scr.units.standardization import StandardizationUnit
from scr.units.validation import ValidationUnit


def build_all_units_runtime(max_ticks: int = 6) -> SCRRuntime:
    return SCRRuntime(
        units=[
            InputStructuringUnit(),
            StandardizationUnit(),
            DivergenceUnit(),
            CompetitionUnit(),
            ValidationUnit(),
            ConsolidationUnit(),
        ],
        config=RuntimeConfig(max_ticks=max_ticks),
    )


def test_activation_policy_does_not_activate_all_units_on_each_tick() -> None:
    task_path = Path("tasks/task_001").resolve()
    field = FieldState(task_signal={"task_id": "task_001", "task_path": str(task_path)})
    runtime = build_all_units_runtime()

    result = runtime.run(field)
    policy_events = [entry for entry in result.trace if entry["unit"] == "runtime" and entry["event_type"] == "activation_policy"]

    assert policy_events
    assert all(len(event["changes"]["selected_units"]) <= 1 for event in policy_events)


def test_activation_policy_can_reduce_tick_count_for_prepopulated_field() -> None:
    task_path = Path("tasks/task_001").resolve()
    fresh_field = FieldState(task_signal={"task_id": "task_001", "task_path": str(task_path)})
    fresh_runtime = build_all_units_runtime()
    fresh_result = fresh_runtime.run(fresh_field)

    prepopulated_field = FieldState(
        task_signal={"task_id": "task_001", "task_path": str(task_path)},
        context_map={
            "task_id": "task_001",
            "task_path": str(task_path),
            "files": {
                "bug.py": str(task_path / "bug.py"),
                "test_bug.py": str(task_path / "test_bug.py"),
                "meta.txt": str(task_path / "meta.txt"),
            },
            "artifacts": {
                "bug.py": (task_path / "bug.py").read_text(encoding="utf-8"),
                "test_bug.py": (task_path / "test_bug.py").read_text(encoding="utf-8"),
                "meta.txt": (task_path / "meta.txt").read_text(encoding="utf-8"),
            },
            "expected_failure": "wrong operator in add",
        },
    )
    prepopulated_runtime = build_all_units_runtime(max_ticks=3)
    prepopulated_result = prepopulated_runtime.run(prepopulated_field)

    assert prepopulated_result.tick < fresh_result.tick


def test_trace_contains_only_units_really_activated() -> None:
    task_path = Path("tasks/task_001").resolve()
    field = FieldState(task_signal={"task_id": "task_001", "task_path": str(task_path)})
    runtime = build_all_units_runtime()

    result = runtime.run(field)
    selected_units = []
    for event in result.trace:
        if event["unit"] == "runtime" and event["event_type"] == "activation_policy":
            selected_units.extend(event["changes"]["selected_units"])

    activated_unit_events = [
        entry["unit"]
        for entry in result.trace
        if entry["unit"] != "runtime" and entry["event_type"] == "unit_delta_applied"
    ]

    assert activated_unit_events
    assert set(activated_unit_events).issubset(set(selected_units))
