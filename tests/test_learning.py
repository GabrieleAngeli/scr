import json

from scr.learning import L1LearningUpdater, LearningRunComparator, ReplayFeatureExtractor
from scr.replay import ReplayLoader, ReplayRecorder, ReplayValidator
from tests.test_replay import build_consolidated_field


def build_valid_replay(tmp_path, run_id: str = "learning-run") -> dict:
    field = build_consolidated_field()
    recorder = ReplayRecorder(base_dir=tmp_path / ".scr" / "runs")
    recorder.record(field, run_id=run_id)
    loader = ReplayLoader(base_dir=tmp_path / ".scr" / "runs")
    replay = loader.load(run_id)
    ReplayValidator().validate(replay)
    return replay


def test_learning_updater_creates_learning_state_json(tmp_path) -> None:
    replay = build_valid_replay(tmp_path, run_id="state-create")
    state_path = tmp_path / ".scr" / "learning_state.json"
    updater = L1LearningUpdater(state_path=state_path)

    updater.update(replay)

    assert state_path.exists()


def test_learning_updater_updates_divergence_weight_on_success(tmp_path) -> None:
    replay = build_valid_replay(tmp_path, run_id="success-run")
    state_path = tmp_path / ".scr" / "learning_state.json"
    updater = L1LearningUpdater(state_path=state_path)

    state = updater.update(replay)

    assert state["divergence"]["weight"] > 1.0


def test_learning_updater_penalizes_failed_replay(tmp_path) -> None:
    replay = build_valid_replay(tmp_path, run_id="failed-run")
    replay["outcome"] = "FAILED_TIMEOUT"
    replay["selected_hypothesis"] = None
    state_path = tmp_path / ".scr" / "learning_state.json"
    updater = L1LearningUpdater(state_path=state_path)

    state = updater.update(replay)

    assert state["divergence"]["weight"] < 1.0


def test_learning_updater_keeps_parameters_within_min_max(tmp_path) -> None:
    replay = build_valid_replay(tmp_path, run_id="clamp-run")
    replay["outcome"] = "FAILED_TIMEOUT"
    replay["validation_results"] = [
        {"hypothesis_id": "div-001", "passed": False},
        {"hypothesis_id": "div-002", "passed": False},
    ]

    state_path = tmp_path / ".scr" / "learning_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "divergence": {
                    "threshold": 0.5,
                    "weight": 0.1,
                    "sensitivity": 1.0,
                    "decay": 0.05,
                },
                "competition": {
                    "threshold": 0.5,
                    "weight": 1.0,
                    "sensitivity": 1.0,
                    "decay": 0.05,
                    "max_active_hypotheses": 1,
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    updater = L1LearningUpdater(state_path=state_path)

    state = updater.update(replay)

    assert state["divergence"]["weight"] == 0.1
    assert state["competition"]["max_active_hypotheses"] == 1


def test_learning_update_is_deterministic_for_same_replay(tmp_path) -> None:
    replay = build_valid_replay(tmp_path, run_id="deterministic-run")
    left_path = tmp_path / "left" / "learning_state.json"
    right_path = tmp_path / "right" / "learning_state.json"
    left_updater = L1LearningUpdater(state_path=left_path)
    right_updater = L1LearningUpdater(state_path=right_path)

    left_state = left_updater.update(replay)
    right_state = right_updater.update(replay)

    assert left_state == right_state


def test_replay_feature_extractor_returns_learning_features(tmp_path) -> None:
    replay = build_valid_replay(tmp_path, run_id="feature-run")
    features = ReplayFeatureExtractor.extract(replay)

    assert features["outcome"] == replay["outcome"]
    assert features["total_ticks"] >= 1
    assert isinstance(features["activated_units"], list)
    assert "validation_count" in features
    assert "failed_validations" in features


def test_learning_run_comparator_reports_deltas(tmp_path) -> None:
    before = build_valid_replay(tmp_path, run_id="before-run")
    after = build_valid_replay(tmp_path, run_id="after-run")
    after["outcome"] = "SUCCESS"

    comparison = LearningRunComparator.compare(before, after)

    assert set(comparison) == {"before", "after", "delta", "improved"}
    assert "ticks" in comparison["delta"]
    assert "failed_validations_reduced" in comparison["improved"]
