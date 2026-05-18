import re
from datetime import datetime
from time import sleep
from typing import List, Optional
import argparse

import requests
from bs4 import BeautifulSoup

from app.backend.db import get_connection
from app.loaders.competitions import add_competition_arguments, build_selected_competitions

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


def build_squad_url(club: dict) -> str:
    return (
        f"{BASE}/{club['club_slug']}/kader/verein/{club['transfermarkt_club_id']}"
        f"/saison_id/{club['season']}/plus/1"
    )


def fetch_soup(url: str) -> BeautifulSoup:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    soup = BeautifulSoup(response.text, "html.parser")
    return soup


def parse_transfermarkt_date(value: str):
    cleaned = value.split("(")[0].strip()
    if not cleaned or cleaned == "-":
        return None
    cleaned = datetime.strptime(cleaned, "%d/%m/%Y").date()
    return cleaned


def parse_height(value: str):
    cleaned = value.strip().replace("m", "").replace(",", ".")
    if not cleaned or cleaned == "-":
        return None
    return float(cleaned)


def parse_market_value(value: str):
    cleaned = value.strip().replace("€", "").replace(",", ".")
    if not cleaned or cleaned == "-":
        return None

    multiplier = 1
    if cleaned.endswith("m"):
        multiplier = 1_000_000
        cleaned = cleaned[:-1]
    elif cleaned.endswith("k"):
        multiplier = 1_000
        cleaned = cleaned[:-1]

    try:
        return float(cleaned) * multiplier
    except ValueError:
        return None


def extract_row_cells(row) -> list:
    return row.find_all("td", recursive=False)


def extract_date_of_birth(cells: list):
    for cell in cells:
        value = cell.get_text(" ", strip=True)
        if re.fullmatch(r"\d{2}/\d{2}/\d{4}( \(\d+\))?", value) is None:
            continue
        date_of_birth = parse_transfermarkt_date(value)
        if date_of_birth is not None:
            return date_of_birth
    return None


def extract_nationality(row) -> Optional[str]:
    nationalities = []

    for image in row.select("img[class*='flaggenrahmen']"):
        value = image.get("title") or image.get("alt", "")
        value = value.strip()
        if value and value not in nationalities:
            nationalities.append(value)

    if nationalities:
        return ", ".join(nationalities)

    for cell in extract_row_cells(row):
        if cell.select_one("img[class*='flaggenrahmen']") is None:
            continue
        value = cell.get_text(" ", strip=True)
        if value:
            return value

    return None


def extract_height(cells: list):
    for cell in cells:
        value = cell.get_text(" ", strip=True)
        if re.fullmatch(r"\d,\d{2}m", value) is None:
            continue
        height = parse_height(value)
        if height is not None and 1.4 <= height <= 2.3:
            return height
    return None


def extract_foot(cells: list) -> Optional[str]:
    for cell in cells:
        value = cell.get_text(" ", strip=True)
        normalized = value.lower()
        if normalized in {"right", "left", "both"}:
            return value
    return None


def extract_position(main_cell, player_name: str) -> Optional[str]:
    position_cell = main_cell.select_one("table.inline-table tr:nth-of-type(2) td")
    if position_cell is not None:
        position = position_cell.get_text(" ", strip=True)
        if position and position != player_name:
            return position

    for value in main_cell.get_text("\n", strip=True).splitlines():
        value = value.strip()
        if not value or value == player_name or value.isdigit():
            continue
        return value

    return None


def parse_player_row(row) -> Optional[dict]:
    profile_link = row.select_one("a[href*='/profil/spieler/']")
    if profile_link is None:
        return None

    href = profile_link.get("href", "")
    match = re.search(r"/profil/spieler/(\d+)", href)
    if not match:
        return None

    main_cell = row.select_one("td.posrela")
    if main_cell is None:
        return None

    player_name = profile_link.get_text(" ", strip=True) or None
    position = extract_position(main_cell, player_name)

    cells = extract_row_cells(row)
    if len(cells) < 8:
        return None

    market_value_cell = row.select_one("td.rechts.hauptlink")
    market_value = None
    if market_value_cell is not None:
        market_value = parse_market_value(market_value_cell.get_text(" ", strip=True))

    return {
        "transfermarkt_player_id": int(match.group(1)),
        "player_name": player_name,
        "position": position,
        "date_of_birth": extract_date_of_birth(cells),
        "nationality": extract_nationality(row),
        "height_m": extract_height(cells),
        "foot": extract_foot(cells),
        "market_value_eur": market_value,
    }


