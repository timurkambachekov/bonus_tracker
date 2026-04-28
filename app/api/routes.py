from fastapi import APIRouter, HTTPException

from app.repositories.bonus_tracker import (
    fetch_contract_bonuses,
    fetch_contract_bonus_conditions,
    fetch_contracts_for_player,
    fetch_player_by_id,
    fetch_player_stats,
    get_summary,
    list_clubs,
    list_players,
    list_spartak_contracts,
    list_stats,
    ping_database,
)
from app.services.player_service import build_contract_list, build_player_detail_response

router = APIRouter()


@router.get("/")
def api_root():
    return {
        "message": "bonus_tracker API",
        "endpoints": [
            "/health",
            "/api/summary",
            "/api/clubs",
            "/api/players",
            "/api/players/{player_id}",
            "/api/stats",
            "/api/contracts/spartak",
            "/docs",
        ],
    }


@router.get("/health")
def healthcheck():
    row = ping_database()
    return {"status": "ok", "database": row["ok"] == 1}


@router.get("/api/summary")
def summary():
    return get_summary()


@router.get("/api/clubs")
def clubs():
    items = list_clubs()
    return {"items": items, "count": len(items)}


@router.get("/api/players")
def players(limit: int = 200):
    if limit < 1 or limit > 2000:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 2000")

    items = list_players(limit)
    return {"items": items, "count": len(items)}


@router.get("/api/players/{player_id}")
def player_detail(player_id: int):
    player = fetch_player_by_id(player_id)
    if not player:
        raise HTTPException(status_code=404, detail="player not found")

    stats = fetch_player_stats(player_id)
    contracts = fetch_contracts_for_player(player_id)
    bonuses = fetch_contract_bonuses(player_id)
    conditions = fetch_contract_bonus_conditions(player_id)
    return build_player_detail_response(player, stats, contracts, bonuses, conditions)


@router.get("/api/stats")
def stats(limit: int = 500):
    if limit < 1 or limit > 5000:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 5000")

    items = list_stats(limit)
    return {"items": items, "count": len(items)}


@router.get("/api/contracts/spartak")
def spartak_contracts():
    contracts = list_spartak_contracts()
    bonuses = fetch_contract_bonuses()
    conditions = fetch_contract_bonus_conditions()
    items = build_contract_list(
        contracts,
        bonuses,
        conditions,
        include_progress=False,
    )
    return {"items": items, "count": len(items)}
