from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union

from app.domain.contracts.condition import Condition
from app.domain.contracts.enums import BonusCompetition, BonusType, ConditionOperator

StatValue = Union[float, int]
Stats = dict[str, StatValue]


@dataclass
class Bonus:
    id: int
    bonus_type: BonusType
    competition: BonusCompetition
    payout: float
    conditions: list[Condition]
    binding_group: Optional[str] = None
    operator: ConditionOperator = ConditionOperator.AND

    def is_earned(self, stats: Stats) -> bool:
        if not self.conditions:
            return False

        results = [condition.is_met(stats) for condition in self.conditions]
        if self.operator == ConditionOperator.OR:
            return any(results)
        return all(results)
