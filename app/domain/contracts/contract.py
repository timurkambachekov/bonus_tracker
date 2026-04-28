from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.contracts.bonus import Bonus


@dataclass
class Contract:
    id: int
    player_id: int
    club_id: int
    start_date: str
    end_date: str
    base_salary: float
    bonuses: list[Bonus] = field(default_factory=list)
    binding_bonus_groups: list[list[Bonus]] = field(default_factory=list)
    contract_text: str = ""

    def earned_bonuses(self, stats: dict[str, float | int]) -> list[Bonus]:
        earned = [bonus for bonus in self.bonuses if bonus.is_earned(stats)]
        if not self.binding_bonus_groups:
            return earned

        resolved: list[Bonus] = []
        bound_bonus_ids = set()

        for group in self.binding_bonus_groups:
            earned_group = [bonus for bonus in group if bonus in earned]
            bound_bonus_ids.update(bonus.id for bonus in group)
            if earned_group:
                resolved.append(max(earned_group, key=lambda bonus: bonus.payout))

        for bonus in earned:
            if bonus.id not in bound_bonus_ids:
                resolved.append(bonus)

        return resolved

    def total_bonus_payout(self, stats: dict[str, float | int]) -> float:
        return sum(bonus.payout for bonus in self.earned_bonuses(stats))
