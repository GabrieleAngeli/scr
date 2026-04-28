from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .field import FieldState


class ReplayRecorder:
    def __init__(self, base_dir: str | Path = ".scr/runs") -> None:
        self.base_dir = Path(base_dir)

    def record(self, field: FieldState, run_id: str | None = None) -> Path:
        run_identifier = run_id or uuid4().hex
        self.base_dir.mkdir(parents=True, exist_ok=True)

        payload = {
            "run_id": run_identifier,
            "task_id": field.task_signal.get("task_id"),
            "outcome": field.outcome,
            "selected_hypothesis": field.selected_hypothesis,
            "hypothesis_pool": field.hypothesis_pool,
            "active_hypotheses": field.context_map.get("active_hypotheses", []),
            "validation_results": field.context_map.get("validation_results", []),
            "trace": field.trace,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        file_path = self.base_dir / f"{run_identifier}.json"
        file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return file_path

    @staticmethod
    def serialize_field(field: FieldState) -> dict:
        return asdict(field)


class ReplayLoader:
    def __init__(self, base_dir: str | Path = ".scr/runs") -> None:
        self.base_dir = Path(base_dir)

    def load(self, run_id: str) -> dict:
        file_path = self.base_dir / f"{run_id}.json"
        return json.loads(file_path.read_text(encoding="utf-8"))


class ReplayValidator:
    REQUIRED_TOP_LEVEL_KEYS = {
        "run_id",
        "task_id",
        "outcome",
        "hypothesis_pool",
        "trace",
        "created_at",
    }
    REQUIRED_TRACE_KEYS = {
        "seq",
        "tick",
        "unit",
        "event_type",
        "reason",
        "input_summary",
        "changes",
    }

    def validate(self, replay: dict) -> None:
        missing_keys = self.REQUIRED_TOP_LEVEL_KEYS.difference(replay.keys())
        if missing_keys:
            raise ValueError(f"Replay missing required keys: {sorted(missing_keys)}")

        trace = replay["trace"]
        if not trace:
            raise ValueError("Replay trace must not be empty")

        expected_min_seq = None
        for entry in trace:
            missing_trace_keys = self.REQUIRED_TRACE_KEYS.difference(entry.keys())
            if missing_trace_keys:
                raise ValueError(f"Trace entry missing required keys: {sorted(missing_trace_keys)}")

            seq = entry["seq"]
            if expected_min_seq is None:
                expected_min_seq = seq
            elif seq <= expected_min_seq:
                raise ValueError("Trace seq values must be strictly increasing")
            expected_min_seq = seq

        if replay["outcome"] == "SUCCESS" and replay.get("selected_hypothesis") is None:
            raise ValueError("Replay with SUCCESS outcome must include selected_hypothesis")
