from typing import Optional

from app.backend.domain import Bonus, BonusType


def condition_actual_value(condition, stats: dict) -> Optional[float]:
    actual = condition._actual_value(stats)
    if actual is None:
        return None
    return float(actual)


def condition_progress(condition, stats: dict) -> Optional[float]:
    actual = condition_actual_value(condition, stats)
    if actual is None:
        return None

    threshold = float(condition.threshold)
    if threshold == 0:
        return 1.0

    if condition.direction.value in (">=", ">"):
        return round(min(actual / threshold, 1.0), 4)

    if condition.direction.value in ("<=", "<"):
        if actual <= threshold:
            return 1.0
        return round(max(1 - ((actual - threshold) / threshold), 0.0), 4)

    return 1.0 if actual == threshold else 0.0


def calculate_bonus_progress(bonus: Bonus, stats: dict) -> dict:
    requirements = {}
    actuals = {}
    metric_progress = {}
    evaluable = True

    for condition in bonus.conditions:
        key = condition.condition_type.value
        requirements[key] = float(condition.threshold)
        actual = condition_actual_value(condition, stats)
        actuals[key] = actual
        progress = condition_progress(condition, stats)
        metric_progress[key] = progress
        if actual is None:
            evaluable = False

    comparable = [value for value in metric_progress.values() if value is not None]
    if not comparable:
        completion_ratio = None
    elif bonus.operator.value == "or":
        completion_ratio = round(max(comparable), 4)
    else:
        completion_ratio = round(min(comparable), 4)

    achieved = evaluable and bonus.is_earned(stats)
    times_achieved = None
    payout_value = 0.0

    if bonus.bonus_type == BonusType.REPEATABLE:
        counts = []
        for condition in bonus.conditions:
            threshold = float(condition.threshold)
            actual = actuals.get(condition.condition_type.value)
            if actual is None or threshold <= 0:
                continue
            if condition.direction.value not in (">=", ">"):
                continue
            counts.append(int(actual) // int(threshold))
        times_achieved = min(counts) if counts else 0

    if achieved:
        payout_value = float(bonus.payout)
        if bonus.bonus_type == BonusType.REPEATABLE:
            payout_value *= times_achieved or 0

    return {
        "actuals": actuals,
        "requirements": requirements,
        "metric_progress": metric_progress,
        "completion_ratio": completion_ratio,
        "achieved": achieved,
        "evaluable": evaluable,
        "times_achieved": times_achieved,
        "payout_value": payout_value,
    }


def evaluate_bonus_progress(bonus: Bonus, stats: dict) -> dict:
    return calculate_bonus_progress(bonus, stats)
