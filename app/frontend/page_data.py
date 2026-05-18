from app.backend.domain import BonusType
from app.backend.services import calculate_bonus_progress
from app.frontend.api_client import (
    load_active_contract,
    load_contract_bonuses,
    load_player,
    load_players,
    load_player_stats,
)


def load_player_page_data(player_id):
    player = load_player(player_id)
    seasonal_stats = load_player_stats(
        player_id,
        club_id=player.team.id if player.team else None,
    )
    contract = load_active_contract(player_id)
    bonuses = load_contract_bonuses(contract.id) if contract else []
    return player, seasonal_stats, contract, bonuses


def contract_season_rows(contract, seasonal_stats):
    if not contract:
        return []

    start_year = int(str(contract.start_date)[:4])
    end_year = int(str(contract.end_date)[:4])
    return [
        row
        for row in seasonal_stats
        if row.get("season") is not None and start_year <= int(row["season"]) <= end_year
    ]


def build_player_bonus_summary_row(player, contract, bonuses, stats_row):
    seasonal_count = 0
    seasonal_payout = 0.0

    for bonus in bonuses:
        if bonus.bonus_type != BonusType.SEASONAL:
            continue

        progress = calculate_bonus_progress(bonus, stats_row)
        if not progress["achieved"]:
            continue

        payout_value = float(progress["payout_value"])
        seasonal_count += 1
        seasonal_payout += payout_value

    return {
        "Player": player.name,
        "Position": player.position or "-",
        "Season": int(stats_row["season"]),
        "Contract Start": contract.start_date,
        "Contract End": contract.end_date,
        "Seasonal Bonuses": seasonal_count,
        "Seasonal Payout": seasonal_payout,
        "Total Payout": seasonal_payout,
    }


def load_squad_bonus_summary(club_id):
    players = load_players(club_id)
    unique_players = {}
    for player in players:
        unique_players[player.id] = player
    summary_rows = []

    for player in unique_players.values():
        contract = load_active_contract(player.id)
        if not contract:
            continue

        bonuses = load_contract_bonuses(contract.id)
        if not bonuses:
            continue

        seasonal_stats = load_player_stats(player.id, club_id=club_id)
        for stats_row in contract_season_rows(contract, seasonal_stats):
            summary_rows.append(
                build_player_bonus_summary_row(player, contract, bonuses, stats_row)
            )

    return sorted(
        summary_rows,
        key=lambda row: (-int(row["Season"]), row["Player"]),
    )
