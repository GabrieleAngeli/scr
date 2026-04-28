from __future__ import annotations

from abc import ABC, abstractmethod

from ..delta import FieldDelta
from ..field import FieldState


class CompetenceUnit(ABC):
    name: str
    threshold: float
    sensitivity: float
    weight: float
    decay: float

    @abstractmethod
    def activation(self, field: FieldState) -> float:
        raise NotImplementedError

    @abstractmethod
    def transform(self, field: FieldState) -> FieldDelta:
        raise NotImplementedError
