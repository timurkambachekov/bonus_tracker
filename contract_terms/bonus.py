class Bonus:
    """
    Represents a bonus accomplishment in a player's contract based on specific performance metrics.
    """
    def __init__(
        self,
        games: int = 0,
        minutes: int = 0,
        goals: int = 0,
        assists: int = 0,
        bonus_value: float = 0.0,
        bonus_type: str = "repeatable",
        competition: str = "official",
    ):
        """
        Initialize a Bonus instance.

        :param games: Number of games played
        :param minutes: Number of minutes played
        :param goals: Number of goals scored
        :param assists: Number of assists made
        :param bonus_value: The monetary value of the bonus (e.g., 50000.0 for €50,000)
        :param bonus_type: seasonal, one_time, or repeatable
        :param competition: scope of the bonus, e.g. official
        """
        self.games = games
        self.minutes = minutes
        self.goals = goals
        self.assists = assists
        self.bonus_value = bonus_value
        self.bonus_type = bonus_type
        self.competition = competition

    def __str__(self):
        conditions = []
        if self.games > 0:
            conditions.append(f"{self.games} games")
        if self.minutes > 0:
            conditions.append(f"{self.minutes} minutes")
        if self.goals > 0:
            conditions.append(f"{self.goals} goals")
        if self.assists > 0:
            conditions.append(f"{self.assists} assists")
        condition_str = ", ".join(conditions) if conditions else "No conditions"
        return (
            f"Bonus(type={self.bonus_type}, competition={self.competition}, "
            f"{condition_str}, bonus_value={self.bonus_value})"
        )

    def __repr__(self):
        return self.__str__()
