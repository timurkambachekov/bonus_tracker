from __future__ import annotations

from dataclasses import dataclass, field

from app.backend.domain.contracts.bonus import Bonus


@dataclass
class Contract:
    id: int
    player_id: int
    club_id: int
    start_date: str
    end_date: str
    base_salary: float
    bonuses: list[Bonus] = field(default_factory=list)
    contract_text: str = ""

    def earned_bonuses(self, stats: dict[str, float | int]) -> list[Bonus]:
        earned = [bonus for bonus in self.bonuses if bonus.is_earned(stats)]
        resolved: list[Bonus] = []
        grouped: dict[str, list[Bonus]] = {}

        for bonus in earned:
            if bonus.binding_group:
                grouped.setdefault(bonus.binding_group, []).append(bonus)
            else:
                resolved.append(bonus)

        for group in grouped.values():
            resolved.append(max(group, key=lambda bonus: bonus.payout))

        return resolved

    def total_bonus_payout(self, stats: dict[str, float | int]) -> float:
        return sum(bonus.payout for bonus in self.earned_bonuses(stats))
