from enum import Enum


class BonusType(str, Enum):
    SEASONAL = "seasonal"
    ONE_TIME = "one_time"
    REPEATABLE = "repeatable"


class BonusCompetition(str, Enum):
    RU1 = "RU1"
    FA_CUP = "FA Cup"
    OFFICIAL = "official"


class ConditionOperator(str, Enum):
    AND = "and"
    OR = "or"


class ConditionDirection(str, Enum):
    GREATER_THAN = ">"
    LESS_THAN = "<"
    EQUAL_TO = "="
    GREATER_THAN_OR_EQUAL_TO = ">="
    LESS_THAN_OR_EQUAL_TO = "<="


class ConditionType(str, Enum):
    GOALS = "goals"
    ASSISTS = "assists"
    GOAL_CONTRIBUTIONS = "goal_contributions"
    MINUTES_PLAYED = "minutes_played"
    GAMES_PLAYED = "games_played"
    STARTS = "starts"
    FULL_GAMES = "full_games"
    YELLOW_CARDS = "yellow_cards"
    RED_CARDS = "red_cards"
