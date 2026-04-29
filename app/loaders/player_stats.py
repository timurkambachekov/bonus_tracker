import re

import requests
from bs4 import BeautifulSoup

from app.backend.db import get_connection
from app.loaders.common import parse_float, parse_int

BASE = "https://www.transfermarkt.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/83.0.4103.97 Safari/537.36"
    )
}


class BlockedPageError(RuntimeError):
    pass


def derive_count(total, subset):
    if total is None:
        return None
    if subset is None:
        subset = 0
    return max(int(total) - int(subset), 0)


def clean_stat_value(value: str):
    if value is None:
        return None
    cleaned = str(value).strip()
    if cleaned.lower() in {
        "",
        "-",
        "–",
        "—",
        "not used during this season",
    }:
        return None
    return cleaned


def parse_minutes(value: str):
    cleaned = clean_stat_value(value)
    if cleaned is None:
        return 0
    return parse_int(cleaned.replace("'", "").replace(".", ""))


def parse_stat_int(value: str):
    cleaned = clean_stat_value(value)
    if cleaned is None:
        return 0
    try:
        return parse_int(cleaned)
    except (TypeError, ValueError):
        return 0


def parse_stat_float(value: str):
    cleaned = clean_stat_value(value)
    if cleaned is None:
        return 0.0
    try:
        return parse_float(cleaned)
    except (TypeError, ValueError):
        return 0.0


def parse_player_id_from_href(href: str):
    if not href:
        return None
    match = re.search(r"/spieler/(\d+)", href)
    return int(match.group(1)) if match else None


def build_stats_url(club: dict) -> str:
    competition_code = club["competition_code"]
    season = club["season"]
    return (
        f"{BASE}/{club['club_slug']}/leistungsdaten/verein/{club['transfermarkt_club_id']}"
        f"/plus/1?reldata={competition_code}%26{season}"
    )


def fetch_soup(url: str) -> BeautifulSoup:
    response = requests.get(url, headers=HEADERS, timeout=30)
    if response.status_code in (202, 403):
        raise BlockedPageError(f"Transfermarkt blocked the request: {url}")
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    return BeautifulSoup(response.text, "html.parser")


def parse_stats_table(club: dict) -> list[dict]:
    soup = fetch_soup(build_stats_url(club))
    table = soup.find("table", class_="items")
    if table is None:
        raise ValueError(f"Stats table not found for {club['club_name']}")

    stats = []
    valid_player_ids = club["player_id_map"]

    for row in table.select("tbody > tr"):
        cells = row.find_all("td", recursive=False)
        if len(cells) < 15:
            continue

        player_cell = cells[1]
        player_anchor = player_cell.select_one("a[href*='/profil/spieler/']")
        transfermarkt_player_id = (
            parse_player_id_from_href(player_anchor.get("href", ""))
            if player_anchor is not None
            else None
        )
        internal_player_id = valid_player_ids.get(transfermarkt_player_id)
        if transfermarkt_player_id is None or internal_player_id is None:
            continue

        stats.append(
            {
                "player_id": internal_player_id,
                "club_id": club["id"],
                "competition_id": club["competition_id"],
                "season": club["season"],
                "squad_inclusions": parse_stat_int(cells[4].get_text(strip=True)),
                "appearances": parse_stat_int(cells[5].get_text(strip=True)),
                "goals": parse_stat_int(cells[6].get_text(strip=True)),
                "assists": parse_stat_int(cells[7].get_text(strip=True)),
                "yellow_cards": parse_stat_int(cells[8].get_text(strip=True)),
                "second_yellow_cards": parse_stat_int(cells[9].get_text(strip=True)),
                "red_cards": parse_stat_int(cells[10].get_text(strip=True)),
                "substitutions_on": parse_stat_int(cells[11].get_text(strip=True)),
                "substitutions_off": parse_stat_int(cells[12].get_text(strip=True)),
                "ppg": parse_stat_float(cells[13].get_text(strip=True)),
                "minutes_played": parse_minutes(cells[14].get_text(strip=True)),
            }
        )

    if not stats:
        raise ValueError(f"No stats found for {club['club_name']}")

    return stats


def fetch_clubs(cursor) -> list[dict]:
    cursor.execute(
        """
        SELECT
            clubs.id,
            clubs.transfermarkt_club_id,
            clubs.club_slug,
            clubs.club_name,
            clubs.competition_id,
            competitions.transfermarkt_code AS competition_code,
            competitions.season
        FROM clubs
        JOIN competitions ON competitions.id = clubs.competition_id
        WHERE clubs.transfermarkt_club_id IS NOT NULL
          AND clubs.club_slug IS NOT NULL
          AND competitions.transfermarkt_code IS NOT NULL
          AND competitions.season IS NOT NULL
        ORDER BY clubs.id;
        """
    )
    return cursor.fetchall()


def attach_club_players(cursor, clubs: list[dict]) -> list[dict]:
    enriched_clubs = []

    for club in clubs:
        cursor.execute(
            """
            SELECT id, transfermarkt_player_id
            FROM players
            WHERE club_id = %s
              AND transfermarkt_player_id IS NOT NULL;
            """,
            (club["id"],),
        )
        player_id_map = {
            row["transfermarkt_player_id"]: row["id"]
            for row in cursor.fetchall()
        }
        if not player_id_map:
            continue

        club["player_id_map"] = player_id_map
        enriched_clubs.append(club)

    return enriched_clubs


def store_stats(cursor, row: dict) -> None:
    appearances = row["appearances"]
    substitutions_on = row["substitutions_on"]
    substitutions_off = row["substitutions_off"]
    starts = int(appearances) - int(substitutions_on)
    full_games = int(starts) - int(substitutions_off)

    cursor.execute(
        """
        DELETE FROM player_season_stats
        WHERE player_id = %s
          AND club_id = %s
          AND competition_id = %s
          AND season = %s;
        """,
        (
            row["player_id"],
            row["club_id"],
            row["competition_id"],
            row["season"],
        ),
    )

    cursor.execute(
        """
        INSERT INTO player_season_stats (
            player_id,
            club_id,
            competition_id,
            season,
            squad_inclusions,
            appearances,
            starts,
            full_games,
            substitutions_on,
            substitutions_off,
            minutes_played,
            goals,
            assists,
            yellow_cards,
            second_yellow_cards,
            red_cards,
            ppg
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """,
        (
            row["player_id"],
            row["club_id"],
            row["competition_id"],
            row["season"],
            row["squad_inclusions"],
            appearances,
            starts,
            full_games,
            substitutions_on,
            substitutions_off,
            row["minutes_played"],
            row["goals"],
            row["assists"],
            row["yellow_cards"],
            row["second_yellow_cards"],
            row["red_cards"],
            row["ppg"],
        ),
    )


def load_player_stats() -> None:
    total_stats = 0
    skipped_clubs = 0

    with get_connection() as connection:
        with connection.cursor() as cursor:
            clubs = attach_club_players(cursor, fetch_clubs(cursor))

            for club in clubs:
                try:
                    rows = parse_stats_table(club)
                except (BlockedPageError, ValueError) as error:
                    skipped_clubs += 1
                    print(f"Skipped {club['club_name']}: {error}")
                    continue

                for row in rows:
                    store_stats(cursor, row)

                total_stats += len(rows)
                print(f"Processed {len(rows)} stats rows for {club['club_name']}")

        connection.commit()

    print(
        f"Processed {total_stats} stats rows across {len(clubs) - skipped_clubs} clubs; "
        f"skipped {skipped_clubs} clubs"
    )


def main():
    load_player_stats()


if __name__ == "__main__":
    main()
