from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FieldDelta:
    source_unit: str
    salience_updates: dict[str, float] = field(default_factory=dict)
    tension_updates: dict[str, float] = field(default_factory=dict)
    energy_updates: dict[str, float] = field(default_factory=dict)
    hypotheses_add: list[dict[str, Any]] = field(default_factory=list)
    hypotheses_replace: list[dict[str, Any]] | None = None
    hypotheses_remove: list[str] = field(default_factory=list)
    context_updates: dict[str, Any] = field(default_factory=dict)
    stability_shift: float = 0.0
    trace_events: list[dict[str, Any]] = field(default_factory=list)
