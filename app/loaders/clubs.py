import re

import requests
from bs4 import BeautifulSoup

from app.db import get_connection

BASE = "https://www.transfermarkt.com"
COMPETITIONS = [
    {
        "code": "RU1",
        "slug": "premier-liga",
        "country": "Russia",
        "season": 2025,
    },
]
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
                club_name,
                competition_id
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (transfermarkt_club_id) DO UPDATE
            SET club_slug = EXCLUDED.club_slug,
                club_name = EXCLUDED.club_name,
                competition_id = EXCLUDED.competition_id;
            """,
            (
                club["club_id"],
                club["club_slug"],
                club["club_name"],
                competition_id,
            ),
        )

    print(
        f"Processed {len(payload['clubs'])} clubs for {payload['competition_name']} "
        f"({payload['competition_code']}, season {payload['season']})"
    )
    return len(payload["clubs"])


def load_clubs() -> None:
    total_clubs = 0

    with get_connection() as connection:
        with connection.cursor() as cursor:
            for competition in COMPETITIONS:
                total_clubs += load_competition_clubs(
                    cursor,
                    competition=competition,
                )

        connection.commit()

    print(f"Processed {total_clubs} clubs across {len(COMPETITIONS)} competitions")


def main():
    load_clubs()


if __name__ == "__main__":
    main()
