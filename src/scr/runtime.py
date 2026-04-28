from __future__ import annotations

from dataclasses import dataclass, field

from .delta import FieldDelta
from .field import FieldState
from .units.base import CompetenceUnit


@dataclass
class RuntimeConfig:
    max_ticks: int = 1


class ActivationPolicy:
    def select_next_unit(self, field: FieldState, available_units: dict[str, CompetenceUnit]) -> CompetenceUnit | None:
        selected_name = self._select_unit_name(field, set(available_units))
        if selected_name is None:
            return None
        return available_units[selected_name]

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
    unit_by_name: dict[str, CompetenceUnit] = field(init=False)

    def __post_init__(self) -> None:
        self.unit_by_name = {unit.name: unit for unit in self.units}

    def run(self, field: FieldState) -> FieldState:
        while True:
            if field.outcome is not None:
                break
            if field.tick >= self.config.max_ticks:
                break
            selected_unit = self.activation_policy.select_next_unit(field, self.unit_by_name)
            if selected_unit is None:
                break
            field.tick += 1
            self.run_tick(field, selected_unit)
        return field

    def run_tick(self, field: FieldState, selected_unit: CompetenceUnit) -> FieldDelta | None:
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

        field.trace.append(
            {
                "seq": self._next_seq(field),
                "tick": field.tick,
                "unit": "runtime",
                "event_type": "activation_policy",
                "reason": "next unit selected from field state",
                "input_summary": {
                    "available_units": list(self.unit_by_name),
                },
                "changes": {
                    "selected_unit": selected_unit.name,
                },
            }
        )

        activation = selected_unit.activation(field)
        field.activation_levels[selected_unit.name] = activation
        if activation < selected_unit.threshold:
            field.trace.append(
                {
                    "seq": self._next_seq(field),
                    "tick": field.tick,
                    "unit": "runtime",
                    "event_type": "unit_skipped",
                    "reason": "selected unit was below activation threshold",
                    "input_summary": {
                        "selected_unit": selected_unit.name,
                        "activation": activation,
                        "threshold": selected_unit.threshold,
                    },
                    "changes": {},
                }
            )
            return None

        delta = selected_unit.transform(field)
        self.apply_delta(field, delta)
        return delta

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
