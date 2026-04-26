def threshold_value(value):
    if value in (None, ""):
        return 0
    return value


def infer_starts(stats_row):
    appearances = stats_row.get("appearances")
    substitutions_on = stats_row.get("substitutions_on")
    if appearances is None or substitutions_on is None:
        return None
    return max(int(appearances) - int(substitutions_on), 0)


def calculate_repeatable_count(requirements, actuals):
    goals_required = requirements.get("goals") or 0
    assists_required = requirements.get("assists") or 0
    if goals_required and assists_required:
        total_required = goals_required + assists_required
        total_actual = (actuals.get("goals") or 0) + (actuals.get("assists") or 0)
        return total_actual // total_required

    counts = []
    for metric, required in requirements.items():
        if not required:
            continue
        actual = actuals.get(metric)
        if actual is None:
            return None
        counts.append(int(actual) // int(required))
    return min(counts) if counts else 0


def calculate_bonus_payout(bonus_type, bonus_value, achieved, times_achieved):
    if bonus_value in (None, ""):
        return 0
    bonus_value = float(bonus_value)
    if bonus_type == "repeatable":
        return bonus_value * (times_achieved or 0)
    return bonus_value if achieved else 0


def evaluate_bonus_progress(bonus, stats_row):
    bonus_type = bonus.get("bonus_type") or "repeatable"
    requirements = {
        "games": threshold_value(bonus.get("games")),
        "starts": threshold_value(bonus.get("starts")),
        "minutes": threshold_value(bonus.get("minutes")),
        "goals": threshold_value(bonus.get("goals")),
        "assists": threshold_value(bonus.get("assists")),
    }
    actuals = {
        "games": stats_row.get("squad_inclusions"),
        "starts": infer_starts(stats_row),
        "minutes": stats_row.get("minutes_played"),
        "goals": stats_row.get("goals"),
        "assists": stats_row.get("assists"),
    }

    metric_progress = {}
    achieved = True
    evaluable = True

    for metric, required in requirements.items():
        if not required:
            continue
        actual = actuals.get(metric)
        if actual is None:
            evaluable = False
            achieved = False
            metric_progress[metric] = None
            continue
        ratio = min(float(actual) / float(required), 1.0)
        metric_progress[metric] = round(ratio, 4)
        if actual < required:
            achieved = False

    comparable = [value for value in metric_progress.values() if value is not None]
    completion_ratio = round(min(comparable), 4) if comparable else None
    times_achieved = (
        calculate_repeatable_count(requirements, actuals)
        if bonus_type == "repeatable"
        else None
    )
    payout_value = calculate_bonus_payout(
        bonus_type=bonus_type,
        bonus_value=bonus.get("bonus_value"),
        achieved=achieved and evaluable,
        times_achieved=times_achieved,
    )

    return {
        "season": stats_row.get("season"),
        "actuals": actuals,
        "requirements": requirements,
        "metric_progress": metric_progress,
        "completion_ratio": completion_ratio,
        "achieved": achieved and evaluable,
        "evaluable": evaluable,
        "times_achieved": times_achieved,
        "payout_value": payout_value,
    }
