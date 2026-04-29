from fastapi import APIRouter

from app.repositories.catalog import (
    fetch_active_contract_by_player,
    fetch_latest_stats_by_player,
    fetch_player_by_id,
    list_clubs_by_competition,
    list_bonuses_by_contract,
    list_competitions,
    list_conditions_by_bonus,
    list_players_by_club,
    list_players_by_competition,
)

router = APIRouter()


def list_response(items):
    return {"items": items, "count": len(items)}


@router.get("/")
def root():
    return {"message": "bonus_tracker API"}


@router.get("/api/competitions")
def competitions():
    return list_response(list_competitions())


@router.get("/api/competitions/{competition_id}/clubs")
def clubs_by_competition(competition_id: int):
    return list_response(list_clubs_by_competition(competition_id))


@router.get("/api/competitions/{competition_id}/players")
def players_by_competition(competition_id: int):
    return list_response(list_players_by_competition(competition_id))


@router.get("/api/clubs/{club_id}/players")
def players_by_club(club_id: int):
    return list_response(list_players_by_club(club_id))


@router.get("/api/players/{player_id}")
def player_by_id(player_id: int):
    return fetch_player_by_id(player_id)


@router.get("/api/players/{player_id}/contract")
def active_contract_by_player(player_id: int):
    return fetch_active_contract_by_player(player_id)


@router.get("/api/players/{player_id}/stats")
def latest_stats_by_player(player_id: int):
    return fetch_latest_stats_by_player(player_id)


@router.get("/api/contracts/{contract_id}/bonuses")
def bonuses_by_contract(contract_id: int):
    return list_response(list_bonuses_by_contract(contract_id))


@router.get("/api/bonuses/{bonus_id}/conditions")
def conditions_by_bonus(bonus_id: int):
    return list_response(list_conditions_by_bonus(bonus_id))
