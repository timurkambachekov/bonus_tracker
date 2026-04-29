from app.ui.api_client import (
    load_active_contract,
    load_contract_bonuses,
    load_player,
    load_player_stats,
)


def load_player_page_data(player_id):
    player = load_player(player_id)
    stats = load_player_stats(player_id)
    contract = load_active_contract(player_id)
    bonuses = load_contract_bonuses(contract.id) if contract else []
    return player, stats, contract, bonuses
