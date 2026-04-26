import csv
import random
from datetime import datetime
from pathlib import Path

from app.db import get_connection

DEFAULT_CONTRACT_START = "2025-07-01"
DEFAULT_CONTRACT_END = "2026-06-30"
BASE_SALARY_RANGE_RUB = (300_000, 8_000_000)

# Simplified representation of the bonus clauses.
# Clauses 4.1 and 4.2 are stored separately even though the contract text says
# they should not be summed; that exclusivity would need to be handled by payout logic.
BONUS_TEMPLATES = [
    {"bonus_key": "seasonal_games", "bonus_type": "seasonal", "competition": "official", "games": 5, "starts": 0, "minutes": 0, "goals": 0, "assists": 0},
    {"bonus_key": "seasonal_750", "bonus_type": "seasonal", "competition": "official", "games": 0, "starts": 0, "minutes": 750, "goals": 0, "assists": 0},
    {"bonus_key": "seasonal_1500", "bonus_type": "seasonal", "competition": "official", "games": 0, "starts": 0, "minutes": 1500, "goals": 0, "assists": 0},
    {"bonus_key": "seasonal_2100", "bonus_type": "seasonal", "competition": "official", "games": 0, "starts": 0, "minutes": 2100, "goals": 0, "assists": 0},
    {"bonus_key": "squad", "bonus_type": "repeatable", "competition": "official", "games": 1, "starts": 0, "minutes": 0, "goals": 0, "assists": 0},
    {"bonus_key": "start_appearance", "bonus_type": "one_time", "competition": "official", "games": 0, "starts": 1, "minutes": 5, "goals": 0, "assists": 0},
    {"bonus_key": "goal", "bonus_type": "repeatable", "competition": "official", "games": 0, "starts": 0, "minutes": 0, "goals": 1, "assists": 0},
    {"bonus_key": "assist", "bonus_type": "repeatable", "competition": "official", "games": 0, "starts": 0, "minutes": 0, "goals": 0, "assists": 1},
]

BONUS_VALUE_RANGES_RUB = {
    "seasonal_games": (75_000, 200_000),
    "seasonal_750": (150_000, 400_000),
    "seasonal_1500": (300_000, 700_000),
    "seasonal_2100": (500_000, 1_200_000),
    "squad": (10_000, 75_000),
    "start_appearance": (25_000, 150_000),
    "goal": (30_000, 200_000),
    "assist": (20_000, 150_000),
}


def parse_date(value):
    if not value:
        return None
    value = str(value).strip()
    if value in {"-", "nan", "None"}:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def random_rub_amount(low: int, high: int, step: int = 5_000) -> int:
    return random.randrange(low, high + step, step)


def salary_for_player(seed_value: int) -> int:
    random.seed(f"salary-{seed_value}")
    return random_rub_amount(BASE_SALARY_RANGE_RUB[0], BASE_SALARY_RANGE_RUB[1], step=25_000)


def bonus_value_for_player(seed_value: int, bonus_key: str) -> int:
    low, high = BONUS_VALUE_RANGES_RUB[bonus_key]
    random.seed(f"bonus-{seed_value}-{bonus_key}")
    return random_rub_amount(low, high)


def load_player_contract_dates(source: Path):
    with source.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    return {
        int(float(row["player_id"])): {
            "contract_start": parse_date(row.get("joined")) or DEFAULT_CONTRACT_START,
            "contract_end": parse_date(row.get("contract_end")) or DEFAULT_CONTRACT_END,
        }
        for row in rows
        if row.get("player_id")
    }


def load_league_contract_terms(source: Path):
    contract_dates = load_player_contract_dates(source)

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT p.id, p.transfermarkt_player_id, c.id AS club_id
                FROM players p
                JOIN clubs c ON c.id = p.club_id
                ORDER BY p.id;
                """
            )
            players = cursor.fetchall()

            contract_count = 0
            bonus_count = 0

            for player in players:
                transfermarkt_player_id = player["transfermarkt_player_id"]
                date_info = contract_dates.get(transfermarkt_player_id, {})
                contract_start = date_info.get("contract_start", DEFAULT_CONTRACT_START)
                contract_end = date_info.get("contract_end", DEFAULT_CONTRACT_END)
                seed_value = transfermarkt_player_id or player["id"]
                base_salary_rub = salary_for_player(seed_value)

                cursor.execute(
                    """
                    INSERT INTO contract_terms (
                        player_id,
                        club_id,
                        base_salary,
                        contract_start,
                        contract_end
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (player_id, club_id, contract_start, contract_end) DO UPDATE
                    SET base_salary = EXCLUDED.base_salary
                    RETURNING id;
                    """,
                    (
                        player["id"],
                        player["club_id"],
                        base_salary_rub,
                        contract_start,
                        contract_end,
                    ),
                )
                contract_term_id = cursor.fetchone()["id"]
                contract_count += 1

                cursor.execute(
                    "DELETE FROM contract_bonuses WHERE contract_term_id = %s;",
                    (contract_term_id,),
                )

                for bonus in BONUS_TEMPLATES:
                    bonus_value_rub = bonus_value_for_player(seed_value, bonus["bonus_key"])
                    cursor.execute(
                        """
                        INSERT INTO contract_bonuses (
                            contract_term_id,
                            bonus_type,
                            competition,
                            games,
                            starts,
                            minutes,
                            goals,
                            assists,
                            bonus_value
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                        """,
                        (
                            contract_term_id,
                            bonus["bonus_type"],
                            bonus["competition"],
                            bonus["games"],
                            bonus.get("starts", 0),
                            bonus["minutes"],
                            bonus["goals"],
                            bonus["assists"],
                            bonus_value_rub,
                        ),
                    )
                    bonus_count += 1

        connection.commit()

    print(
        f"Loaded {contract_count} league contract terms and "
        f"{bonus_count} contract bonuses"
    )


def main():
    source = Path(__file__).resolve().parent.parent / "rpl_players.csv"
    if not source.exists():
        raise FileNotFoundError(f"Missing source file: {source}")

    load_league_contract_terms(source)


if __name__ == "__main__":
    main()
