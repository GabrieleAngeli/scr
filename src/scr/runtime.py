from __future__ import annotations

from dataclasses import dataclass, field

from .delta import FieldDelta
from .field import FieldState
from .units.base import CompetenceUnit


@dataclass
class RuntimeConfig:
    max_ticks: int = 1


class ActivationPolicy:
    def select_units(self, field: FieldState, units: list[CompetenceUnit]) -> list[CompetenceUnit]:
        available = {unit.name: unit for unit in units}
        selected_name = self._select_unit_name(field, set(available))
        if selected_name is None:
            return []
        return [available[selected_name]]

    @staticmethod
    def _select_unit_name(field: FieldState, available_unit_names: set[str]) -> str | None:
        if not field.context_map and "input_structuring" in available_unit_names:
            return "input_structuring"
        if field.context_map.get("code_artifact") is None and "standardization" in available_unit_names:
            return "standardization"
        if not field.hypothesis_pool and "divergence" in available_unit_names:
            return "divergence"
        if field.hypothesis_pool and not field.context_map.get("active_hypotheses") and "competition" in available_unit_names:
            return "competition"
        if (
            field.context_map.get("active_hypotheses")
            and "validation_results" not in field.context_map
            and "validation" in available_unit_names
        ):
            return "validation"
        if "validation_results" in field.context_map and field.outcome is None and "consolidation" in available_unit_names:
            return "consolidation"
        if not field.hypothesis_pool and field.outcome is None and "consolidation" in available_unit_names:
            return "consolidation"
        return None


@dataclass
class SCRRuntime:
    units: list[CompetenceUnit]
    config: RuntimeConfig = field(default_factory=RuntimeConfig)
    activation_policy: ActivationPolicy = field(default_factory=ActivationPolicy)

    def run(self, field: FieldState) -> FieldState:
        while field.tick < self.config.max_ticks:
            field.tick += 1
            active_deltas = self.run_tick(field)
            if field.outcome is not None or not active_deltas:
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

        selected_units = self.activation_policy.select_units(field, self.units)
        field.trace.append(
            {
                "seq": self._next_seq(field),
                "tick": field.tick,
                "unit": "runtime",
                "event_type": "activation_policy",
                "reason": "units selected from field state",
                "input_summary": {
                    "available_units": [unit.name for unit in self.units],
                },
                "changes": {
                    "selected_units": [unit.name for unit in selected_units],
                },
            }
        )

        for unit in selected_units:
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
        if delta.hypotheses_replace is not None:
            field.hypothesis_pool = list(delta.hypotheses_replace)
        field.hypothesis_pool.extend(delta.hypotheses_add)
        if delta.hypotheses_remove:
            field.hypothesis_pool = [
                item
                for item in field.hypothesis_pool
                if item.get("id") not in set(delta.hypotheses_remove)
            ]
        field.stability_score += delta.stability_shift
        if delta.outcome is not None:
            field.outcome = delta.outcome
        if delta.selected_hypothesis is not None:
            field.selected_hypothesis = delta.selected_hypothesis
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
