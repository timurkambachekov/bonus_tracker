import re
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE = "https://www.transfermarkt.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/83.0.4103.97 Safari/537.36"
    )
}
SEASON = 2025


def parse_player_id(href: str):
    if not href:
        return None
    match = re.search(r"/spieler/(\d+)", href)
    return int(match.group(1)) if match else None


def parse_dob_age(value: str):
    if not value:
        return None, None
    match = re.match(r"^(?P<dob>\d{1,2}/\d{1,2}/\d{4})(?:\s*\((?P<age>\d+)\))?$", value.strip())
    if not match:
        return value, None
    dob = match.group("dob")
    age = match.group("age")
    return dob, int(age) if age is not None else None


def parse_height(value: str):
    if not value:
        return None
    s = value.strip().replace("m", "").replace(",", ".")
    if s in {"", "-", "—"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_market_value(value: str):
    if not value:
        return None
    s = value.strip().replace("€", "").replace(" ", "").replace(",", ".")
    if s in {"", "-", "—"}:
        return None
    multiplier = 1.0
    if s.endswith("m"):
        multiplier = 1_000_000
        s = s[:-1]
    elif s.endswith("k"):
        multiplier = 1_000
        s = s[:-1]
    try:
        return float(s) * multiplier
    except ValueError:
        return None


def text(cell):
    return cell.get_text(" ", strip=True) or None


def parse_nationality(cell):
    images = cell.find_all("img")
    nationalities = []
    for image in images:
        alt = image.get("alt", "").strip()
        if alt:
            nationalities.append(alt)

    if nationalities:
        return ", ".join(nationalities)

    return text(cell)


def parse_roster(club_slug: str, club_id: int):
    url = f"{BASE}/{club_slug}/kader/verein/{club_id}/saison_id/{SEASON}/plus/1"
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", class_="items")
    if table is None:
        raise ValueError(f"Roster table not found for {club_slug} ({club_id})")

    players = []
    for row in table.select("tbody > tr"):
        cells = row.find_all("td", recursive=False)
        if len(cells) < 10:
            continue

        player_cell = cells[1]
        player_anchor = player_cell.select_one("a[href*='/profil/spieler/']")
        profile_href = player_anchor.get("href", "") if player_anchor else ""
        profile_url = urljoin(BASE, profile_href) if profile_href else None
        date_of_birth, age = parse_dob_age(text(cells[2]))

        inline_table = player_cell.find("table")
        player_name = None
        position = None
        if inline_table:
            nested_rows = inline_table.find_all("tr")
            if len(nested_rows) >= 1:
                name_cells = nested_rows[0].find_all("td")
                if len(name_cells) >= 2:
                    player_name = text(name_cells[1])
            if len(nested_rows) >= 2:
                position_cell = nested_rows[1].find("td")
                if position_cell:
                    position = text(position_cell)

        if not player_name and player_anchor:
            player_name = text(player_anchor)

        players.append(
            {
                "shirt_number": text(cells[0]),
                "player_id": parse_player_id(profile_href),
                "player_name": player_name,
                "position": position,
                "date_of_birth": date_of_birth,
                "age": age,
                "nationality": parse_nationality(cells[3]),
                "height_m": parse_height(text(cells[4])),
                "foot": text(cells[5]),
                "joined": text(cells[6]),
                "contract_end": text(cells[8]),
                "market_value_eur": parse_market_value(text(cells[9])),
                "player_profile_url": profile_url,
                "club_id": int(club_id),
                "club_slug": club_slug,
            }
        )

    return players


def main():
    clubs_path = Path(__file__).resolve().parent.parent.parent / "rpl_clubs.csv"
    clubs = pd.read_csv(clubs_path)

    slug_column = "club_slug" if "club_slug" in clubs.columns else "slug"
    all_players = []

    for _, club in clubs.iterrows():
        club_slug = str(club[slug_column]).strip()
        club_id = int(club["club_id"])
        print(f"Fetching {club_slug} ({club_id})")
        try:
            all_players.extend(parse_roster(club_slug, club_id))
        except Exception as exc:
            print(f"Failed to fetch {club_slug} ({club_id}): {exc}")

    output = pd.DataFrame(all_players)
    if not output.empty:
        output = output.dropna(subset=["player_id"])
        output["player_id"] = output["player_id"].astype(int)
        output["club_id"] = output["club_id"].astype(int)
        output = output.drop_duplicates(subset=["player_id", "club_id", "club_slug"])
        output = output.sort_values(["club_slug", "player_name"], na_position="last").reset_index(drop=True)
    output_path = Path(__file__).resolve().parent.parent.parent / "rpl_players.csv"
    output.to_csv(output_path, index=False)
    print(f"Saved {len(output)} players to {output_path}")


if __name__ == "__main__":
    main()
