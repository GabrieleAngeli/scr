from __future__ import annotations

from dataclasses import dataclass, field

from .delta import FieldDelta
from .field import FieldState
from .units.base import CompetenceUnit


@dataclass
class RuntimeConfig:
    max_ticks: int = 1


@dataclass
class SCRRuntime:
    units: list[CompetenceUnit]
    config: RuntimeConfig = field(default_factory=RuntimeConfig)

    def run(self, field: FieldState) -> FieldState:
        while field.tick < self.config.max_ticks:
            field.tick += 1
            active_deltas = self.run_tick(field)
            if active_deltas:
                break
        return field

    def run_tick(self, field: FieldState) -> list[FieldDelta]:
        deltas: list[FieldDelta] = []
        field.trace.append(
            {
                "seq": self._next_seq(field),
                "tick": field.tick,
                "unit": "runtime",
                "event_type": "tick_start",
                "reason": "tick execution started",
                "input_summary": {"tick": field.tick},
                "changes": {},
            }
        )

        for unit in self.units:
            activation = unit.activation(field)
            field.activation_levels[unit.name] = activation
            if activation < unit.threshold:
                continue
            deltas.append(unit.transform(field))

        for delta in deltas:
            self.apply_delta(field, delta)

        return deltas

    @staticmethod
    def apply_delta(field: FieldState, delta: FieldDelta) -> None:
        field.context_map.update(delta.context_updates)
        field.salience_map.update(delta.salience_updates)
        field.tension_map.update(delta.tension_updates)
        field.energy_map.update(delta.energy_updates)
        field.hypothesis_pool.extend(delta.hypotheses_add)
        if delta.hypotheses_remove:
            field.hypothesis_pool = [
                item
                for item in field.hypothesis_pool
                if item.get("id") not in set(delta.hypotheses_remove)
            ]
        field.stability_score += delta.stability_shift
        for event in delta.trace_events:
            normalized_event = {
                "seq": len(field.trace) + 1,
                "tick": event["tick"],
                "unit": event["unit"],
                "event_type": event["event_type"],
                "reason": event["reason"],
                "input_summary": event["input_summary"],
                "changes": event["changes"],
            }
            field.trace.append(normalized_event)

    @staticmethod
    def _next_seq(field: FieldState) -> int:
        return len(field.trace) + 1
