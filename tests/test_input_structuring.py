import json
import pytest

from dataclasses import asdict
from pathlib import Path

from scr.field import FieldState
from scr.runtime import SCRRuntime
from scr.units.input_structuring import InputStructuringUnit

@pytest.fixture
def field_after_run(tmp_path):
    task_dir = tmp_path / "task"
    task_dir.mkdir()

    (task_dir / "bug.py").write_text(
        "def add(a, b):\n    return a - b\n",
        encoding="utf-8"
    )

    (task_dir / "test_bug.py").write_text(
        "from bug import add\n\n"
        "def test_add():\n"
        "    assert add(1, 2) == 3\n",
        encoding="utf-8"
    )

    (task_dir / "meta.txt").write_text(
        "Fix the add function\n",
        encoding="utf-8"
    )

    runtime = SCRRuntime(units=[InputStructuringUnit()])
    field = FieldState(
        task_signal={
            "task_id": "tmp_task",
            "task_path": str(task_dir),
        }
    )
    return runtime.run(field)

def make_task_signal() -> dict[str, str]:
    task_path = Path("tasks/task_001").resolve()
    return {"task_id": "task_001", "task_path": str(task_path)}


def test_input_structuring_unit_returns_field_delta_without_mutating_field() -> None:
    field = FieldState(task_signal=make_task_signal(), tick=1)
    before_context = dict(field.context_map)
    before_salience = dict(field.salience_map)
    before_trace = list(field.trace)
    unit = InputStructuringUnit()

    delta = unit.transform(field)

    assert field.context_map == before_context
    assert field.salience_map == before_salience
    assert field.trace == before_trace
    assert delta.source_unit == "input_structuring"
    assert delta.context_updates["task_id"] == "task_001"
    assert "bug.py" in delta.context_updates["files"]
    assert delta.salience_updates == {
        "code": 1.0,
        "tests": 0.9,
        "failure_signal": 0.8,
    }
    assert delta.hypotheses_add == []
    assert delta.hypotheses_remove == []
    assert delta.energy_updates == {}
    assert delta.tension_updates == {}


def test_runtime_applies_input_structuring_delta_to_field() -> None:
    runtime = SCRRuntime(units=[InputStructuringUnit()])
    field = FieldState(task_signal=make_task_signal())

    result = runtime.run(field)

    assert result.tick == 1
    assert result.context_map["task_id"] == "task_001"
    assert result.context_map["expected_failure"] == "wrong operator in add"
    assert "return a - b" in result.context_map["artifacts"]["bug.py"]
    assert "assert add(2, 3) == 5" in result.context_map["artifacts"]["test_bug.py"]
    assert result.salience_map == {
        "code": 1.0,
        "tests": 0.9,
        "failure_signal": 0.8,
    }
    assert result.activation_levels["input_structuring"] == 1.0
    assert result.trace[0]["unit"] == "runtime"


def test_input_structuring_trace_is_semantically_sufficient_for_replay() -> None:
    runtime = SCRRuntime(units=[InputStructuringUnit()])
    field = FieldState(task_signal=make_task_signal())

    result = runtime.run(field)

    input_events = [event for event in result.trace if event["unit"] == "input_structuring"]

    assert len(input_events) == 1

    event = input_events[0]
    assert set(event) >= {"seq", "tick", "unit", "reason", "input_summary", "changes"}
    assert isinstance(event["seq"], int)
    assert event["seq"] >= 1
    assert event["tick"] == 1
    assert event["unit"] == "input_structuring"
    assert event["reason"] == "task_signal contains task_id and task_path"
    assert event["input_summary"]["task_id"] == "task_001"
    assert event["input_summary"]["files_detected"] == ["bug.py", "test_bug.py", "meta.txt"]
    assert event["input_summary"]["expected_failure_present"] is True
    assert "context_keys" in event["changes"]
    assert "salience_updates" in event["changes"]
    assert event["changes"]["salience_updates"]["code"] == 1.0
    assert "expected_failure" in event["changes"]["context_keys"]


def test_field_state_is_json_serializable_after_runtime_execution() -> None:
    runtime = SCRRuntime(units=[InputStructuringUnit()])
    field = FieldState(task_signal=make_task_signal())

    result = runtime.run(field)
    serialized = asdict(result)
    payload = json.dumps(serialized)

    assert "\"task_id\": \"task_001\"" in payload
    assert "\"unit\": \"input_structuring\"" in payload

def test_trace_structure_is_replayable(field_after_run):
    trace = [entry for entry in field_after_run.trace if entry["unit"] == "input_structuring"]

    assert len(trace) == 1

    entry = trace[0]

    # campi obbligatori
    assert "seq" in entry
    assert "tick" in entry
    assert "unit" in entry
    assert "reason" in entry
    assert "input_summary" in entry
    assert "changes" in entry

    # semantica minima
    assert entry["unit"] == "input_structuring"
    assert isinstance(entry["changes"], dict)
    assert isinstance(entry["input_summary"], dict)

def test_trace_contains_meaningful_changes(field_after_run):
    entry = next(item for item in field_after_run.trace if item["unit"] == "input_structuring")

    changes = entry["changes"]

    # deve contenere modifiche reali
    assert "context_keys" in changes
    assert "salience_updates" in changes

    # NON deve essere vuoto o generico
    assert len(changes) > 0

def test_trace_not_plain_log(field_after_run):
    entry = next(item for item in field_after_run.trace if item["unit"] == "input_structuring")

    # evita roba tipo stringhe inutili
    assert not isinstance(entry, str)

    # evita log stile print
    assert "message" not in entry

def test_trace_can_be_serialized(field_after_run):
    json.dumps(field_after_run.trace)

def test_print_trace(field_after_run):
    print("\nTRACE:")
    for entry in field_after_run.trace:
        print(entry)
