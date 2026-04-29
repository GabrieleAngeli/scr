from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path


class L1LearningUpdater:
    DEFAULT_STATE = {
        "divergence": {
            "threshold": 0.5,
            "weight": 1.0,
            "sensitivity": 1.0,
            "decay": 0.05,
        },
        "competition": {
            "threshold": 0.5,
            "weight": 1.0,
            "sensitivity": 1.0,
            "decay": 0.05,
            "max_active_hypotheses": 2,
        },
    }
    DIVERGENCE_WEIGHT_MIN = 0.10
    DIVERGENCE_WEIGHT_MAX = 5.00
    COMPETITION_MAX_ACTIVE_MIN = 1
    COMPETITION_MAX_ACTIVE_MAX = 5

    def __init__(self, state_path: str | Path = ".scr/learning_state.json") -> None:
        self.state_path = Path(state_path)

    def update(self, replay: dict) -> dict:
        state = self._load_state()
        reward = self._compute_reward(replay)
        pruned_count = self._count_pruned_hypotheses(replay)
        failed_validations = self._count_failed_validations(replay)

        divergence_weight = float(state["divergence"]["weight"])
        divergence_delta = reward
        if pruned_count >= 2:
            divergence_delta -= 0.10
        state["divergence"]["weight"] = self._clamp_float(
            divergence_weight + divergence_delta,
            self.DIVERGENCE_WEIGHT_MIN,
            self.DIVERGENCE_WEIGHT_MAX,
        )

        max_active = int(state["competition"]["max_active_hypotheses"])
        if failed_validations >= 2:
            max_active -= 1
        state["competition"]["max_active_hypotheses"] = self._clamp_int(
            max_active,
            self.COMPETITION_MAX_ACTIVE_MIN,
            self.COMPETITION_MAX_ACTIVE_MAX,
        )

        self._write_state(state)
        return state

    def _load_state(self) -> dict:
        if not self.state_path.exists():
            return deepcopy(self.DEFAULT_STATE)
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _write_state(self, state: dict) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps(state, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    @staticmethod
    def _compute_reward(replay: dict) -> float:
        outcome = str(replay.get("outcome", ""))
        total_ticks = max((int(entry["tick"]) for entry in replay.get("trace", [])), default=0)

        if outcome == "SUCCESS":
            return 0.20 if total_ticks <= 6 else 0.10
        if outcome == "REOPENED":
            return -0.20
        if outcome.startswith("FAILED_"):
            return -0.30
        return 0.0

    @staticmethod
    def _count_pruned_hypotheses(replay: dict) -> int:
        for entry in replay.get("trace", []):
            if entry.get("unit") != "competition":
                continue
            pruned = entry.get("changes", {}).get("pruned_hypotheses", [])
            return len(pruned)
        return 0

    @staticmethod
    def _count_failed_validations(replay: dict) -> int:
        failed_validations = 0
        for result in replay.get("validation_results", []):
            if not result.get("passed", False):
                failed_validations += 1
        return failed_validations

    @staticmethod
    def _clamp_float(value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(round(value, 4), maximum))

    @staticmethod
    def _clamp_int(value: int, minimum: int, maximum: int) -> int:
        return max(minimum, min(value, maximum))


class ReplayFeatureExtractor:
    @staticmethod
    def extract(replay: dict) -> dict:
        trace = replay.get("trace", [])
        total_ticks = max((int(entry.get("tick", 0)) for entry in trace), default=0)
        activated_units: list[str] = []
        for entry in trace:
            unit = str(entry.get("unit", ""))
            if unit and unit != "runtime" and unit not in activated_units:
                activated_units.append(unit)

        validation_results = replay.get("validation_results", [])
        failed_validations = sum(1 for result in validation_results if not result.get("passed", False))
        pruned_hypotheses = 0
        for entry in trace:
            if entry.get("unit") == "competition":
                pruned_hypotheses = len(entry.get("changes", {}).get("pruned_hypotheses", []))
                break

        return {
            "outcome": replay.get("outcome"),
            "total_ticks": total_ticks,
            "activated_units": activated_units,
            "activated_unit_count": len(activated_units),
            "validation_count": len(validation_results),
            "failed_validations": failed_validations,
            "pruned_hypotheses": pruned_hypotheses,
            "selected_hypothesis": replay.get("selected_hypothesis"),
        }


class LearningRunComparator:
    @staticmethod
    def compare(before_replay: dict, after_replay: dict) -> dict:
        before = ReplayFeatureExtractor.extract(before_replay)
        after = ReplayFeatureExtractor.extract(after_replay)
        return {
            "before": before,
            "after": after,
            "delta": {
                "ticks": after["total_ticks"] - before["total_ticks"],
                "failed_validations": after["failed_validations"] - before["failed_validations"],
                "activated_unit_count": after["activated_unit_count"] - before["activated_unit_count"],
                "validation_count": after["validation_count"] - before["validation_count"],
            },
            "improved": {
                "ticks_reduced": after["total_ticks"] < before["total_ticks"],
                "failed_validations_reduced": after["failed_validations"] < before["failed_validations"],
                "outcome_improved": str(after.get("outcome")) == "SUCCESS" and str(before.get("outcome")) != "SUCCESS",
            },
        }
