import csv
from datetime import datetime
from pathlib import Path

from app.db import get_connection


def parse_int(value):
    if value in (None, ""):
        return None
    return int(float(value))


def parse_float(value):
    if value in (None, ""):
        return None
    return float(value)


def parse_date(value):
    if value in (None, ""):
        return None
    return datetime.strptime(value, "%d/%m/%Y").date()


def load_players(source: Path):
    with source.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, transfermarkt_club_id
                FROM clubs
                WHERE transfermarkt_club_id IS NOT NULL;
                """
            )
            club_id_map = {
                row["transfermarkt_club_id"]: row["id"]
                for row in cursor.fetchall()
            }

            player_count = 0
            skipped_count = 0

            for row in rows:
                transfermarkt_player_id = parse_int(row["player_id"])
                transfermarkt_club_id = parse_int(row["club_id"])

                if transfermarkt_player_id is None or transfermarkt_club_id is None:
                    skipped_count += 1
                    continue

                internal_club_id = club_id_map.get(transfermarkt_club_id)
                if internal_club_id is None:
                    skipped_count += 1
                    continue

                cursor.execute(
                    """
                    INSERT INTO players (
                        transfermarkt_player_id,
                        player_name,
                        position,
                        date_of_birth,
                        nationality,
                        height_m,
                        foot,
                        market_value_eur,
                        club_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (transfermarkt_player_id) DO UPDATE
                    SET player_name = EXCLUDED.player_name,
                        position = EXCLUDED.position,
                        date_of_birth = EXCLUDED.date_of_birth,
                        nationality = EXCLUDED.nationality,
                        height_m = EXCLUDED.height_m,
                        foot = EXCLUDED.foot,
                        market_value_eur = EXCLUDED.market_value_eur,
                        club_id = EXCLUDED.club_id;
                    """,
                    (
                        transfermarkt_player_id,
                        row["player_name"] or None,
                        row["position"] or None,
                        parse_date(row["date_of_birth"]),
                        row["nationality"] or None,
                        parse_float(row["height_m"]),
                        row["foot"] or None,
                        parse_float(row["market_value_eur"]),
                        internal_club_id,
                    ),
                )
                player_count += 1

        connection.commit()

    print(
        f"Processed {player_count} player rows "
        f"from {source}; skipped {skipped_count} invalid rows"
    )


def main():
    source = Path(__file__).resolve().parent.parent / "rpl_players.csv"
    if not source.exists():
        raise FileNotFoundError(f"Missing source file: {source}")

    load_players(source)


if __name__ == "__main__":
    main()
