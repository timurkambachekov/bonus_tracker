from app.domain import (
    Bonus,
    BonusCompetition,
    BonusType,
    Condition,
    ConditionDirection,
    ConditionOperator,
    ConditionType,
)

KNOWN_COMPETITIONS = {item.value for item in BonusCompetition}


def build_stats_snapshot(stats_row):
    return {
        "games_played": stats_row.get("squad_inclusions"),
        "starts": stats_row.get("starts"),
        "full_games": stats_row.get("full_games"),
        "minutes_played": stats_row.get("minutes_played"),
        "goals": stats_row.get("goals"),
        "assists": stats_row.get("assists"),
        "yellow_cards": stats_row.get("yellow_cards"),
        "red_cards": stats_row.get("red_cards"),
    }


def build_bonus_model(bonus_row):
    competition_code = bonus_row.get("competition_code") or "official"
    return Bonus(
        id=bonus_row.get("id") or 0,
        bonus_type=BonusType(bonus_row.get("bonus_type") or "seasonal"),
        competition=BonusCompetition(competition_code)
        if competition_code in KNOWN_COMPETITIONS
        else BonusCompetition.OFFICIAL,
        payout=float(bonus_row.get("bonus_value") or 0),
        conditions=[
            Condition(
                id=condition.get("id") or 0,
                condition_type=ConditionType(condition.get("condition_type") or "games_played"),
                direction=ConditionDirection(condition.get("direction") or ">="),
                threshold=float(condition.get("threshold") or 0),
            )
            for condition in (bonus_row.get("conditions") or [])
        ],
        operator=ConditionOperator(bonus_row.get("condition_operator") or "and"),
    )


def evaluate_bonus_progress(bonus, stats_row):
    bonus_model = build_bonus_model(bonus)
    stats_snapshot = build_stats_snapshot(stats_row)
    requirements = {
        condition["condition_type"]: float(condition.get("threshold") or 0)
        for condition in (bonus.get("conditions") or [])
        if condition.get("direction") == ">="
    }
    actuals = {key: stats_snapshot.get(key) for key in requirements}
    metric_progress = {}
    evaluable = True

    for key, required in requirements.items():
        actual = actuals.get(key)
        if actual is None:
            evaluable = False
            metric_progress[key] = None
            continue
        metric_progress[key] = round(min(float(actual) / required, 1.0), 4) if required else 1.0

    comparable = [value for value in metric_progress.values() if value is not None]
    completion_ratio = round(min(comparable), 4) if comparable else None
    achieved = evaluable and bonus_model.is_earned(stats_snapshot)
    times_achieved = None

    if bonus_model.bonus_type == BonusType.REPEATABLE:
        counts = []
        for key, required in requirements.items():
            if not required:
                continue
            actual = actuals.get(key)
            if actual is None:
                counts = None
                break
            counts.append(int(actual) // int(required))
        times_achieved = min(counts) if counts else 0

    payout_value = 0.0
    if achieved:
        payout_value = float(bonus.get("bonus_value") or 0)
        if bonus_model.bonus_type == BonusType.REPEATABLE:
            payout_value *= times_achieved or 0

    return {
        "season": stats_row.get("season"),
        "actuals": actuals,
        "requirements": requirements,
        "metric_progress": metric_progress,
        "completion_ratio": completion_ratio,
        "achieved": achieved,
        "evaluable": evaluable,
        "times_achieved": times_achieved,
        "payout_value": payout_value,
    }
