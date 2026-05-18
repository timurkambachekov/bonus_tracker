import os
from typing import Optional

import requests

from app.backend.domain import (
    Bonus,
    BonusCompetition,
    BonusType,
    Competition,
    Condition,
    ConditionDirection,
    ConditionOperator,
    ConditionType,
    Contract,
    Player,
    Team,
)

API_BASE_URL = os.getenv("BONUS_TRACKER_API_URL", "http://127.0.0.1:8000")
KNOWN_BONUS_COMPETITIONS = {item.value for item in BonusCompetition}


def fetch_json(path: str, params: Optional[dict] = None):
    response = requests.get(f"{API_BASE_URL}{path}", params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def post_json(path: str):
    response = requests.post(f"{API_BASE_URL}{path}", timeout=30)
    response.raise_for_status()
    return response.json()


def build_competition(data: dict) -> Competition:
    return Competition(
        id=data["id"],
        name=data["name"],
        code=data.get("transfermarkt_code") or data.get("code"),
        country=data.get("country"),
        season=data.get("season"),
    )


def build_team(data: dict, competition: Optional[Competition] = None) -> Team:
    if competition is None and (
        data.get("competition_id")
        or data.get("competition_name")
        or data.get("competition_code")
        or data.get("season")
    ):
        competition = Competition(
            id=data.get("competition_id") or 0,
            name=data.get("competition_name") or data.get("name") or "",
            code=data.get("competition_code") or data.get("transfermarkt_code"),
            country=data.get("competition_country") or data.get("country"),
            season=data.get("season") or data.get("competition_season"),
        )
    return Team(
        id=data["id"],
        name=data.get("club_name") or data.get("name") or "",
        slug=data.get("club_slug") or data.get("slug"),
        transfermarkt_club_id=data.get("transfermarkt_club_id"),
        competition=competition,
    )


def build_player(data: dict, team: Optional[Team] = None) -> Player:
    return Player(
        id=data["id"],
        name=data.get("player_name"),
        transfermarkt_player_id=data.get("transfermarkt_player_id"),
        position=data.get("position"),
        nationality=data.get("nationality"),
        date_of_birth=data.get("date_of_birth"),
        height_m=data.get("height_m"),
        foot=data.get("foot"),
        market_value_eur=data.get("market_value_eur"),
        team=team,
    )


def build_condition(data: dict) -> Condition:
    return Condition(
        id=data["id"],
        condition_type=ConditionType(data["condition_type"]),
        direction=ConditionDirection(data["direction"]),
        threshold=float(data.get("threshold")),
    )


def build_bonus(data: dict, conditions: Optional[list] = None) -> Bonus:
    competition_code = data.get("competition_code") or BonusCompetition.OFFICIAL.value
    if competition_code not in KNOWN_BONUS_COMPETITIONS:
        competition_code = BonusCompetition.OFFICIAL.value

    return Bonus(
        id=data["id"],
        bonus_type=BonusType(data["bonus_type"]),
        competition=BonusCompetition(competition_code),
        payout=float(data.get("bonus_value") or 0),
        conditions=conditions or [],
        competition_name=data.get("competition_name"),
        binding_group=data.get("binding_group"),
        operator=ConditionOperator(data.get("condition_operator") or "and"),
    )


def build_contract(data: dict, bonuses: Optional[list] = None) -> Contract:
    return Contract(
        id=data["id"],
        player_id=data["player_id"],
        club_id=data["club_id"],
        start_date=str(data["contract_start"]),
        end_date=str(data["contract_end"]),
        base_salary=float(data.get("base_salary")),
        bonuses=bonuses or [],
        contract_text=data.get("contract_text"),
    )


def load_competitions(season: Optional[int] = None):
    params = {"season": season} if season is not None else None
    return [build_competition(item) for item in fetch_json("/api/competitions", params=params)["items"]]


def load_clubs(competition_id: int, season: Optional[int] = None):
    params = {"season": season} if season is not None else None
    clubs = fetch_json(f"/api/competitions/{competition_id}/clubs", params=params)["items"]
    return [build_team(item) for item in clubs]


def load_players(club_id: int, season: Optional[int] = None):
    params = {"season": season} if season is not None else None
    players = fetch_json(f"/api/clubs/{club_id}/players", params=params)["items"]
    return [build_player(item) for item in players]


def load_player(player_id: int) -> Player:
    data = fetch_json(f"/api/players/{player_id}")
    team = None
    if data.get("club_id") or data.get("club_name"):
        competition = None
        if data.get("competition_id") or data.get("competition_name"):
            competition = Competition(
                id=data.get("competition_id") or 0,
                name=data.get("competition_name") or "",
                code=data.get("transfermarkt_code"),
                country=data.get("competition_country"),
                season=data.get("competition_season"),
            )
        team = Team(
            id=data.get("club_id") or 0,
            name=data.get("club_name") or "",
            slug=data.get("club_slug"),
            transfermarkt_club_id=data.get("transfermarkt_club_id"),
            competition=competition,
        )
    return build_player(data, team=team)


def load_active_contract(player_id: int):
    data = fetch_json(f"/api/players/{player_id}/contract")
    if not data:
        return None
    return build_contract(data)


def load_player_stats(
    player_id: int,
    seasons: Optional[list[int]] = None,
    club_id: Optional[int] = None,
    competition_id: Optional[int] = None,
):
    params = {}
    if seasons:
        params["seasons"] = seasons
    if club_id is not None:
        params["club_id"] = club_id
    if competition_id is not None:
        params["competition_id"] = competition_id
    return fetch_json(f"/api/players/{player_id}/stats", params=params or None)["items"]


def load_bonuses(contract_id: int):
    bonuses = fetch_json(f"/api/contracts/{contract_id}/bonuses")["items"]
    return [build_bonus(item) for item in bonuses]


def load_conditions(bonus_id: int):
    conditions = fetch_json(f"/api/bonuses/{bonus_id}/conditions")["items"]
    return [build_condition(item) for item in conditions]


def load_contract_bonuses(contract_id: int):
    bonuses = load_bonuses(contract_id)
    for bonus in bonuses:
        bonus.conditions = load_conditions(bonus.id)
    return bonuses


def load_app_user(email: str):
    response = requests.get(
        f"{API_BASE_URL}/api/auth/by-email",
        params={"email": email},
        timeout=30,
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def touch_app_user_login(user_id: int):
    return post_json(f"/api/auth/{user_id}/touch-login")
