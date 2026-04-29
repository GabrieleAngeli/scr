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


def selected_units_from_trace(trace: list[dict]) -> list[str]:
    selected: list[str] = []
    for event in trace:
        if event["unit"] == "runtime" and event["event_type"] == "activation_policy":
            unit_name = event["changes"]["selected_unit"]
            if unit_name is not None:
                selected.append(unit_name)
    return selected


def test_activation_policy_does_not_activate_all_units_on_each_tick() -> None:
    task_path = Path("tasks/task_001").resolve()
    field = FieldState(task_signal={"task_id": "task_001", "task_path": str(task_path)})
    runtime = build_all_units_runtime()

    result = runtime.run(field)
    policy_events = [entry for entry in result.trace if entry["unit"] == "runtime" and entry["event_type"] == "activation_policy"]

    assert policy_events
    assert all(isinstance(event["changes"]["selected_unit"], (str, type(None))) for event in policy_events)


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
            selected_unit = event["changes"]["selected_unit"]
            if selected_unit is not None:
                selected_units.append(selected_unit)

    activated_unit_events = [
        entry["unit"]
        for entry in result.trace
        if entry["unit"] != "runtime" and entry["event_type"] == "unit_delta_applied"
    ]

    assert activated_unit_events
    assert set(activated_unit_events).issubset(set(selected_units))


def test_tick_count_is_not_greater_than_units_really_needed() -> None:
    task_path = Path("tasks/task_001").resolve()
    field = FieldState(task_signal={"task_id": "task_001", "task_path": str(task_path)})
    runtime = build_all_units_runtime(max_ticks=10)

    result = runtime.run(field)
    activated_units = [
        entry["unit"]
        for entry in result.trace
        if entry["unit"] != "runtime" and entry["event_type"] == "unit_delta_applied"
    ]

    assert result.tick <= len(activated_units)


def test_trace_shows_sequential_activation() -> None:
    task_path = Path("tasks/task_001").resolve()
    field = FieldState(task_signal={"task_id": "task_001", "task_path": str(task_path)})
    runtime = build_all_units_runtime(max_ticks=10)

    result = runtime.run(field)
    policy_events = [entry for entry in result.trace if entry["unit"] == "runtime" and entry["event_type"] == "activation_policy"]
    unit_events = [entry for entry in result.trace if entry["unit"] != "runtime" and entry["event_type"] == "unit_delta_applied"]

    assert len(policy_events) == len(unit_events)
    for policy_event, unit_event in zip(policy_events, unit_events):
        assert policy_event["tick"] == unit_event["tick"]
        assert policy_event["changes"]["selected_unit"] == unit_event["unit"]


def test_gating_fresh_field_requires_full_chain() -> None:
    task_path = Path("tasks/task_001").resolve()
    field = FieldState(task_signal={"task_id": "task_001", "task_path": str(task_path)})
    runtime = build_all_units_runtime(max_ticks=10)

    result = runtime.run(field)
    assert result.tick == 6
    assert selected_units_from_trace(result.trace) == [
        "input_structuring",
        "standardization",
        "divergence",
        "competition",
        "validation",
        "consolidation",
    ]


