from datetime import date
import random

from app.backend.db import get_connection

DEFAULT_CONTRACT_START_MONTH = 7
DEFAULT_CONTRACT_START_DAY = 1
DEFAULT_CONTRACT_END_MONTH = 6
DEFAULT_CONTRACT_END_DAY = 30
MIN_BASE_SALARY_RUB = 300_000
MAX_BASE_SALARY_RUB = 8_000_000
MINUTE_BINDING_GROUP = "seasonal_minutes_ladder"
RPL_COMPETITION_CODE = "RU1"


def stat_value(row: dict, key: str) -> int:
    return int(row.get(key) or 0)


def seeded_random(*parts) -> random.Random:
    return random.Random(":".join(str(part) for part in parts))


def round_rub(amount: float, step: int = 5_000) -> int:
    return int(round(amount / step) * step)


def clamp(value: float, lower: int, upper: int) -> int:
    return max(lower, min(int(value), upper))


def estimate_base_salary(player: dict) -> int:
    market_value = float(player.get("market_value_eur") or 500_000)
    minutes_played = stat_value(player, "minutes_played")
    starts = stat_value(player, "starts")
    goal_contributions = stat_value(player, "goals") + stat_value(player, "assists")
    rng = seeded_random("salary", player["player_id"])

    estimate = 250_000
    estimate += market_value / 4.5
    estimate += minutes_played * 175
    estimate += starts * 25_000
    estimate += goal_contributions * 60_000
    estimate *= rng.uniform(0.9, 1.15)

    return clamp(round_rub(estimate, step=25_000), MIN_BASE_SALARY_RUB, MAX_BASE_SALARY_RUB)


def contract_period(player: dict) -> tuple[str, str]:
    season = int(player.get("season") or date.today().year)
    rng = seeded_random("contract-length", player["player_id"])
    duration_years = 2 if rng.random() < 0.7 else 3

    start_date = date(season, DEFAULT_CONTRACT_START_MONTH, DEFAULT_CONTRACT_START_DAY)
    end_date = date(
        season + duration_years,
        DEFAULT_CONTRACT_END_MONTH,
        DEFAULT_CONTRACT_END_DAY,
    )
    return start_date.isoformat(), end_date.isoformat()


def monthly_bonus_amount(base_salary: int, rng: random.Random, lower: float, upper: float) -> int:
    return round_rub(base_salary * rng.uniform(lower, upper), step=10_000)


def build_bonus_specs(player: dict, base_salary: int) -> list[dict]:
    rng = seeded_random("bonuses", player["player_id"])
    bonuses = []

    bonuses.append(
        {
            "bonus_category": "squad_inclusions",
            "bonus_type": "seasonal",
            "binding_group": None,
            "condition_operator": "and",
            "bonus_value": monthly_bonus_amount(base_salary, rng, 0.12, 0.22),
            "conditions": [("squad_inclusions", ">=", 5)],
        }
    )

    minute_tiers = [
        ("minutes_750_1500", 750, 1500, monthly_bonus_amount(base_salary, rng, 0.18, 0.3)),
        ("minutes_1500_2100", 1500, 2100, monthly_bonus_amount(base_salary, rng, 0.28, 0.45)),
        ("minutes_2100_plus", 2100, None, monthly_bonus_amount(base_salary, rng, 0.42, 0.65)),
    ]

    for bonus_category, lower_bound, upper_bound, amount in minute_tiers:
        conditions = [("minutes_played", ">=", lower_bound)]
        if upper_bound is not None:
            conditions.append(("minutes_played", "<", upper_bound))
        bonuses.append(
            {
                "bonus_category": bonus_category,
                "bonus_type": "seasonal",
                "binding_group": MINUTE_BINDING_GROUP,
                "condition_operator": "and",
                "bonus_value": amount,
                "conditions": conditions,
            }
        )

    contribution_threshold = 3 if stat_value(player, "goals") + stat_value(player, "assists") < 7 else 5
    bonuses.append(
        {
            "bonus_category": "goal_contributions",
            "bonus_type": "seasonal",
            "binding_group": None,
            "condition_operator": "and",
            "bonus_value": round_rub(rng.uniform(150_000, 550_000), step=10_000),
            "conditions": [("goal_contributions", ">=", contribution_threshold)],
        }
    )

    return bonuses


def build_contract_text(start_date: str, end_date: str, bonuses: list[dict]) -> str:
    clause_lines = []

    for bonus in bonuses:
        amount = f"{int(bonus['bonus_value']):,}".replace(",", " ")
        if bonus["bonus_category"] == "squad_inclusions":
            clause_lines.append(
                f"If the Player is included in the matchday squad at least 5 times in Russian Premier League matches during one sporting season, "
                f"the Player shall be granted a monthly incentive payment in the amount of {amount} RUB."
            )
        elif bonus["bonus_category"] == "minutes_750_1500":
            clause_lines.append(
                f"If the Player records at least 750, but fewer than 1,500, minutes of playing time in Russian Premier League matches during one sporting season, "
                f"the base monthly incentive payment shall be increased to {amount} RUB."
            )
        elif bonus["bonus_category"] == "minutes_1500_2100":
            clause_lines.append(
                f"If the Player records at least 1,500, but fewer than 2,100, minutes of playing time in Russian Premier League matches during one sporting season, "
                f"the base monthly incentive payment shall be increased to {amount} RUB."
            )
        elif bonus["bonus_category"] == "minutes_2100_plus":
            clause_lines.append(
                f"If the Player records at least 2,100 minutes of playing time in Russian Premier League matches during one sporting season, "
                f"the base monthly incentive payment shall be increased to {amount} RUB."
            )
        elif bonus["bonus_category"] == "goal_contributions":
            threshold = int(bonus["conditions"][0][2])
            clause_lines.append(
                f"If the Player records at least {threshold} goal contributions in one sporting season, "
                f"the Player shall receive a seasonal bonus in the amount of {amount} RUB."
            )

    clause_lines.append(
        "Bonuses under clauses 3.2-3.4 are non-cumulative; only the single highest applicable bonus shall be paid."
    )

    return (
        f"Contract term: {start_date} to {end_date}. "
        + " ".join(clause_lines)
    )


