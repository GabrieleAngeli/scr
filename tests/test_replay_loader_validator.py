import pytest

from scr.replay import ReplayLoader, ReplayRecorder, ReplayValidator
from tests.test_replay import build_consolidated_field


def test_replay_loader_loads_existing_replay(tmp_path) -> None:
    field = build_consolidated_field()
    recorder = ReplayRecorder(base_dir=tmp_path / ".scr" / "runs")
    recorder.record(field, run_id="loadable-run")
    loader = ReplayLoader(base_dir=tmp_path / ".scr" / "runs")

    replay = loader.load("loadable-run")

    assert replay["run_id"] == "loadable-run"


def test_replay_validator_accepts_valid_replay(tmp_path) -> None:
    field = build_consolidated_field()
    recorder = ReplayRecorder(base_dir=tmp_path / ".scr" / "runs")
    replay_path = recorder.record(field, run_id="valid-run")
    loader = ReplayLoader(base_dir=tmp_path / ".scr" / "runs")
    validator = ReplayValidator()

    replay = loader.load("valid-run")
    validator.validate(replay)

    assert replay_path.exists()


def test_replay_validator_fails_when_trace_missing(tmp_path) -> None:
    field = build_consolidated_field()
    recorder = ReplayRecorder(base_dir=tmp_path / ".scr" / "runs")
    recorder.record(field, run_id="missing-trace")
    loader = ReplayLoader(base_dir=tmp_path / ".scr" / "runs")
    validator = ReplayValidator()

    replay = loader.load("missing-trace")
    replay.pop("trace")

    with pytest.raises(ValueError, match="Replay missing required keys"):
        validator.validate(replay)


def test_replay_validator_fails_when_seq_is_not_increasing(tmp_path) -> None:
    field = build_consolidated_field()
    recorder = ReplayRecorder(base_dir=tmp_path / ".scr" / "runs")
    recorder.record(field, run_id="bad-seq")
    loader = ReplayLoader(base_dir=tmp_path / ".scr" / "runs")
    validator = ReplayValidator()

    replay = loader.load("bad-seq")
    replay["trace"][1]["seq"] = replay["trace"][0]["seq"]

    with pytest.raises(ValueError, match="Trace seq values must be strictly increasing"):
        validator.validate(replay)


def test_replay_validator_fails_when_success_has_no_selected_hypothesis(tmp_path) -> None:
    field = build_consolidated_field()
    recorder = ReplayRecorder(base_dir=tmp_path / ".scr" / "runs")
    recorder.record(field, run_id="missing-selected")
    loader = ReplayLoader(base_dir=tmp_path / ".scr" / "runs")
    validator = ReplayValidator()

    replay = loader.load("missing-selected")
    replay["outcome"] = "SUCCESS"
    replay["selected_hypothesis"] = None

    with pytest.raises(ValueError, match="selected_hypothesis"):
        validator.validate(replay)
