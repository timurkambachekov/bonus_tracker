from app.backend.domain.contracts.bonus import Bonus
from app.backend.domain.contracts.condition import Condition
from app.backend.domain.contracts.contract import Contract
from app.backend.domain.contracts.enums import (
    BonusCompetition,
    BonusType,
    ConditionDirection,
    ConditionOperator,
    ConditionType,
)

bonuses = [
    Bonus(
        id=1,
        bonus_type=BonusType.SEASONAL,
        competition=BonusCompetition.RU1,
        payout=50_000,
        operator=ConditionOperator.AND,
        conditions=[
            Condition(
                id=1,
                condition_type=ConditionType.GOALS,
                direction=ConditionDirection.GREATER_THAN_OR_EQUAL_TO,
                threshold=10,
            ),
            Condition(
                id=2,
                condition_type=ConditionType.ASSISTS,
                direction=ConditionDirection.GREATER_THAN_OR_EQUAL_TO,
                threshold=5,
            ),
        ],
    ),
    Bonus(
        id=2,
        bonus_type=BonusType.ONE_TIME,
        competition=BonusCompetition.FA_CUP,
        payout=20_000.0,
        operator=ConditionOperator.OR,
        conditions=[
            Condition(
                id=3,
                condition_type=ConditionType.GAMES_PLAYED,
                direction=ConditionDirection.GREATER_THAN_OR_EQUAL_TO,
                threshold=5,
            ),
            Condition(
                id=4,
                condition_type=ConditionType.MINUTES_PLAYED,
                direction=ConditionDirection.GREATER_THAN_OR_EQUAL_TO,
                threshold=300,
            ),
        ],
    ),
]

contract = Contract(
    id=1,
    player_id=1,
    club_id=1,
    start_date="2023-01-01",
    end_date="2025-12-31",
    base_salary=1_000_000.0,
    bonuses=bonuses,
    contract_text="Sample contract text",
)
