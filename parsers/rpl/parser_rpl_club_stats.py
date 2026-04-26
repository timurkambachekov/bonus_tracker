import re
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE = "https://www.transfermarkt.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/83.0.4103.97 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.transfermarkt.com/",
    "Connection": "keep-alive",
}
SEASON = 2025


def parse_int(value):
    if value is None:
        return 0
    s = str(value).strip()
    if s in {"", "-", "–", "—"}:
        return 0
    try:
        return int(float(s))
    except ValueError:
        return 0


def parse_float(value):
    if value is None:
        return 0.0
    s = str(value).strip().replace(" ", "").replace(",", ".")
    if s in {"", "-", "–", "—"}:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_minutes(value):
    if value is None:
        return 0
    s = str(value).strip().replace("'", "").replace(".", "")
    return parse_int(s)


def parse_player_id_from_href(href: str):
    if not href:
        return None
    match = re.search(r"/spieler/(\d+)", href)
    return int(match.group(1)) if match else None


def build_stats_url(club_slug: str, club_id: int, season: int = SEASON) -> str:
    return f"{BASE}/{club_slug}/leistungsdaten/verein/{club_id}/plus/1?reldata=RU1%26{season}"


def parse_stats_table(html: str, club_slug: str, club_id: int, valid_player_ids: set[int]) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="items")
    if table is None:
        raise ValueError("Stats table not found in HTML")

    stats = []
    for row in table.select("tbody > tr"):
        cells = row.find_all("td", recursive=False)
        if len(cells) < 15:
            continue

        player_cell = cells[1]
        player_anchor = player_cell.select_one("a[href*='/profil/spieler/']")
        player_id = parse_player_id_from_href(player_anchor.get("href", "")) if player_anchor else None
        if player_id is None or player_id not in valid_player_ids:
            continue

        stats.append(
            {
                "club_slug": club_slug,
                "club_id": club_id,
                "season": SEASON,
                "player_id": player_id,
                "squad_inclusions": parse_int(cells[4].get_text(strip=True)),
                "appearances": parse_int(cells[5].get_text(strip=True)),
                "goals": parse_int(cells[6].get_text(strip=True)),
                "assists": parse_int(cells[7].get_text(strip=True)),
                "yellow_cards": parse_int(cells[8].get_text(strip=True)),
                "second_yellow_cards": parse_int(cells[9].get_text(strip=True)),
                "red_cards": parse_int(cells[10].get_text(strip=True)),
                "substitutions_on": parse_int(cells[11].get_text(strip=True)),
                "substitutions_off": parse_int(cells[12].get_text(strip=True)),
                "ppg": parse_float(cells[13].get_text(strip=True)),
                "minutes_played": parse_minutes(cells[14].get_text(strip=True)),
            }
        )

    return stats


def fetch_club_stats(club_slug: str, club_id: int, valid_player_ids: set[int]) -> list[dict]:
    url = build_stats_url(club_slug, club_id)
    print(f"Fetching {club_slug} ({club_id}) -> {url}")
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return parse_stats_table(response.text, club_slug, club_id, valid_player_ids)


def load_players(source: Path) -> pd.DataFrame:
    return pd.read_csv(source)


def main() -> None:
    source = Path(__file__).resolve().parent.parent.parent / "rpl_players.csv"
    players = load_players(source)
    players = players.dropna(subset=["player_id", "club_id", "club_slug"])
    players["player_id"] = players["player_id"].apply(parse_int)
    players["club_id"] = players["club_id"].apply(parse_int)

    all_stats = []
    club_groups = players.groupby(["club_slug", "club_id"])

    for (club_slug, club_id), group in club_groups:
        valid_player_ids = {
            player_id for player_id in group["player_id"].tolist() if player_id is not None
        }
        try:
            all_stats.extend(fetch_club_stats(str(club_slug), int(club_id), valid_player_ids))
        except Exception as exc:
            print(f"Failed to fetch stats for {club_slug} ({club_id}): {exc}")

    output = pd.DataFrame(all_stats)
    if not output.empty:
        output = output.drop_duplicates(subset=["player_id", "club_id", "season"])
        output = output.sort_values(["club_slug", "player_id"], na_position="last").reset_index(drop=True)

    output_path = Path(__file__).resolve().parent.parent.parent / "rpl_club_stats.csv"
    output.to_csv(output_path, index=False)
    print(f"Saved {len(output)} stats records to {output_path}")


if __name__ == "__main__":
    main()
