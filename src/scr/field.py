from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FieldState:
    task_signal: dict[str, Any]
    context_map: dict[str, Any] = field(default_factory=dict)
    salience_map: dict[str, float] = field(default_factory=dict)
    hypothesis_pool: list[dict[str, Any]] = field(default_factory=list)
    energy_map: dict[str, float] = field(default_factory=dict)
    tension_map: dict[str, float] = field(default_factory=dict)
    stability_score: float = 1.0
    activation_levels: dict[str, float] = field(default_factory=dict)
    trace: list[dict[str, Any]] = field(default_factory=list)
    tick: int = 0
