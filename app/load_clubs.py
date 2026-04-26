import csv
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from app.db import get_connection

BASE = "https://www.transfermarkt.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/83.0.4103.97 Safari/537.36"
    )
}


def parse_int(value):
    if value in (None, ""):
        return None
    return int(float(value))


def fetch_club_name(club_slug, club_id):
    if not club_slug or club_id is None:
        return None
    url = f"{BASE}/{club_slug}/kader/verein/{club_id}/saison_id/2025/plus/1"
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    heading = soup.find("h1")
    if heading:
        name = heading.get_text(" ", strip=True)
        if name:
            return name

    title = soup.find("title")
    if title:
        text = title.get_text(" ", strip=True)
        if " - " in text:
            return text.split(" - ", 1)[0].strip()
        if text:
            return text

    return None


def load_clubs(source: Path):
    with source.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    with get_connection() as connection:
        with connection.cursor() as cursor:
            club_count = 0
            skipped_count = 0

            for row in rows:
                transfermarkt_club_id = parse_int(row["club_id"])
                club_slug = row.get("club_slug") or row.get("slug") or None

                if transfermarkt_club_id is None:
                    skipped_count += 1
                    continue

                club_name = row.get("club_name") or row.get("team_name")
                if not club_name:
                    try:
                        club_name = fetch_club_name(club_slug, transfermarkt_club_id)
                    except Exception as exc:
                        print(
                            f"Failed to fetch club name for {club_slug} "
                            f"({transfermarkt_club_id}): {exc}"
                        )

                cursor.execute(
                    """
                    INSERT INTO clubs (transfermarkt_club_id, club_slug, club_name)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (transfermarkt_club_id) DO UPDATE
                    SET club_slug = EXCLUDED.club_slug,
                        club_name = EXCLUDED.club_name;
                    """,
                    (transfermarkt_club_id, club_slug, club_name),
                )
                club_count += 1

        connection.commit()

    print(f"Processed {club_count} club rows from {source}; skipped {skipped_count} invalid rows")


def main():
    source = Path(__file__).resolve().parent.parent / "rpl_clubs.csv"
    if not source.exists():
        raise FileNotFoundError(f"Missing source file: {source}")

    load_clubs(source)


if __name__ == "__main__":
    main()
