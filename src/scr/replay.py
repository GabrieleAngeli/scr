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
