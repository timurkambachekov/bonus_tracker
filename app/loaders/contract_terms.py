from datetime import date
import random
from typing import Optional

from app.db import get_connection

DEFAULT_CONTRACT_START_MONTH = 7
DEFAULT_CONTRACT_START_DAY = 1
DEFAULT_CONTRACT_END_MONTH = 6
DEFAULT_CONTRACT_END_DAY = 30
MIN_BASE_SALARY_RUB = 300_000
MAX_BASE_SALARY_RUB = 8_000_000


def stat_value(row: dict, key: str) -> int:
    return int(row.get(key) or 0)


def seeded_random(*parts) -> random.Random:
    return random.Random(":".join(str(part) for part in parts))


def round_rub(amount: float, step: int = 5_000) -> int:
    return int(round(amount / step) * step)


def clamp(value: float, lower: int, upper: int) -> int:
    return max(lower, min(int(value), upper))


def infer_role(position: str) -> str:
    normalized = (position or "").lower()
    if "goalkeeper" in normalized:
        return "goalkeeper"
    if any(token in normalized for token in ("centre-back", "back", "defender")):
        return "defender"
    if any(token in normalized for token in ("winger", "forward", "striker", "attack")):
        return "attacker"
    return "midfielder"


def estimate_base_salary(player: dict) -> int:
    market_value = float(player.get("market_value_eur") or 500_000)
    minutes_played = stat_value(player, "minutes_played")
    goals = stat_value(player, "goals")
    assists = stat_value(player, "assists")
    starts = stat_value(player, "starts")
    role = infer_role(player.get("position"))

    estimate = 250_000
    estimate += market_value / 4.5
    estimate += min(minutes_played, 2_400) * 175
    estimate += starts * 20_000

    if role == "attacker":
        estimate += goals * 90_000 + assists * 55_000
    elif role == "midfielder":
        estimate += goals * 70_000 + assists * 65_000
    elif role == "defender":
        estimate += goals * 110_000 + assists * 40_000
    else:
        estimate += goals * 150_000

    rng = seeded_random("salary", player["player_id"], player.get("transfermarkt_player_id"))
    estimate *= rng.uniform(0.9, 1.15)
    return clamp(round_rub(estimate, step=25_000), MIN_BASE_SALARY_RUB, MAX_BASE_SALARY_RUB)


def contract_period(player: dict) -> tuple[str, str]:
    season = int(player.get("season") or date.today().year)
    minutes_played = stat_value(player, "minutes_played")
    market_value = float(player.get("market_value_eur") or 0)
    rng = seeded_random("contract-length", player["player_id"])

    if minutes_played >= 1_800 or market_value >= 6_000_000:
        duration_years = 2 if rng.random() < 0.75 else 3
    elif minutes_played >= 600 or market_value >= 2_000_000:
        duration_years = 2 if rng.random() < 0.45 else 1
    else:
        duration_years = 1

    start_date = date(season, DEFAULT_CONTRACT_START_MONTH, DEFAULT_CONTRACT_START_DAY)
    end_date = date(
        season + duration_years,
        DEFAULT_CONTRACT_END_MONTH,
        DEFAULT_CONTRACT_END_DAY,
    )
    return start_date.isoformat(), end_date.isoformat()


def seasonal_minute_thresholds(player: dict) -> list[int]:
    minutes_played = stat_value(player, "minutes_played")
    if minutes_played >= 2_000:
        return [750, 1_500, 2_100]
    if minutes_played >= 1_200:
        return [500, 1_000, 1_500]
    if minutes_played >= 500:
        return [300, 600, 900]
    return [150, 300]


def starts_threshold(player: dict) -> Optional[int]:
    starts = stat_value(player, "starts")
    if starts >= 22:
        return 20
    if starts >= 14:
        return 12
    if starts >= 8:
        return 8
    return None


def full_games_threshold(player: dict) -> Optional[int]:
    full_games = stat_value(player, "full_games")
    if full_games >= 18:
        return 15
    if full_games >= 10:
        return 8
    return None


