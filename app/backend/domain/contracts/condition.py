from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union

from app.backend.domain.contracts.enums import ConditionDirection, ConditionType

StatValue = Union[float, int]
Stats = dict[str, StatValue]


@dataclass
class Condition:
    id: int
    condition_type: ConditionType
    direction: ConditionDirection
    threshold: float

    def is_met(self, stats: Stats) -> bool:
        actual = self._actual_value(stats)
        if actual is None:
            return False

        if self.direction == ConditionDirection.GREATER_THAN:
            return actual > self.threshold
        if self.direction == ConditionDirection.LESS_THAN:
            return actual < self.threshold
        if self.direction == ConditionDirection.EQUAL_TO:
            return actual == self.threshold
        if self.direction == ConditionDirection.GREATER_THAN_OR_EQUAL_TO:
            return actual >= self.threshold
        return actual <= self.threshold

    def _actual_value(self, stats: Stats) -> Optional[StatValue]:
        if self.condition_type == ConditionType.GOAL_CONTRIBUTIONS:
            goals = stats.get("goals")
            assists = stats.get("assists")
            if goals is None or assists is None:
                return None
            return goals + assists

        stat_key_map = {
            ConditionType.GOALS: "goals",
            ConditionType.ASSISTS: "assists",
            ConditionType.MINUTES_PLAYED: "minutes_played",
            ConditionType.SQUAD_INCLUSIONS: "squad_inclusions",
            ConditionType.APPEARANCES: "appearances",
            ConditionType.GAMES_PLAYED: "appearances",
            ConditionType.STARTS: "starts",
            ConditionType.FULL_GAMES: "full_games",
            ConditionType.YELLOW_CARDS: "yellow_cards",
            ConditionType.RED_CARDS: "red_cards",
        }
        return stats.get(stat_key_map[self.condition_type])
