import argparse


COMPETITION_PRESETS = {
    "rpl": {
        "code": "RU1",
        "slug": "premier-liga",
        "country": "Russia",
    },
    "russian-cup": {
        "code": "RUC",
        "slug": "russian-cup",
        "country": "Russia",
    },
    "fnl": {
        "code": "RU2",
        "slug": "1-division",
        "country": "Russia",
    },
    "second-league-a": {
        "code": "RU3N",
        "slug": "2-division-a",
        "country": "Russia",
    },
}


def competition_keys() -> list[str]:
    return sorted(COMPETITION_PRESETS.keys())


def build_selected_competitions(keys: list[str], season: int) -> list[dict]:
    selected_keys = keys or ["rpl"]
    competitions = []

    for key in selected_keys:
        preset = COMPETITION_PRESETS[key]
        competitions.append(
            {
                "key": key,
                "code": preset["code"],
                "slug": preset["slug"],
                "country": preset["country"],
                "season": season,
            }
        )

    return competitions


def add_competition_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument(
        "--competition",
        action="append",
        choices=competition_keys(),
        default=[],
        help="Competition preset to load. Repeat the flag to load multiple competitions.",
    )
    parser.add_argument(
        "--season",
        type=int,
        default=2025,
        help="Transfermarkt season id to scrape.",
    )
    return parser
