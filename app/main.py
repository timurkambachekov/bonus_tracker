from fastapi import FastAPI, HTTPException

from app.bonus_logic import evaluate_bonus_progress
from app.db import get_connection

app = FastAPI(title="bonus_tracker")


def fetch_rows(query: str, params=()):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()


def fetch_one(query: str, params=()):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()

@app.get("/")
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


@app.get("/health")
def healthcheck():
    row = fetch_one("SELECT 1 AS ok;")
    return {"status": "ok", "database": row["ok"] == 1}


@app.get("/api/summary")
def summary():
    row = fetch_one(
        """
        SELECT
            (SELECT COUNT(*) FROM clubs) AS clubs,
            (SELECT COUNT(*) FROM players) AS players,
            (SELECT COUNT(*) FROM player_season_stats) AS stats,
            (SELECT COUNT(*) FROM contract_terms) AS contracts,
            (SELECT COUNT(*) FROM contract_bonuses) AS bonuses;
        """
    )
    return row


@app.get("/api/clubs")
def list_clubs():
    rows = fetch_rows(
        """
        SELECT
            c.id,
            c.transfermarkt_club_id,
            c.club_slug,
            c.club_name,
            COUNT(p.id) AS player_count
        FROM clubs c
        LEFT JOIN players p ON p.club_id = c.id
        GROUP BY c.id, c.transfermarkt_club_id, c.club_slug, c.club_name
        ORDER BY COALESCE(c.club_name, c.club_slug);
        """
    )
    return {"items": rows, "count": len(rows)}


@app.get("/api/players")
def list_players(limit: int = 200):
    if limit < 1 or limit > 2000:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 2000")

    rows = fetch_rows(
        """
        SELECT
            p.id,
            p.transfermarkt_player_id,
            p.player_name,
            p.position,
            p.nationality,
            p.market_value_eur,
            c.club_slug,
            c.club_name
        FROM players p
        LEFT JOIN clubs c ON c.id = p.club_id
        ORDER BY p.player_name
        LIMIT %s;
        """,
        (limit,),
    )
    return {"items": rows, "count": len(rows)}


@app.get("/api/players/{player_id}")
def player_detail(player_id: int):
    player = fetch_one(
        """
        SELECT
            p.id,
            p.transfermarkt_player_id,
            p.player_name,
            p.position,
            p.date_of_birth,
            p.nationality,
            p.height_m,
            p.foot,
            p.market_value_eur,
            c.id AS club_id,
            c.club_slug,
            c.club_name
        FROM players p
        LEFT JOIN clubs c ON c.id = p.club_id
        WHERE p.id = %s;
        """,
        (player_id,),
    )
    if not player:
        raise HTTPException(status_code=404, detail="player not found")

    stats = fetch_rows(
        """
        SELECT
            season,
            squad_inclusions,
            appearances,
            goals,
            assists,
            yellow_cards,
            red_cards,
            substitutions_on,
            substitutions_off,
            minutes_played,
            ppg
        FROM player_season_stats
        WHERE player_id = %s
        ORDER BY season DESC, id DESC;
        """,
        (player_id,),
    )

    contracts = fetch_rows(
        """
        SELECT
            ct.id,
            ct.base_salary,
            ct.contract_start,
            ct.contract_end,
            c.club_slug,
            c.club_name
        FROM contract_terms ct
        LEFT JOIN clubs c ON c.id = ct.club_id
        WHERE ct.player_id = %s
        ORDER BY ct.contract_start DESC NULLS LAST, ct.id DESC;
        """,
        (player_id,),
    )
    bonuses = fetch_rows(
        """
        SELECT
            contract_term_id,
            bonus_type,
            competition,
            games,
            starts,
            minutes,
            goals,
            assists,
            bonus_value
        FROM contract_bonuses
        WHERE contract_term_id IN (
            SELECT id FROM contract_terms WHERE player_id = %s
        )
        ORDER BY contract_term_id, id;
        """,
        (player_id,),
    )

    bonuses_by_contract = {}
    for bonus in bonuses:
        bonuses_by_contract.setdefault(bonus["contract_term_id"], []).append(bonus)

    contract_items = []
    latest_stats = stats[0] if stats else None
    total_payout_value = 0.0
    for contract in contracts:
        item = dict(contract)
        contract_bonuses = []
        contract_payout_value = 0.0
        for bonus in bonuses_by_contract.get(contract["id"], []):
            bonus_item = dict(bonus)
            if latest_stats:
                bonus_item["progress"] = evaluate_bonus_progress(bonus_item, latest_stats)
            else:
                bonus_item["progress"] = None
            payout_value = (
                bonus_item["progress"]["payout_value"]
                if bonus_item.get("progress")
                else 0.0
            )
            bonus_item["payout_value"] = payout_value
            contract_payout_value += payout_value
            contract_bonuses.append(bonus_item)
        item["bonuses"] = contract_bonuses
        item["total_payout_value"] = contract_payout_value
        total_payout_value += contract_payout_value
        contract_items.append(item)

    return {
        "player": player,
        "stats": stats,
        "contracts": contract_items,
        "totals": {
            "total_payout_value": total_payout_value,
        },
    }


@app.get("/api/stats")
def list_stats(limit: int = 500):
    if limit < 1 or limit > 5000:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 5000")

    rows = fetch_rows(
        """
        SELECT
            s.id,
            p.player_name,
            c.club_slug,
            c.club_name,
            s.season,
            s.squad_inclusions,
            s.appearances,
            s.goals,
            s.assists,
            s.minutes_played,
            s.ppg
        FROM player_season_stats s
        LEFT JOIN players p ON p.id = s.player_id
        LEFT JOIN clubs c ON c.id = s.club_id
        ORDER BY c.club_slug, p.player_name
        LIMIT %s;
        """,
        (limit,),
    )
    return {"items": rows, "count": len(rows)}


@app.get("/api/contracts/spartak")
def spartak_contracts():
    contracts = fetch_rows(
        """
        SELECT
            ct.id,
            p.player_name,
            ct.base_salary,
            ct.contract_start,
            ct.contract_end
        FROM contract_terms ct
        JOIN players p ON p.id = ct.player_id
        JOIN clubs c ON c.id = ct.club_id
        WHERE c.club_slug = 'spartak-moscou'
        ORDER BY p.player_name;
        """
    )
    bonuses = fetch_rows(
        """
        SELECT
            contract_term_id,
            bonus_type,
            competition,
            games,
            starts,
            minutes,
            goals,
            assists,
            bonus_value
        FROM contract_bonuses
        ORDER BY contract_term_id, id;
        """
    )

    bonuses_by_contract = {}
    for bonus in bonuses:
        bonuses_by_contract.setdefault(bonus["contract_term_id"], []).append(bonus)

    items = []
    for contract in contracts:
        item = dict(contract)
        item["bonuses"] = bonuses_by_contract.get(contract["id"], [])
        items.append(item)

    return {"items": items, "count": len(items)}
