def format_market_value(value):
    if value is None:
        return "-"
    return f"EUR {value:,.0f}"


def format_money(value):
    if value is None:
        return "-"
    return f"EUR {value:,.0f}"


def format_bonus_title(index, bonus):
    return f"Bonus {index}: {bonus.bonus_type.value}"


def build_stats_row(stats):
    return {
        "Season": stats.get("season"),
        "Competition ID": stats.get("competition_id"),
        "Squad Inclusions": stats.get("squad_inclusions"),
        "Appearances": stats.get("appearances"),
        "Starts": stats.get("starts"),
        "Full Games": stats.get("full_games"),
        "Sub On": stats.get("substitutions_on"),
        "Sub Off": stats.get("substitutions_off"),
        "Minutes": stats.get("minutes_played"),
        "Goals": stats.get("goals"),
        "Assists": stats.get("assists"),
        "Yellow Cards": stats.get("yellow_cards"),
        "Second Yellow": stats.get("second_yellow_cards"),
        "Red Cards": stats.get("red_cards"),
        "PPG": stats.get("ppg"),
    }