def fetch_rpl_competition(cursor) -> dict:
    cursor.execute(
        """
        SELECT id, transfermarkt_code, name, country, season
        FROM competitions
        WHERE transfermarkt_code = %s
        ORDER BY season DESC, id DESC
        LIMIT 1;
        """,
        (RPL_COMPETITION_CODE,),
    )
    competition = cursor.fetchone()
    if not competition:
        raise ValueError("Russian Premier League competition not found in competitions table")
    return competition


def fetch_player_profiles(cursor) -> list[dict]:
    cursor.execute(
        """
        SELECT
            p.id AS player_id,
            p.transfermarkt_player_id,
            p.player_name,
            p.position,
            p.market_value_eur,
            p.club_id,
            c.club_name,
            c.competition_id,
            comp.season,
            stats.squad_inclusions,
            stats.appearances,
            stats.starts,
            stats.full_games,
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
        WHERE comp.transfermarkt_code = %s
        ORDER BY p.id;
        """,
        (RPL_COMPETITION_CODE,),
    )
    return cursor.fetchall()


def clear_contract_tables(cursor) -> None:
    cursor.execute("DELETE FROM contract_bonus_binding_group_members;")
    cursor.execute("DELETE FROM contract_bonus_binding_groups;")
    cursor.execute("DELETE FROM contract_bonus_conditions;")
    cursor.execute("DELETE FROM contract_bonuses;")
    cursor.execute("DELETE FROM contracts;")


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
            bonus_type,
            competition_id,
            condition_operator,
            bonus_value,
            display_order
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id;
        """,
        (
            contract_id,
            bonus["bonus_type"],
            competition_id,
            bonus["condition_operator"],
            bonus["bonus_value"],
            display_order,
        ),
    )
    return cursor.fetchone()["id"]


def ensure_binding_group(cursor, contract_id: int, group_name: str) -> int:
    cursor.execute(
        """
        SELECT id
        FROM contract_bonus_binding_groups
        WHERE contract_id = %s AND group_name = %s;
        """,
        (contract_id, group_name),
    )
    row = cursor.fetchone()
    if row:
        return row["id"]

    cursor.execute(
        """
        INSERT INTO contract_bonus_binding_groups (
            contract_id,
            group_name,
            display_order
        )
        VALUES (
            %s,
            %s,
            COALESCE(
                (
                    SELECT MAX(display_order) + 1
                    FROM contract_bonus_binding_groups
                    WHERE contract_id = %s
                ),
                1
            )
        )
        RETURNING id;
        """,
        (contract_id, group_name, contract_id),
    )
    return cursor.fetchone()["id"]


def insert_bonus_binding(cursor, binding_group_id: int, contract_bonus_id: int) -> None:
    cursor.execute(
        """
        INSERT INTO contract_bonus_binding_group_members (
            binding_group_id,
            contract_bonus_id
        )
        VALUES (%s, %s);
        """,
        (binding_group_id, contract_bonus_id),
    )


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
    print("Connecting to database")
    with get_connection() as connection:
        print("Connected to database")
        with connection.cursor() as cursor:
            # clear_contract_tables(cursor)
            print("Fetching competition")
            rpl_competition = fetch_rpl_competition(cursor)
            print(f"Loaded competition {rpl_competition['transfermarkt_code']}")
            print("Fetching player profiles")
            players = fetch_player_profiles(cursor)
            print(f"Loaded {len(players)} player profiles")

            contract_count = 0
            bonus_count = 0
            condition_count = 0

            for index, player in enumerate(players, start=1):
                base_salary = estimate_base_salary(player)
                start_date, end_date = contract_period(player)
                bonuses = build_bonus_specs(player, base_salary)
                contract_text = build_contract_text(start_date, end_date, bonuses)
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
                        competition_id=rpl_competition["id"],
                        display_order=display_order,
                        bonus=bonus,
                    )
                    bonus_count += 1
                    if bonus["binding_group"]:
                        binding_group_id = ensure_binding_group(
                            cursor,
                            contract_id=contract_id,
                            group_name=bonus["binding_group"],
                        )
                        insert_bonus_binding(
                            cursor,
                            binding_group_id=binding_group_id,
                            contract_bonus_id=bonus_id,
                        )
                    condition_count += insert_bonus_conditions(
                        cursor,
                        contract_bonus_id=bonus_id,
                        conditions=bonus["conditions"],
                    )

                if index % 25 == 0:
                    print(f"Processed {index}/{len(players)} players")

        print("Committing transaction")
        connection.commit()
        print("Commit complete")

    print(
        f"Generated {contract_count} contracts, {bonus_count} seasonal bonuses, "
        f"and {condition_count} bonus conditions"
    )


def main():
    load_league_contract_terms()


if __name__ == "__main__":
    main()
