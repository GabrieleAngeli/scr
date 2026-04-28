import json
from pathlib import Path

from scr.field import FieldState
from scr.replay import ReplayRecorder
from scr.runtime import RuntimeConfig, SCRRuntime
from scr.units.competition import CompetitionUnit
from scr.units.consolidation import ConsolidationUnit
from scr.units.divergence import DivergenceUnit
from scr.units.input_structuring import InputStructuringUnit
from scr.units.standardization import StandardizationUnit
from scr.units.validation import ValidationUnit


def build_consolidated_field() -> FieldState:
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
    consolidation_runtime = SCRRuntime(units=[ConsolidationUnit()], config=RuntimeConfig(max_ticks=6))
    return consolidation_runtime.run(
        validation_runtime.run(
            competition_runtime.run(
                divergence_runtime.run(
                    standardization_runtime.run(
                        input_runtime.run(field)
                    )
                )
            )
        )
    )


def test_replay_recorder_creates_json_file(tmp_path) -> None:
    field = build_consolidated_field()
    recorder = ReplayRecorder(base_dir=tmp_path / ".scr" / "runs")

    replay_path = recorder.record(field, run_id="test-run")

    assert replay_path.exists()
    assert replay_path.name == "test-run.json"


def test_replay_json_is_serializable(tmp_path) -> None:
    field = build_consolidated_field()
    recorder = ReplayRecorder(base_dir=tmp_path / ".scr" / "runs")

    replay_path = recorder.record(field, run_id="serializable-run")
    payload = json.loads(replay_path.read_text(encoding="utf-8"))

    assert payload["run_id"] == "serializable-run"


def test_replay_contains_complete_trace(tmp_path) -> None:
    field = build_consolidated_field()
    recorder = ReplayRecorder(base_dir=tmp_path / ".scr" / "runs")

    replay_path = recorder.record(field, run_id="trace-run")
    payload = json.loads(replay_path.read_text(encoding="utf-8"))

    assert payload["trace"] == field.trace
    assert len(payload["trace"]) > 0


def test_replay_contains_outcome(tmp_path) -> None:
    field = build_consolidated_field()
    recorder = ReplayRecorder(base_dir=tmp_path / ".scr" / "runs")

    replay_path = recorder.record(field, run_id="outcome-run")
    payload = json.loads(replay_path.read_text(encoding="utf-8"))

    assert payload["outcome"] == "SUCCESS"


def test_replay_contains_selected_hypothesis_when_success(tmp_path) -> None:
    field = build_consolidated_field()
    recorder = ReplayRecorder(base_dir=tmp_path / ".scr" / "runs")

    replay_path = recorder.record(field, run_id="selected-run")
    payload = json.loads(replay_path.read_text(encoding="utf-8"))

    assert payload["selected_hypothesis"] is not None
    assert payload["selected_hypothesis"]["hypothesis_id"] == "div-001"