def parse_squad_page(club: dict) -> list[dict]:
    soup = fetch_soup(build_squad_url(club))
    players = []

    for row in soup.select("table.items tbody tr"):
        player = parse_player_row(row)
        if player is None:
            continue
        players.append(player)

    unique_players = {player["transfermarkt_player_id"]: player for player in players}
    players = list(unique_players.values())
    if not players:
        raise ValueError(f"No players found for {club['club_name']}")

    return players


def fetch_clubs(cursor, competition_codes: Optional[List[str]] = None, season: Optional[int] = None) -> list[dict]:
    params = []
    where_clauses = [
        "clubs.transfermarkt_club_id IS NOT NULL",
        "clubs.club_slug IS NOT NULL",
        "club_competitions.season IS NOT NULL",
    ]

    if competition_codes:
        where_clauses.append("competitions.transfermarkt_code = ANY(%s)")
        params.append(competition_codes)

    if season is not None:
        where_clauses.append("club_competitions.season = %s")
        params.append(season)

    cursor.execute(
        f"""
        SELECT
            clubs.id,
            clubs.transfermarkt_club_id,
            clubs.club_slug,
            clubs.club_name,
            club_competitions.season
        FROM clubs
        JOIN club_competitions ON club_competitions.club_id = clubs.id
        JOIN competitions ON competitions.id = club_competitions.competition_id
        WHERE {' AND '.join(where_clauses)};
        """,
        params,
    )
    return cursor.fetchall()


def load_players(competition_codes: Optional[List[str]] = None, season: Optional[int] = None) -> None:
    total_players = 0

    with get_connection() as connection:
        with connection.cursor() as cursor:
            clubs = fetch_clubs(cursor, competition_codes=competition_codes, season=season)

            for club in clubs:
                players = parse_squad_page(club)

                for player in players:
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
                            market_value_eur
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (transfermarkt_player_id) DO UPDATE
                        SET player_name = EXCLUDED.player_name,
                            position = EXCLUDED.position,
                            date_of_birth = EXCLUDED.date_of_birth,
                            nationality = EXCLUDED.nationality,
                            height_m = EXCLUDED.height_m,
                            foot = EXCLUDED.foot,
                            market_value_eur = EXCLUDED.market_value_eur
                        RETURNING id;
                        """,
                        (
                            player["transfermarkt_player_id"],
                            player["player_name"],
                            player["position"],
                            player["date_of_birth"],
                            player["nationality"],
                            player["height_m"],
                            player["foot"],
                            player["market_value_eur"],
                        ),
                    )
                    player_row = cursor.fetchone()
                    cursor.execute(
                        """
                        INSERT INTO player_clubs (
                            player_id,
                            club_id,
                            season
                        )
                        VALUES (%s, %s, %s)
                        ON CONFLICT (player_id, club_id, season) DO NOTHING;
                        """,
                        (
                            player_row["id"],
                            club["id"],
                            club["season"],
                        ),
                    )

                total_players += len(players)
                print(f"Processed {len(players)} players for {club['club_name']}")

        connection.commit()

    print(f"Processed {total_players} players across {len(clubs)} clubs")


def parse_args():
    parser = argparse.ArgumentParser(description="Load players for clubs already stored in the database.")
    add_competition_arguments(parser)
    return parser.parse_args()


def main():
    args = parse_args()
    competitions = build_selected_competitions(args.competition, season=args.season)
    load_players(
        competition_codes=[competition["code"] for competition in competitions],
        season=args.season,
    )


if __name__ == "__main__":
    main()
