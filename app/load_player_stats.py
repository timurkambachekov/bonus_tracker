import csv
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


def load_player_stats(source: Path):
    with source.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, transfermarkt_player_id
                FROM players
                WHERE transfermarkt_player_id IS NOT NULL;
                """
            )
            player_id_map = {
                row["transfermarkt_player_id"]: row["id"]
                for row in cursor.fetchall()
            }
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

            stats_count = 0
            skipped_count = 0

            for row in rows:
                transfermarkt_player_id = parse_int(row["player_id"])
                transfermarkt_club_id = parse_int(row["club_id"])
                season = parse_int(row["season"])

                if transfermarkt_club_id is None or season is None or transfermarkt_player_id is None:
                    skipped_count += 1
                    continue

                internal_club_id = club_id_map.get(transfermarkt_club_id)
                internal_player_id = player_id_map.get(transfermarkt_player_id)
                if internal_club_id is None or internal_player_id is None:
                    skipped_count += 1
                    continue

                cursor.execute(
                    """
                    INSERT INTO player_season_stats (
                        player_id,
                        club_id,
                        season,
                        squad_inclusions,
                        appearances,
                        goals,
                        assists,
                        yellow_cards,
                        second_yellow_cards,
                        red_cards,
                        substitutions_on,
                        substitutions_off,
                        minutes_played,
                        ppg
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (player_id, club_id, season) DO UPDATE
                    SET squad_inclusions = EXCLUDED.squad_inclusions,
                        appearances = EXCLUDED.appearances,
                        goals = EXCLUDED.goals,
                        assists = EXCLUDED.assists,
                        yellow_cards = EXCLUDED.yellow_cards,
                        second_yellow_cards = EXCLUDED.second_yellow_cards,
                        red_cards = EXCLUDED.red_cards,
                        substitutions_on = EXCLUDED.substitutions_on,
                        substitutions_off = EXCLUDED.substitutions_off,
                        minutes_played = EXCLUDED.minutes_played,
                        ppg = EXCLUDED.ppg;
                    """,
                    (
                        internal_player_id,
                        internal_club_id,
                        season,
                        parse_int(row.get("squad_inclusions")),
                        parse_int(row["appearances"]),
                        parse_int(row["goals"]),
                        parse_int(row["assists"]),
                        parse_int(row["yellow_cards"]),
                        parse_int(row["second_yellow_cards"]),
                        parse_int(row["red_cards"]),
                        parse_int(row["substitutions_on"]),
                        parse_int(row["substitutions_off"]),
                        parse_int(row["minutes_played"]),
                        parse_float(row["ppg"]),
                    ),
                )
                stats_count += 1

        connection.commit()

    print(
        f"Processed {stats_count} stats rows from {source}; skipped {skipped_count} invalid rows"
    )


def main():
    source = Path(__file__).resolve().parent.parent / "rpl_club_stats.csv"
    if not source.exists():
        raise FileNotFoundError(f"Missing source file: {source}")

    load_player_stats(source)


if __name__ == "__main__":
    main()
