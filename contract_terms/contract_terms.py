from typing import List
from contract_terms.bonus import Bonus


class ContractTerms:
    """
    Represents a player's contract terms with a club, including a list of bonuses.
    """
    def __init__(self, player_id: int, club_id: int, base_salary: float, contract_start: str, contract_end: str, bonuses: List[Bonus]):
        """
        Initialize a ContractTerms instance.

        :param player_id: Unique identifier for the player
        :param club_id: Unique identifier for the club
        :param base_salary: Base annual salary (e.g., 1000000.0 for €1,000,000)
        :param contract_start: Start date of the contract (e.g., "2023-07-01")
        :param contract_end: End date of the contract (e.g., "2026-06-30")
        :param bonuses: List of Bonus instances for this contract
        """
        self.player_id = player_id
        self.club_id = club_id
        self.base_salary = base_salary
        self.contract_start = contract_start
        self.contract_end = contract_end
        self.bonuses = bonuses

    def total_bonus_value(self) -> float:
        """
        Calculate the total bonus value from all bonuses.

        :return: Sum of all bonus values
        """
        return sum(bonus.bonus_value for bonus in self.bonuses)

    def __str__(self):
        bonuses_str = "\n".join(f"  - {bonus}" for bonus in self.bonuses)
        return (
            f"ContractTerms(\n"
            f"  player_id={self.player_id},\n"
            f"  club_id={self.club_id},\n"
            f"  base_salary={self.base_salary},\n"
            f"  contract_start='{self.contract_start}',\n"
            f"  contract_end='{self.contract_end}',\n"
            f"  bonuses=[\n{bonuses_str}\n  ]\n"
            f")"
        )

    def __repr__(self):
        return self.__str__()
