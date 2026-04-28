from pathlib import Path

from scr.field import FieldState
from scr.runtime import RuntimeConfig, SCRRuntime
from scr.units.competition import CompetitionUnit
from scr.units.divergence import DivergenceUnit
from scr.units.input_structuring import InputStructuringUnit
from scr.units.standardization import StandardizationUnit


def build_diverged_field() -> FieldState:
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
    return divergence_runtime.run(standardization_runtime.run(input_runtime.run(field)))


def test_competition_orders_hypotheses_by_confidence() -> None:
    field = build_diverged_field()
    runtime = SCRRuntime(units=[CompetitionUnit()], config=RuntimeConfig(max_ticks=4))

    result = runtime.run(field)
    confidences = [float(hypothesis["confidence"]) for hypothesis in result.hypothesis_pool]

    assert confidences == sorted(confidences, reverse=True)


def test_competition_keeps_at_most_two_active_hypotheses() -> None:
    field = build_diverged_field()
    runtime = SCRRuntime(units=[CompetitionUnit()], config=RuntimeConfig(max_ticks=4))

    result = runtime.run(field)
    active = [item for item in result.hypothesis_pool if item.get("status") == "active"]

    assert len(active) <= 2
    assert len(result.context_map["active_hypotheses"]) <= 2


def test_competition_marks_remaining_hypotheses_as_pruned() -> None:
    field = build_diverged_field()
    runtime = SCRRuntime(units=[CompetitionUnit()], config=RuntimeConfig(max_ticks=4))

    result = runtime.run(field)
    pruned = [item for item in result.hypothesis_pool if item.get("status") == "pruned"]

    assert len(pruned) >= 1


def test_competition_does_not_remove_hypotheses_from_pool() -> None:
    field = build_diverged_field()
    initial_count = len(field.hypothesis_pool)
    runtime = SCRRuntime(units=[CompetitionUnit()], config=RuntimeConfig(max_ticks=4))

    result = runtime.run(field)

    assert len(result.hypothesis_pool) == initial_count


def test_competition_trace_is_replayable() -> None:
    field = build_diverged_field()
    runtime = SCRRuntime(units=[CompetitionUnit()], config=RuntimeConfig(max_ticks=4))

    result = runtime.run(field)
    event = next(item for item in result.trace if item["unit"] == "competition")

    assert event["event_type"] == "unit_delta_applied"
    assert "active_hypotheses" in event["changes"]
    assert "pruned_hypotheses" in event["changes"]

def test_print_trace() -> None:
    field = build_diverged_field()
    runtime = SCRRuntime(units=[CompetitionUnit()], config=RuntimeConfig(max_ticks=4))
    result = runtime.run(field)

    print("\nTRACE:")
    for entry in result.trace:
        print(entry)