def test_gating_starts_from_standardization_when_context_is_preloaded() -> None:
    task_path = Path("tasks/task_001").resolve()
    field = FieldState(
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
    runtime = build_all_units_runtime(max_ticks=10)

    result = runtime.run(field)
    assert result.tick == 5
    assert selected_units_from_trace(result.trace)[0] == "standardization"


def test_gating_starts_from_divergence_when_standardization_outputs_exist() -> None:
    task_path = Path("tasks/task_001").resolve()
    field = FieldState(
        task_signal={"task_id": "task_001", "task_path": str(task_path)},
        context_map={
            "code_artifact": {
                "name": "bug.py",
                "path": str(task_path / "bug.py"),
                "content": (task_path / "bug.py").read_text(encoding="utf-8"),
            },
            "test_artifact": {
                "name": "test_bug.py",
                "path": str(task_path / "test_bug.py"),
                "content": (task_path / "test_bug.py").read_text(encoding="utf-8"),
            },
            "metadata_artifact": {
                "name": "meta.txt",
                "path": str(task_path / "meta.txt"),
                "content": (task_path / "meta.txt").read_text(encoding="utf-8"),
            },
        },
    )
    runtime = build_all_units_runtime(max_ticks=10)

    result = runtime.run(field)
    assert result.tick == 4
    assert selected_units_from_trace(result.trace) == [
        "divergence",
        "competition",
        "validation",
        "consolidation",
    ]


def test_gating_starts_from_competition_when_hypotheses_already_exist() -> None:
    task_path = Path("tasks/task_001").resolve()
    field = FieldState(
        task_signal={"task_id": "task_001", "task_path": str(task_path)},
        context_map={"code_artifact": {"path": str(task_path / "bug.py"), "content": "def add(a, b): return a-b"}},
        hypothesis_pool=[
            {
                "hypothesis_id": "h1",
                "confidence": 0.9,
                "suspected_issue": "wrong operator",
                "proposed_change_summary": "replace subtraction with addition",
            }
        ],
    )
    runtime = build_all_units_runtime(max_ticks=10)

    result = runtime.run(field)
    assert result.tick == 3
    assert selected_units_from_trace(result.trace) == ["competition", "validation", "consolidation"]


def test_gating_goes_directly_to_validation_with_active_hypotheses() -> None:
    task_path = Path("tasks/task_001").resolve()
    field = FieldState(
        task_signal={"task_id": "task_001", "task_path": str(task_path)},
        context_map={
            "active_hypotheses": ["h1"],
            "code_artifact": {
                "name": "bug.py",
                "path": str(task_path / "bug.py"),
                "content": (task_path / "bug.py").read_text(encoding="utf-8"),
            },
            "test_artifact": {
                "name": "test_bug.py",
                "path": str(task_path / "test_bug.py"),
                "content": (task_path / "test_bug.py").read_text(encoding="utf-8"),
            },
            "metadata_artifact": {
                "name": "meta.txt",
                "path": str(task_path / "meta.txt"),
                "content": (task_path / "meta.txt").read_text(encoding="utf-8"),
            },
        },
        hypothesis_pool=[
            {
                "hypothesis_id": "h1",
                "confidence": 0.9,
                "suspected_issue": "wrong operator",
                "proposed_change_summary": "replace subtraction with addition",
            }
        ],
    )
    runtime = build_all_units_runtime(max_ticks=10)

    result = runtime.run(field)
    assert result.tick == 2
    assert selected_units_from_trace(result.trace) == ["validation", "consolidation"]


def test_gating_goes_directly_to_consolidation_with_validation_results() -> None:
    task_path = Path("tasks/task_001").resolve()
    field = FieldState(
        task_signal={"task_id": "task_001", "task_path": str(task_path)},
        context_map={
            "code_artifact": {"name": "bug.py", "path": str(task_path / "bug.py"), "content": "def add(a,b): return a+b"},
            "active_hypotheses": ["h1"],
            "validation_results": [
                {
                    "hypothesis_id": "h1",
                    "passed": True,
                    "returncode": 0,
                    "temporary_task_path": str(task_path),
                    "stdout": "",
                    "stderr": "",
                }
            ]
        },
        hypothesis_pool=[{"hypothesis_id": "h1", "status": "validated"}],
    )
    runtime = build_all_units_runtime(max_ticks=10)

    result = runtime.run(field)
    assert result.tick == 1
    assert selected_units_from_trace(result.trace) == ["consolidation"]


def test_gating_does_not_run_when_outcome_is_already_defined() -> None:
    task_path = Path("tasks/task_001").resolve()
    field = FieldState(
        task_signal={"task_id": "task_001", "task_path": str(task_path)},
        outcome="SUCCESS",
    )
    runtime = build_all_units_runtime(max_ticks=10)

    result = runtime.run(field)
    assert result.tick == 0
    assert selected_units_from_trace(result.trace) == []