def goals_threshold(player: dict) -> Optional[int]:
    goals = stat_value(player, "goals")
    if goals >= 12:
        return 10
    if goals >= 7:
        return 5
    if goals >= 3:
        return 3
    return None


def assists_threshold(player: dict) -> Optional[int]:
    assists = stat_value(player, "assists")
    if assists >= 10:
        return 8
    if assists >= 6:
        return 5
    if assists >= 3:
        return 3
    return None


def bonus_value(player: dict, bonus_key: str, base_salary: int) -> int:
    role = infer_role(player.get("position"))
    rng = seeded_random("bonus", player["player_id"], bonus_key)

    if bonus_key.startswith("seasonal_minutes"):
        return round_rub(base_salary * rng.uniform(0.35, 1.1))
    if bonus_key == "seasonal_starts":
        return round_rub(base_salary * rng.uniform(0.3, 0.8))
    if bonus_key == "seasonal_full_games":
        return round_rub(base_salary * rng.uniform(0.3, 0.75))
    if bonus_key == "seasonal_goals":
        if role == "defender":
            return round_rub(rng.uniform(180_000, 450_000))
        if role == "attacker":
            return round_rub(rng.uniform(220_000, 650_000))
        return round_rub(rng.uniform(180_000, 500_000))
    if bonus_key == "seasonal_assists":
        if role == "defender":
            return round_rub(rng.uniform(120_000, 300_000))
        return round_rub(rng.uniform(150_000, 420_000))
    return round_rub(base_salary * 0.2)


def build_bonus_specs(player: dict, base_salary: int) -> list[dict]:
    role = infer_role(player.get("position"))
    bonuses = []

    for threshold in seasonal_minute_thresholds(player):
        bonuses.append(
            {
                "clause_key": f"seasonal_minutes_{threshold}",
                "bonus_type": "seasonal",
                "condition_operator": "and",
                "conditions": [("minutes_played", ">=", threshold)],
            }
        )

    starts_target = starts_threshold(player)
    if starts_target is not None:
        bonuses.append(
            {
                "clause_key": "seasonal_starts",
                "bonus_type": "seasonal",
                "condition_operator": "and",
                "conditions": [("starts", ">=", starts_target)],
            }
        )

    goals_target = goals_threshold(player)
    if goals_target is not None and role in {"attacker", "midfielder", "defender"}:
        bonuses.append(
            {
                "clause_key": "seasonal_goals",
                "bonus_type": "seasonal",
                "condition_operator": "and",
                "conditions": [("goals", ">=", goals_target)],
            }
        )

    assists_target = assists_threshold(player)
    if assists_target is not None and role in {"attacker", "midfielder", "defender"}:
        bonuses.append(
            {
                "clause_key": "seasonal_assists",
                "bonus_type": "seasonal",
                "condition_operator": "and",
                "conditions": [("assists", ">=", assists_target)],
            }
        )

    full_games_target = full_games_threshold(player)
    if full_games_target is not None and role in {"goalkeeper", "defender"}:
        bonuses.append(
            {
                "clause_key": "seasonal_full_games",
                "bonus_type": "seasonal",
                "condition_operator": "and",
                "conditions": [("full_games", ">=", full_games_target)],
            }
        )

    for bonus in bonuses:
        bonus["bonus_value"] = bonus_value(player, bonus["clause_key"], base_salary)

    return bonuses


def build_contract_text(player: dict, start_date: str, end_date: str, bonuses: list[dict]) -> str:
    bonus_keys = ", ".join(bonus["clause_key"] for bonus in bonuses[:4])
    return (
        f"Employment term: {start_date} to {end_date}. "
        f"Variable compensation includes seasonal bonuses tied to {bonus_keys}."
    )


