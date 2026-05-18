import argparse
import re

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
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.transfermarkt.com/",
}


def build_competition_url(
    competition: dict,
) -> str:
    return (
        f"{BASE}/{competition['slug']}/startseite/wettbewerb/{competition['code']}"
        f"?saison_id={competition['season']}"
    )


def fetch_soup(url: str) -> BeautifulSoup:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    return BeautifulSoup(response.text, "html.parser")


def parse_competition_page(competition: dict) -> dict:
    url = build_competition_url(competition)
    soup = fetch_soup(url)

    competition_name = soup.find("h1").get_text(" ", strip=True)
    clubs = []

    for anchor in soup.select("table.items tbody td.hauptlink a[href*='/startseite/verein/']"):
        href = anchor.get("href", "")
        match = re.search(r"/([^/]+)/startseite/verein/(\d+)", href)
        if not match:
            continue

        clubs.append(
            {
                "club_slug": match.group(1),
                "club_id": int(match.group(2)),
                "club_name": anchor.get_text(" ", strip=True),
                "country": competition["country"],
            }
        )

    unique_clubs = {club["club_id"]: club for club in clubs}
    clubs = list(unique_clubs.values())
    if not clubs:
        raise ValueError(f"No clubs found at {url}")

    return {
        "competition_code": competition["code"],
        "competition_name": competition_name,
        "competition_country": competition["country"],
        "season": competition["season"],
        "clubs": clubs,
    }


def upsert_competition(
    cursor,
    competition_code: str,
    competition_name: str,
    competition_country: str,
    season: int,
) -> int:
    cursor.execute(
        """
        INSERT INTO competitions (transfermarkt_code, name, country, season)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (transfermarkt_code) DO UPDATE
        SET name = EXCLUDED.name,
            country = EXCLUDED.country,
            season = EXCLUDED.season
        RETURNING id;
        """,
        (competition_code, competition_name, competition_country, season),
    )
    return cursor.fetchone()["id"]


def load_competition_clubs(cursor, competition: dict) -> int:
    payload = parse_competition_page(competition)

    competition_id = upsert_competition(
        cursor,
        competition_code=payload["competition_code"],
        competition_name=payload["competition_name"],
        competition_country=payload["competition_country"],
        season=payload["season"],
    )

    for club in payload["clubs"]:
        cursor.execute(
            """
            INSERT INTO clubs (
                transfermarkt_club_id,
                club_slug,
                club_name
            )
            VALUES (%s, %s, %s)
            ON CONFLICT (transfermarkt_club_id) DO UPDATE
            SET club_slug = EXCLUDED.club_slug,
                club_name = EXCLUDED.club_name
            RETURNING id;
            """,
            (
                club["club_id"],
                club["club_slug"],
                club["club_name"],
            ),
        )
        club_row = cursor.fetchone()
        cursor.execute(
            """
            INSERT INTO club_competitions (
                club_id,
                competition_id,
                season
            )
            VALUES (%s, %s, %s)
            ON CONFLICT (club_id, competition_id, season) DO NOTHING;
            """,
            (
                club_row["id"],
                competition_id,
                payload["season"],
            ),
        )

    print(
        f"Processed {len(payload['clubs'])} clubs for {payload['competition_name']} "
        f"({payload['competition_code']}, season {payload['season']})"
    )
    return len(payload["clubs"])


def load_clubs() -> None:
    load_clubs_for_competitions(build_selected_competitions([], season=2025))


def load_clubs_for_competitions(competitions: list[dict]) -> None:
    total_clubs = 0

    with get_connection() as connection:
        with connection.cursor() as cursor:
            for competition in competitions:
                total_clubs += load_competition_clubs(
                    cursor,
                    competition=competition,
                )

        connection.commit()

    print(f"Processed {total_clubs} clubs across {len(competitions)} competitions")


def parse_args():
    parser = argparse.ArgumentParser(description="Load clubs for one or more Transfermarkt competitions.")
    add_competition_arguments(parser)
    return parser.parse_args()


def main():
    args = parse_args()
    load_clubs_for_competitions(
        build_selected_competitions(args.competition, season=args.season)
    )


if __name__ == "__main__":
    main()