def fetch_player_profiles(cursor) -> list[dict]:
    cursor.execute(
        """
        SELECT
            p.id AS player_id,
            p.transfermarkt_player_id,
            p.player_name,
            p.position,
            p.market_value_eur,
            p.date_of_birth,
            p.club_id,
            c.club_name,
            c.competition_id,
            comp.season,
            stats.squad_inclusions,
            stats.appearances,
            stats.starts,
            stats.full_games,
            stats.substitutions_on,
            stats.substitutions_off,
            stats.minutes_played,
            stats.goals,
            stats.assists,
            stats.yellow_cards,
            stats.red_cards,
            stats.ppg
        FROM players p
        JOIN clubs c ON c.id = p.club_id
        JOIN competitions comp ON comp.id = c.competition_id
        LEFT JOIN LATERAL (
            SELECT *
            FROM player_season_stats s
            WHERE s.player_id = p.id
            ORDER BY s.season DESC, s.created_at DESC, s.id DESC
            LIMIT 1
        ) stats ON TRUE
        ORDER BY p.id;
        """
    )
    return cursor.fetchall()


def insert_contract(cursor, player: dict, base_salary: int, start_date: str, end_date: str, contract_text: str) -> int:
    cursor.execute(
        """
        INSERT INTO contracts (
            player_id,
            club_id,
            base_salary,
            contract_start,
            contract_end,
            contract_text
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id;
        """,
        (
            player["player_id"],
            player["club_id"],
            base_salary,
            start_date,
            end_date,
            contract_text,
        ),
    )
    return cursor.fetchone()["id"]


def insert_bonus(cursor, contract_id: int, competition_id: int, display_order: int, bonus: dict) -> int:
    cursor.execute(
        """
        INSERT INTO contract_bonuses (
            contract_id,
            clause_key,
            bonus_type,
            competition_id,
            condition_operator,
            bonus_value,
            display_order
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
        """,
        (
            contract_id,
            bonus["clause_key"],
            bonus["bonus_type"],
            competition_id,
            bonus["condition_operator"],
            bonus["bonus_value"],
            display_order,
        ),
    )
    return cursor.fetchone()["id"]


def insert_bonus_conditions(cursor, contract_bonus_id: int, conditions: list[tuple[str, str, int]]) -> int:
    count = 0
    for display_order, (condition_type, direction, threshold) in enumerate(conditions, start=1):
        cursor.execute(
            """
            INSERT INTO contract_bonus_conditions (
                contract_bonus_id,
                condition_type,
                direction,
                threshold,
                display_order
            )
            VALUES (%s, %s, %s, %s, %s);
            """,
            (
                contract_bonus_id,
                condition_type,
                direction,
                threshold,
                display_order,
            ),
        )
        count += 1
    return count


def load_league_contract_terms() -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            players = fetch_player_profiles(cursor)

            contract_count = 0
            bonus_count = 0
            condition_count = 0

            for player in players:
                base_salary = estimate_base_salary(player)
                start_date, end_date = contract_period(player)
                bonuses = build_bonus_specs(player, base_salary)
                contract_text = build_contract_text(player, start_date, end_date, bonuses)
                contract_id = insert_contract(
                    cursor,
                    player=player,
                    base_salary=base_salary,
                    start_date=start_date,
                    end_date=end_date,
                    contract_text=contract_text,
                )
                contract_count += 1

                for display_order, bonus in enumerate(bonuses, start=1):
                    bonus_id = insert_bonus(
                        cursor,
                        contract_id=contract_id,
                        competition_id=player["competition_id"],
                        display_order=display_order,
                        bonus=bonus,
                    )
                    bonus_count += 1
                    condition_count += insert_bonus_conditions(
                        cursor,
                        contract_bonus_id=bonus_id,
                        conditions=bonus["conditions"],
                    )

        connection.commit()

    print(
        f"Generated {contract_count} contracts, {bonus_count} seasonal bonuses, "
        f"and {condition_count} bonus conditions"
    )


def main():
    load_league_contract_terms()


if __name__ == "__main__":
    main()
